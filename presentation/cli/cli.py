# presentation/cli/cli.py
import argparse
import sys
from datetime import datetime, date

from sqlalchemy.exc import SQLAlchemyError
from tabulate import tabulate

from application.commands.generate_schedule_command import GenerateScheduleCommand
from application.commands.generate_schedule_handler import GenerateScheduleHandler
from application.commands.create_manual_assignment_command import CreateManualAssignmentCommand
from application.commands.create_manual_assignment_handler import CreateManualAssignmentHandler
from domain.models.TeamModel import TeamModel
from domain.models.db import Session
from domain.repositories.implementations.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from domain.repositories.implementations.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from domain.repositories.implementations.sqlalchemy_team_repository import SqlAlchemyTeamRepository
from domain.repositories.implementations.sqlalchemy_assignment_repository import SqlAlchemyAssignmentRepository
from domain.repositories.implementations.sqlalchemy_employee_work_history_repository import SqlAlchemyEmployeeWorkHistoryRepository
from domain.services.schedule_service import ScheduleService


def get_team_by_name(name):
    """
    Look up a team by name and return its ID.

    Args:
        name (str): The name of the team to look up

    Returns:
        int: The team ID if found

    Raises:
        ValueError: If the team is not found
    """
    session = Session()
    try:
        team = session.query(TeamModel).filter_by(name=name).first()
        if not team:
            raise ValueError(f"TeamModel '{name}' not found")
        return team.id
    finally:
        session.close()


def setup_dependencies():
    """
    Set up and return the dependencies needed for the application.

    Returns:
        tuple: A tuple containing (session, employee_repository, workstation_repository, team_repository, schedule_service, assignment_repository, work_history_repository)
    """
    session = Session()
    employee_repository = SqlAlchemyEmployeeRepository(session)
    workstation_repository = SqlAlchemyWorkstationRepository(session)
    team_repository = SqlAlchemyTeamRepository(session)
    schedule_service = ScheduleService()
    assignment_repository = SqlAlchemyAssignmentRepository(session)
    work_history_repository = SqlAlchemyEmployeeWorkHistoryRepository(session)

    return session, employee_repository, workstation_repository, team_repository, schedule_service, assignment_repository, work_history_repository


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: The parsed arguments
    """
    parser = argparse.ArgumentParser(description='Heijunka Scheduling System')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Generate schedule command
    generate_parser = subparsers.add_parser('generate', help='Generate a schedule')
    generate_parser.add_argument('--team', type=str, required=True, help='Team name')
    generate_parser.add_argument('--start-date', type=str, default=date.today(), help='Start date for the schedule')
    generate_parser.add_argument('--days', type=int, default=1, help='Number of days to schedule')
    generate_parser.add_argument('--periods', type=int, default=4, help='Number of periods per day')
    generate_parser.add_argument('--call-ins', type=str, nargs='*', help='Employees calling in')
    generate_parser.add_argument('--offline', type=str, nargs='*', help='Employees offline for specific periods in format "employee:periods" (e.g., "John:1,2")')
    generate_parser.add_argument('--force-complete', action='store_true', help='Force complete the schedule')

    # Manual assignment command
    assign_parser = subparsers.add_parser('assign', help='Create a manual assignment')
    assign_parser.add_argument('--employee', type=str, required=True, help='Employee name')
    assign_parser.add_argument('--workstation', type=str, required=True, help='Workstation name')
    assign_parser.add_argument('--date', type=str, default=date.today().isoformat(), help='Assignment date (YYYY-MM-DD)')
    assign_parser.add_argument('--period', type=int, required=True, help='Work period (1-4)')
    assign_parser.add_argument('--schedule-id', type=int, help='Schedule ID (optional)')

    return parser.parse_args()


def format_schedule_table(assignments, employees, workstations, periods, date_obj, call_ins=None, offline=None):
    """
    Format assignments as a readable table for a specific date using tabulate.

    Args:
        assignments: List of WorkAssignment objects
        employees: List of Employee objects
        workstations: List of Workstation objects
        periods: Number of periods per day
        date_obj: The date to display
        call_ins: List of employee names who called in (unavailable)
        offline: List of strings in format "employee:periods" specifying which employees are offline for which periods

    Returns:
        str: Formatted schedule as a string
    """
    # Filter assignments for the specified date
    day_assignments = [a for a in assignments if a.period.date == date_obj]

    # Create a dictionary to store the schedule: {workstation_name: {period: employee_name}}
    schedule = {}
    for ws in workstations:
        schedule[ws.name] = {p+1: "-" for p in range(periods)}

    # Add special rows
    schedule["Offline"] = {p+1: "-" for p in range(periods)}
    schedule["Called-in"] = {p+1: "-" for p in range(periods)}

    # Fill in the schedule with assignments
    for assignment in day_assignments:
        ws_name = assignment.workstation.name
        period = assignment.period.period
        emp_name = assignment.employee.name
        schedule[ws_name][period] = emp_name

    # Parse offline parameter
    employee_offline_periods = {}
    if offline:
        for offline_str in offline:
            parts = offline_str.split(':')
            if len(parts) == 2:
                emp_name, periods_str = parts
                periods_list = [int(p) for p in periods_str.split(',')]
                employee_offline_periods[emp_name] = periods_list

    # Find offline employees (available but not assigned or explicitly marked as offline)
    for p in range(1, periods+1):
        # Get all employees assigned to a workstation in this period
        assigned_employees = {a.employee.id for a in day_assignments if a.period.period == p}

        # Find employees who are available but not assigned
        unassigned_employees = []
        for emp in employees:
            if emp.id not in assigned_employees and emp.is_available_for_period(date_obj, p):
                unassigned_employees.append(emp.name)

        # Find employees who are explicitly marked as offline for this period
        explicitly_offline = []
        for emp_name, offline_periods in employee_offline_periods.items():
            if p in offline_periods:
                explicitly_offline.append(f"{emp_name} (offline)")

        # Combine both lists
        offline_employees = explicitly_offline + unassigned_employees

        # Add to the schedule
        if offline_employees:
            schedule["Offline"][p] = ", ".join(offline_employees)

    # Add called-in employees to the Called-in row
    if call_ins:
        # Show called-in employees in all periods
        called_in_names = []
        for emp in employees:
            if emp.name in call_ins:
                called_in_names.append(emp.name)

        if called_in_names:
            for p in range(1, periods+1):
                schedule["Called-in"][p] = ", ".join(called_in_names)

    # Prepare data for tabulate
    headers = ["Station"] + [f"P{p}" for p in range(1, periods+1)]
    table_data = []

    # Define the specific order of workstations
    station_order = [
        "Parts Wash",
        "H010",
        "H080/H090",
        "H100",
        "H110/H120",
        "H170",
        "BW010",
        "BW070",
        "M050",
        "M090",
        "Offline",
        "Called-in"
    ]

    # Define stations to highlight
    warn_yellow = {'H010', 'M050', 'M090'}
    warn_red = {'BW010', 'H170'}

    # Add rows in the specified order
    for station in station_order:
        if station in schedule:
            row = [station]

            # Apply color highlighting if needed
            color = ''
            if station in warn_yellow:
                color = '\033[93m'  # Yellow
            elif station in warn_red:
                color = '\033[91m'  # Red

            for p in range(1, periods+1):
                value = schedule[station].get(p, "-")
                if color and value != "-":
                    row.append(f"{color}{value}\033[0m")  # Add color and reset
                else:
                    row.append(value)

            table_data.append(row)

    # Format using tabulate
    table_str = tabulate(table_data, headers=headers, tablefmt="grid")

    # Add header
    return f"Schedule for {date_obj}:\n{table_str}"


def handle_manual_assignment(args, session):
    """
    Handle the manual assignment command.

    Args:
        args: Command line arguments
        session: Database session
    """
    try:
        # Setup repositories
        employee_repository = SqlAlchemyEmployeeRepository(session)
        workstation_repository = SqlAlchemyWorkstationRepository(session)
        assignment_repository = SqlAlchemyAssignmentRepository(session)

        # Get employee by name
        employee = employee_repository.get_by_name(args.employee)
        if not employee:
            print(f"Error: Employee '{args.employee}' not found", file=sys.stderr)
            return False

        # Get workstation by name
        workstation = workstation_repository.get_by_name(args.workstation)
        if not workstation:
            print(f"Error: Workstation '{args.workstation}' not found", file=sys.stderr)
            return False

        # Parse date
        try:
            assignment_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format. Use YYYY-MM-DD", file=sys.stderr)
            return False

        # Validate period
        if args.period < 1 or args.period > 4:
            print(f"Error: Period must be between 1 and 4", file=sys.stderr)
            return False

        # Create command handler
        handler = CreateManualAssignmentHandler(assignment_repository)

        # Create command
        command = CreateManualAssignmentCommand(
            employee_id=employee.id,
            workstation_id=workstation.id,
            assignment_date=assignment_date,
            period=args.period,
            schedule_id=args.schedule_id
        )

        # Handle command
        success = handler.handle(command)

        if success:
            print(f"Successfully assigned {args.employee} to {args.workstation} on {args.date} for period {args.period}")
            return True
        else:
            print("Failed to create assignment", file=sys.stderr)
            return False

    except Exception as e:
        print(f"Error creating manual assignment: {e}", file=sys.stderr)
        return False

def main():
    """
    Main entry point for the CLI application.
    """
    try:
        # Parse arguments
        args = parse_arguments()

        # Setup dependencies
        session, employee_repository, workstation_repository, team_repository, schedule_service, assignment_repository, work_history_repository = setup_dependencies()

        try:
            if args.command == 'generate':
                # Get team ID from name
                try:
                    team_id = get_team_by_name(args.team)
                except ValueError as e:
                    print(f"Error: {e}", file=sys.stderr)
                    sys.exit(1)

                # Create handler
                handler = GenerateScheduleHandler(
                    employee_repository=employee_repository,
                    workstation_repository=workstation_repository,
                    team_repository=team_repository,
                    assignment_repository=assignment_repository,
                    schedule_service=schedule_service,
                    session=session
                )

                # Create command
                # Parse start_date if it's a string
                start_date = args.start_date
                if isinstance(start_date, str):
                    try:
                        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                    except ValueError:
                        print(f"Error: Invalid start date format. Use YYYY-MM-DD", file=sys.stderr)
                        sys.exit(1)

                command = GenerateScheduleCommand(
                    team_id=team_id,
                    start_date=start_date,
                    days=args.days,
                    periods_per_day=args.periods,
                    call_ins=args.call_ins,
                    offline=args.offline,
                    force_complete=args.force_complete
                )

                # Handle command
                assignments = handler.handle(command)
            elif args.command == 'assign':
                # Handle manual assignment
                handle_manual_assignment(args, session)
            else:
                print("Error: No command specified. Use 'generate' or 'assign'.", file=sys.stderr)
                sys.exit(1)

            # Display results for generate command
            if args.command == 'generate':
                if not assignments:
                    print("No assignments generated.")
                else:
                    print(f"Generated {len(assignments)} assignments")
                    print("Assignments have been saved to the employee_work_history table.")

                    # Verify assignments were saved to the database
                    start_date = command.start_date
                    end_date = command.start_date  # For now, just verify the first day

                    # Get work history entries for the date range
                    try:
                        work_history_entries = work_history_repository.get_by_date_range(start_date, end_date)
                        saved_count = len(work_history_entries)

                        # Count only the entries that were generated by the scheduler
                        generated_entries = [entry for entry in work_history_entries 
                                            if any(entry.employee_id == a.employee.id and 
                                                   entry.workstation_id == a.workstation.id and
                                                   entry.worked_date == a.period.date and
                                                   entry.work_period == a.period.period
                                                   for a in assignments)]

                        print(f"Verified {len(generated_entries)} of {len(assignments)} assignments in the database.")

                        if len(generated_entries) != len(assignments):
                            print("Warning: Not all assignments were saved to the database.")
                    except Exception as e:
                        print(f"Warning: Could not verify assignments in database: {e}")

                    # Get employees and workstations for the team
                    employees = employee_repository.get_by_team_id(team_id)
                    workstations = workstation_repository.get_by_team_id(team_id)

                    # Group assignments by date
                    assignments_by_date = {}
                    for assignment in assignments:
                        date_key = assignment.period.date
                        if date_key not in assignments_by_date:
                            assignments_by_date[date_key] = []
                        assignments_by_date[date_key].append(assignment)

                    # Print schedule for each date
                    for date_key in sorted(assignments_by_date.keys()):
                        print(format_schedule_table(
                            assignments_by_date[date_key], 
                            employees, 
                            workstations, 
                            args.periods, 
                            date_key,
                            args.call_ins,
                            args.offline
                        ))
                        print("\n")  # Add some space between dates

        except Exception as e:
            print(f"Error generating schedule: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            session.close()

    except SQLAlchemyError as e:
        print(f"Database error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
