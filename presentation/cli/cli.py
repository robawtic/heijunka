# presentation/cli/cli.py
import argparse
import sys
import os
from datetime import datetime, date

from sqlalchemy.exc import SQLAlchemyError
from tabulate import tabulate

from application.commands.generate_schedule_command import GenerateScheduleCommand
from application.commands.generate_schedule_handler import GenerateScheduleHandler
from application.commands.create_manual_assignment_command import CreateManualAssignmentCommand
from application.commands.create_manual_assignment_handler import CreateManualAssignmentHandler
from domain.models.db import Session
from domain.repositories.implementations.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from domain.repositories.implementations.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from domain.repositories.implementations.sqlalchemy_team_repository import SqlAlchemyTeamRepository
from domain.repositories.implementations.sqlalchemy_assignment_repository import SqlAlchemyAssignmentRepository
from domain.repositories.implementations.sqlalchemy_employee_work_history_repository import SqlAlchemyEmployeeWorkHistoryRepository
from domain.repositories.implementations.sqlalchemy_schedule_repository import SqlAlchemyScheduleRepository
from domain.services.schedule_service import ScheduleService




def setup_dependencies():
    """
    Set up and return the dependencies needed for the application.

    Returns:
        tuple: A tuple containing (session, employee_repository, workstation_repository, team_repository, schedule_service, assignment_repository, work_history_repository, aro_repository, aro_service, aro_graph_service, schedule_repository)
    """
    session = Session()
    employee_repository = SqlAlchemyEmployeeRepository(session)
    workstation_repository = SqlAlchemyWorkstationRepository(session)
    team_repository = SqlAlchemyTeamRepository(session)
    schedule_service = ScheduleService()
    assignment_repository = SqlAlchemyAssignmentRepository(session)
    work_history_repository = SqlAlchemyEmployeeWorkHistoryRepository(session)
    schedule_repository = SqlAlchemyScheduleRepository(session)

    # Import here to avoid circular imports
    from domain.repositories.implementations.sqlalchemy_aro_assignment_repository import SqlAlchemyAROAssignmentRepository
    aro_repository = SqlAlchemyAROAssignmentRepository(session)

    # Create and register the schedule recalculation handler
    from domain.services.aro_service import AROService
    from domain.services.schedule_recalculation_handler import ScheduleRecalculationHandler
    from domain.services.aro_graph_service import AROGraphService
    from domain.services.cache_invalidation_handler import CacheInvalidationHandler

    aro_service = AROService(aro_repository, employee_repository, team_repository)
    schedule_recalculation_handler = ScheduleRecalculationHandler(team_repository, schedule_service)

    # Create the ARO graph service
    aro_graph_service = AROGraphService(
        aro_service=aro_service,
        aro_repository=aro_repository,
        employee_repository=employee_repository,
        team_repository=team_repository,
        workstation_repository=workstation_repository
    )

    # Create the cache invalidation handler
    cache_invalidation_handler = CacheInvalidationHandler(aro_graph_service)

    # Register event handlers for schedule recalculation
    aro_service.register_event_handler('aro_assignment_created', schedule_recalculation_handler.handle_aro_assignment_created)
    aro_service.register_event_handler('aro_assignment_removed', schedule_recalculation_handler.handle_aro_assignment_removed)
    aro_service.register_event_handler('aro_assignment_updated', schedule_recalculation_handler.handle_aro_assignment_updated)

    # Register event handlers for cache invalidation
    aro_service.register_event_handler('aro_assignment_created', cache_invalidation_handler.handle_aro_assignment_created)
    aro_service.register_event_handler('aro_assignment_removed', cache_invalidation_handler.handle_aro_assignment_removed)
    aro_service.register_event_handler('aro_assignment_updated', cache_invalidation_handler.handle_aro_assignment_updated)

    return session, employee_repository, workstation_repository, team_repository, schedule_service, assignment_repository, work_history_repository, aro_repository, aro_service, aro_graph_service, schedule_repository


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
    team_group = generate_parser.add_mutually_exclusive_group(required=True)
    team_group.add_argument('--team', type=str, help='Team name')
    team_group.add_argument('--group', type=str, help='Group name (generates schedules for all teams in the group)')
    team_group.add_argument('--department', type=str, help='Department name (generates schedules for all teams in the department)')
    generate_parser.add_argument('--start-date', type=str, default=date.today(), help='Start date for the schedule')
    generate_parser.add_argument('--periods', type=int, default=4, help='Number of periods per day')
    generate_parser.add_argument('--call-ins', type=str, nargs='*', help='Employees calling in')
    generate_parser.add_argument('--offline', type=str, nargs='*', help='Employees offline for specific periods in format "employee:periods" (e.g., "John:1,2")')
    generate_parser.add_argument('--force-complete', action='store_true', help='Force complete the schedule')

    # Simulation command
    simulate_parser = subparsers.add_parser('simulate', help='Run scheduling simulations')
    simulate_parser.add_argument('--team', type=str, required=True, help='Team name')
    simulate_parser.add_argument('--start-date', type=str, default=date.today().isoformat(), help='Start date for the schedule (YYYY-MM-DD)')
    simulate_parser.add_argument('--periods', type=int, default=4, help='Number of periods per day')
    simulate_parser.add_argument('--scenarios', type=str, required=True, help='Path to scenarios JSON file')
    simulate_parser.add_argument('--output-dir', type=str, default='.', help='Directory to save output files')
    simulate_parser.add_argument('--advanced', action='store_true', help='Generate advanced analytics')

    # Regression test command
    regression_parser = subparsers.add_parser('regression-test', help='Run regression tests against golden outputs')
    regression_parser.add_argument('--team', type=str, required=True, help='Team name')
    regression_parser.add_argument('--start-date', type=str, default=date.today().isoformat(), help='Start date for the schedule (YYYY-MM-DD)')
    regression_parser.add_argument('--periods', type=int, default=4, help='Number of periods per day')
    regression_parser.add_argument('--tests', type=str, required=True, help='Path to regression tests JSON file')
    regression_parser.add_argument('--output-dir', type=str, default='.', help='Directory to save output files')
    regression_parser.add_argument('--generate-golden', action='store_true', help='Generate golden outputs instead of running tests')
    regression_parser.add_argument('--golden-output', type=str, help='Path to save golden outputs (required if --generate-golden is used)')
    regression_parser.add_argument('--threshold', type=float, default=0.0, help='Global threshold for all metrics (overrides defaults)')

    # Manual assignment command
    assign_parser = subparsers.add_parser('assign', help='Create a manual assignment')
    assign_parser.add_argument('--employee', type=str, required=True, help='Employee name')
    assign_parser.add_argument('--workstation', type=str, required=True, help='Workstation name')
    assign_parser.add_argument('--date', type=str, default=date.today().isoformat(), help='Assignment date (YYYY-MM-DD)')
    assign_parser.add_argument('--period', type=int, required=True, help='Work period (1-4)')
    assign_parser.add_argument('--schedule-id', type=int, help='Schedule ID (optional)')

    # ARO assignment commands
    aro_subparsers = subparsers.add_parser('aro', help='ARO management commands')
    aro_subparsers = aro_subparsers.add_subparsers(dest='aro_command', help='ARO command to execute')

    # ARO assign command
    aro_assign_parser = aro_subparsers.add_parser('assign', help='Assign an employee as an ARO to another team')
    aro_assign_parser.add_argument('--employee', '-e', type=str, required=True, help='Employee name')
    aro_assign_parser.add_argument('--from-team', '-f', type=str, required=True, help='From team name')
    aro_assign_parser.add_argument('--to-team', '-t', type=str, required=True, help='To team name')
    aro_assign_parser.add_argument('--date', '-d', type=str, default=date.today().isoformat(), help='Assignment date (YYYY-MM-DD)')
    aro_assign_parser.add_argument('--period', '-p', type=int, default=None, help='Period (1-4, omit for full day)')

    # ARO remove command
    aro_remove_parser = aro_subparsers.add_parser('remove', help='Remove an ARO assignment')
    aro_remove_parser.add_argument('--employee', '-e', type=str, required=True, help='Employee name')
    aro_remove_parser.add_argument('--date', '-d', type=str, default=date.today().isoformat(), help='Assignment date (YYYY-MM-DD)')
    aro_remove_parser.add_argument('--period', '-p', type=int, default=None, help='Period (1-4, omit for full day)')

    # ARO optimize command
    aro_optimize_parser = aro_subparsers.add_parser('optimize', help='Optimize ARO assignments using graph theory')
    aro_optimize_parser.add_argument('--team', '-t', type=str, required=True, help='Understaffed team name')
    aro_optimize_parser.add_argument('--count', '-c', type=int, required=True, help='Number of AROs needed')
    aro_optimize_parser.add_argument('--date', '-d', type=str, default=date.today().isoformat(), help='Assignment date (YYYY-MM-DD)')
    aro_optimize_parser.add_argument('--period', '-p', type=int, default=None, help='Period (1-4, omit for full day)')
    aro_optimize_parser.add_argument('--max-hops', '-m', type=int, default=2, help='Maximum number of intermediate teams (default: 2)')

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


def handle_aro_assignment(args, session, aro_service=None, aro_graph_service=None):
    """
    Handle the ARO management commands.

    Args:
        args: Command line arguments
        session: Database session
        aro_service: Optional ARO service instance (if None, a new one will be created)
        aro_graph_service: Optional ARO graph service instance
    """
    try:
        # Setup repositories
        employee_repository = SqlAlchemyEmployeeRepository(session)
        team_repository = SqlAlchemyTeamRepository(session)
        workstation_repository = SqlAlchemyWorkstationRepository(session)

        # Use the provided ARO service or create a new one
        if aro_service is None:
            from domain.repositories.implementations.sqlalchemy_aro_assignment_repository import SqlAlchemyAROAssignmentRepository
            aro_repository = SqlAlchemyAROAssignmentRepository(session)
            from domain.services.aro_service import AROService
            aro_service = AROService(aro_repository, employee_repository, team_repository)

        # Handle ARO optimize command
        if args.aro_command == 'optimize':
            # Create ARO graph service if not provided
            if aro_graph_service is None:
                from domain.repositories.implementations.sqlalchemy_aro_assignment_repository import SqlAlchemyAROAssignmentRepository
                aro_repository = SqlAlchemyAROAssignmentRepository(session)
                from domain.services.aro_graph_service import AROGraphService
                aro_graph_service = AROGraphService(
                    aro_service=aro_service,
                    aro_repository=aro_repository,
                    employee_repository=employee_repository,
                    team_repository=team_repository,
                    workstation_repository=workstation_repository
                )

            # Get team by name
            team = team_repository.get_by_name(args.team)
            if not team:
                print(f"Error: Team '{args.team}' not found", file=sys.stderr)
                return False

            # Parse date
            try:
                assignment_date = datetime.strptime(args.date, "%Y-%m-%d").date()
            except ValueError:
                print(f"Error: Invalid date format. Use YYYY-MM-DD", file=sys.stderr)
                return False

            # Assign optimal AROs
            assignments = aro_graph_service.assign_optimal_aros(
                understaffed_team_id=team.id,
                needed_aros=args.count,
                assignment_date=assignment_date,
                period=args.period
            )

            if assignments:
                print(f"Successfully assigned {len(assignments)} AROs to team {args.team}.")

                # Display the assignments
                for assignment in assignments:
                    employee = employee_repository.get(assignment.employee_id)
                    from_team = team_repository.get(assignment.from_team_id)
                    to_team = team_repository.get(assignment.to_team_id)

                    employee_name = employee.name if employee else f"Employee {assignment.employee_id}"
                    from_team_name = from_team.name if from_team else f"Team {assignment.from_team_id}"
                    to_team_name = to_team.name if to_team else f"Team {assignment.to_team_id}"

                    period_str = f" for period {assignment.period}" if assignment.period else " for the full day"
                    print(f"- {employee_name} from {from_team_name} to {to_team_name}{period_str}")

                return True
            else:
                print(f"Could not find suitable AROs for team {args.team}.")
                return False

        # For other commands, we need an employee
        if args.aro_command != 'optimize':
            # Get employee by name
            employee = employee_repository.get_by_name(args.employee)
            if not employee:
                print(f"Error: Employee '{args.employee}' not found", file=sys.stderr)
                return False

            # Parse date
            try:
                assignment_date = datetime.strptime(args.date, "%Y-%m-%d").date()
            except ValueError:
                print(f"Error: Invalid date format. Use YYYY-MM-DD", file=sys.stderr)
                return False

        # Handle ARO assign command
        if args.aro_command == 'assign':
            # Get from team by name
            from_team = team_repository.get_by_name(args.from_team)
            if not from_team:
                print(f"Error: Team '{args.from_team}' not found", file=sys.stderr)
                return False

            # Get to team by name
            to_team = team_repository.get_by_name(args.to_team)
            if not to_team:
                print(f"Error: Team '{args.to_team}' not found", file=sys.stderr)
                return False

            # Verify employee belongs to from_team
            if employee.team_id != from_team.id:
                print(f"Error: Employee '{args.employee}' does not belong to team '{args.from_team}'", file=sys.stderr)
                return False

            # Assign ARO
            result = aro_service.assign_aro(employee.id, to_team.id, assignment_date, args.period)

            if result["status"] == "success":
                period_str = f" for period {args.period}" if args.period else " for the full day"
                print(f"Successfully assigned {args.employee} as ARO from {args.from_team} to {args.to_team} on {args.date}{period_str}")
                return True
            else:
                print(f"Error: {result['message']}", file=sys.stderr)
                return False

        # Handle ARO remove command
        elif args.aro_command == 'remove':
            # Find the ARO assignment
            assignment = aro_service.find_aro_assignment(employee.id, assignment_date, args.period)
            if not assignment:
                period_str = f" for period {args.period}" if args.period else " for the full day"
                print(f"Error: No ARO assignment found for {args.employee} on {args.date}{period_str}", file=sys.stderr)
                return False

            # Get the from and to teams for display
            from_team = team_repository.get(assignment.from_team_id)
            to_team = team_repository.get(assignment.to_team_id)

            # Remove the ARO assignment
            result = aro_service.remove_aro_assignment(assignment.id)

            if result["status"] == "success":
                period_str = f" for period {args.period}" if args.period else " for the full day"
                from_team_name = from_team.name if from_team else f"team {assignment.from_team_id}"
                to_team_name = to_team.name if to_team else f"team {assignment.to_team_id}"
                print(f"Successfully removed ARO assignment for {args.employee} from {from_team_name} to {to_team_name} on {args.date}{period_str}")
                return True
            else:
                print(f"Error: {result['message']}", file=sys.stderr)
                return False

        else:
            print(f"Error: Unknown ARO command '{args.aro_command}'", file=sys.stderr)
            return False

    except Exception as e:
        print(f"Error handling ARO command: {e}", file=sys.stderr)
        return False

def handle_regression_test(args, session):
    """
    Handle the regression test command.

    Args:
        args: Command line arguments
        session: Database session
    """
    try:
        from domain.services.regression_test_service import RegressionTestService
        from domain.value_objects.regression_test_scenario import RegressionTestScenario
        from tabulate import tabulate
        import os

        # Setup repositories
        employee_repository = SqlAlchemyEmployeeRepository(session)
        workstation_repository = SqlAlchemyWorkstationRepository(session)
        team_repository = SqlAlchemyTeamRepository(session)
        schedule_repository = SqlAlchemyScheduleRepository(session)
        schedule_service = ScheduleService()

        # Get team by name
        team = team_repository.get_by_name(args.team)
        if not team:
            print(f"Error: Team '{args.team}' not found", file=sys.stderr)
            return False

        # Parse start date
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format. Use YYYY-MM-DD", file=sys.stderr)
            return False

        # Create regression test service
        regression_service = RegressionTestService(
            employee_repository=employee_repository,
            workstation_repository=workstation_repository,
            team_repository=team_repository,
            schedule_service=schedule_service,
            schedule_repository=schedule_repository,
            session=session
        )

        # Check if we're generating golden outputs
        if args.generate_golden:
            if not args.golden_output:
                print("Error: --golden-output is required when using --generate-golden", file=sys.stderr)
                return False

            # Load scenarios from the tests file
            try:
                scenarios = regression_service.load_regression_tests_from_file(args.tests, args.team, start_date)
            except Exception as e:
                print(f"Error loading regression tests: {e}", file=sys.stderr)
                return False

            # Apply global threshold if specified
            if args.threshold > 0:
                for scenario in scenarios:
                    for metric in scenario.tolerance_thresholds:
                        scenario.tolerance_thresholds[metric] = args.threshold

            # Generate golden outputs
            try:
                regression_service.save_golden_outputs(scenarios, args.golden_output)
                print(f"Generated golden outputs for {len(scenarios)} scenarios and saved to {args.golden_output}")
                return True
            except Exception as e:
                print(f"Error generating golden outputs: {e}", file=sys.stderr)
                return False

        # Run regression tests
        try:
            # Load regression tests
            scenarios = regression_service.load_regression_tests_from_file(args.tests, args.team, start_date)

            # Apply global threshold if specified
            if args.threshold > 0:
                for scenario in scenarios:
                    for metric in scenario.tolerance_thresholds:
                        scenario.tolerance_thresholds[metric] = args.threshold

            print(f"Running {len(scenarios)} regression tests for team '{args.team}'...")

            # Run tests
            results = regression_service.run_regression_tests(scenarios)

            # Count passed/failed tests
            passed = sum(1 for r in results if r.passed)
            failed = len(results) - passed

            print(f"\nRegression Test Results: {passed} passed, {failed} failed")

            # Create results table
            table_data = []
            for result in results:
                status = "PASSED" if result.passed else "FAILED"
                if result.error_message:
                    reason = result.error_message
                elif not result.passed:
                    failed_metrics = result.get_failed_metrics()
                    reason = ", ".join(f"{m}: expected={e}, actual={a}" for m, (e, a) in failed_metrics.items())
                else:
                    reason = ""

                table_data.append([result.scenario_name, status, reason])

            # Print results table
            print("\n" + tabulate(
                table_data,
                headers=["Scenario", "Status", "Reason"],
                tablefmt="grid"
            ))

            # Save detailed results to file if output directory is specified
            if args.output_dir:
                os.makedirs(args.output_dir, exist_ok=True)

                # Save summary to file
                summary_file = os.path.join(args.output_dir, "regression_test_summary.txt")
                with open(summary_file, 'w') as f:
                    f.write(f"Regression Test Results: {passed} passed, {failed} failed\n\n")
                    f.write(tabulate(
                        table_data,
                        headers=["Scenario", "Status", "Reason"],
                        tablefmt="grid"
                    ))

                print(f"\nSaved summary to {summary_file}")

                # Save detailed results for each scenario
                for i, result in enumerate(results):
                    if not result.passed:
                        detail_file = os.path.join(args.output_dir, f"regression_test_{result.scenario_name}.txt")
                        with open(detail_file, 'w') as f:
                            f.write(f"Regression Test: {result.scenario_name}\n")
                            f.write(f"Status: {'PASSED' if result.passed else 'FAILED'}\n")

                            if result.error_message:
                                f.write(f"Error: {result.error_message}\n")
                            else:
                                f.write("\nMetrics Comparison:\n")
                                metrics_table = []
                                for metric, (expected, actual, passed) in result.metrics_results.items():
                                    if expected is not None:  # Only include metrics with expected values
                                        status = "PASSED" if passed else "FAILED"
                                        metrics_table.append([metric, expected, actual, status])

                                f.write(tabulate(
                                    metrics_table,
                                    headers=["Metric", "Expected", "Actual", "Status"],
                                    tablefmt="grid"
                                ))

                        print(f"Saved detailed results for '{result.scenario_name}' to {detail_file}")

            # Return True if all tests passed, False otherwise
            return passed == len(results)

        except Exception as e:
            print(f"Error running regression tests: {e}", file=sys.stderr)
            return False

    except Exception as e:
        print(f"Error handling regression test command: {e}", file=sys.stderr)
        return False

def handle_simulation(args, session):
    """
    Handle the simulation command.

    Args:
        args: Command line arguments
        session: Database session
    """
    try:
        import json
        from domain.value_objects.scenario import Scenario
        from domain.services.scenario_simulator import ScenarioSimulator
        from domain.services.scenario_comparator import ScenarioComparator

        # Setup repositories
        employee_repository = SqlAlchemyEmployeeRepository(session)
        workstation_repository = SqlAlchemyWorkstationRepository(session)
        team_repository = SqlAlchemyTeamRepository(session)
        schedule_repository = SqlAlchemyScheduleRepository(session)
        schedule_service = ScheduleService()

        # Get team by name
        team = team_repository.get_by_name(args.team)
        if not team:
            print(f"Error: Team '{args.team}' not found", file=sys.stderr)
            return False

        # Parse start date
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format. Use YYYY-MM-DD", file=sys.stderr)
            return False

        # Load scenarios from JSON file
        try:
            with open(args.scenarios, 'r') as f:
                scenarios_data = json.load(f)
        except Exception as e:
            print(f"Error loading scenarios file: {e}", file=sys.stderr)
            return False

        # Create scenario objects
        scenarios = []
        for i, scenario_data in enumerate(scenarios_data):
            scenario = Scenario(
                name=scenario_data.get('name', f"Scenario_{i+1}"),
                team_id=team.id,
                start_date=start_date,
                periods_per_day=args.periods,
                call_ins=scenario_data.get('call_ins', []),
                offline=scenario_data.get('offline', []),
                force_complete=scenario_data.get('force_complete', False),
                metadata=scenario_data.get('metadata', {})
            )
            scenarios.append(scenario)

        print(f"Running {len(scenarios)} scenarios for team '{args.team}'...")

        # Create simulator and run scenarios
        simulator = ScenarioSimulator(
            employee_repository=employee_repository,
            workstation_repository=workstation_repository,
            team_repository=team_repository,
            schedule_service=schedule_service,
            schedule_repository=schedule_repository,
            session=session
        )

        results = simulator.run_scenarios(scenarios)

        print(f"Successfully ran {len(results)} scenarios.")

        # Compare results
        if args.advanced:
            # Use advanced analytics
            from domain.analytics.scenario_analytics import ScenarioAnalytics
            analytics = ScenarioAnalytics(results, session=session)
            analytics.generate_advanced_analytics(args.output_dir)
            print(f"Generated advanced analytics in: {args.output_dir}")

            # Get comparison report for summary table
            comparison_df = analytics.comparator.generate_comparison_report(os.path.join(args.output_dir, "scenario_comparison.csv"))
        else:
            # Use basic comparator
            comparator = ScenarioComparator(results)

            # Generate comparison report
            report_path = os.path.join(args.output_dir, "scenario_comparison.csv")
            comparison_df = comparator.generate_comparison_report(report_path)
            print(f"Generated comparison report: {report_path}")

            # Generate comparison charts
            comparator.generate_comparison_charts(args.output_dir)
            print(f"Generated comparison charts in: {args.output_dir}")

            # Generate scenario heatmap
            comparator.generate_scenario_heatmap(args.output_dir)
            print(f"Generated scenario heatmap in: {args.output_dir}")

        # Print summary table
        print("\nScenario Comparison Summary:")
        summary_cols = ['Scenario', 'Total Assignments']
        if 'Min Employee Assignments' in comparison_df.columns:
            summary_cols.extend(['Min Employee Assignments', 'Max Employee Assignments', 'Avg Employee Assignments'])
        print(tabulate(comparison_df[summary_cols].values.tolist(), 
                      headers=summary_cols, 
                      tablefmt="grid"))

        return True

    except Exception as e:
        print(f"Error running simulations: {e}", file=sys.stderr)
        return False

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
        session, employee_repository, workstation_repository, team_repository, schedule_service, assignment_repository, work_history_repository, aro_repository, aro_service, aro_graph_service, schedule_repository = setup_dependencies()

        try:
            if args.command == 'generate':
                # Create handler
                handler = GenerateScheduleHandler(
                    employee_repository=employee_repository,
                    workstation_repository=workstation_repository,
                    team_repository=team_repository,
                    assignment_repository=assignment_repository,
                    schedule_service=schedule_service,
                    schedule_repository=schedule_repository,
                    session=session
                )

                # Parse start_date if it's a string
                start_date = args.start_date
                if isinstance(start_date, str):
                    try:
                        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                    except ValueError:
                        print(f"Error: Invalid start date format. Use YYYY-MM-DD", file=sys.stderr)
                        sys.exit(1)

                # Get teams based on the provided arguments
                teams = []
                if args.team:
                    # Get team by name
                    try:
                        team = team_repository.get_by_name(args.team)
                        if not team:
                            raise ValueError(f"Team '{args.team}' not found")
                        teams = [team]
                    except ValueError as e:
                        print(f"Error: {e}", file=sys.stderr)
                        sys.exit(1)
                elif args.group:
                    # Get teams by group name
                    teams = team_repository.get_by_group_name(args.group)
                    if not teams:
                        print(f"Error: No teams found in group '{args.group}'", file=sys.stderr)
                        sys.exit(1)
                    print(f"Generating schedules for {len(teams)} teams in group '{args.group}'")
                elif args.department:
                    # Get teams by department name
                    teams = team_repository.get_by_department_name(args.department)
                    if not teams:
                        print(f"Error: No teams found in department '{args.department}'", file=sys.stderr)
                        sys.exit(1)
                    print(f"Generating schedules for {len(teams)} teams in department '{args.department}'")

                # Initialize assignments list
                all_assignments = []

                # Generate schedules for each team
                for team in teams:
                    print(f"\nGenerating schedule for team '{team.name}'...")

                    # Create command for this team
                    command = GenerateScheduleCommand(
                        team_id=team.id,
                        start_date=start_date,
                        periods_per_day=args.periods,
                        call_ins=args.call_ins,
                        offline=args.offline,
                        force_complete=args.force_complete
                    )

                    # Handle command
                    team_assignments = handler.handle(command)

                    if team_assignments:
                        print(f"Generated {len(team_assignments)} assignments for team '{team.name}'")
                        all_assignments.extend(team_assignments)
                    else:
                        print(f"No assignments generated for team '{team.name}'")

                # Set assignments to all_assignments for display later
                assignments = all_assignments
            elif args.command == 'assign':
                # Handle manual assignment
                handle_manual_assignment(args, session)
            elif args.command == 'simulate':
                # Handle simulation command
                handle_simulation(args, session)
            elif args.command == 'regression-test':
                # Handle regression test command
                handle_regression_test(args, session)
            elif args.command == 'aro':
                # Handle ARO management commands
                if not hasattr(args, 'aro_command') or not args.aro_command:
                    print("Error: No ARO command specified. Use 'aro assign', 'aro remove', or 'aro optimize'.", file=sys.stderr)
                    sys.exit(1)
                handle_aro_assignment(args, session, aro_service, aro_graph_service)
            else:
                print("Error: No command specified. Use 'generate', 'assign', 'simulate', 'regression-test', or 'aro'.", file=sys.stderr)
                sys.exit(1)

            # Display results for generate command
            if args.command == 'generate':
                if not assignments:
                    print("\nNo assignments generated.")
                else:
                    print(f"\nGenerated a total of {len(assignments)} assignments across all teams")
                    print("Assignments have been saved to the employee_work_history table.")

                    # Verify assignments were saved to the database
                    try:
                        # Get the start date from the first team's command
                        start_date = start_date  # We already have this from earlier
                        end_date = start_date  # For now, just verify the first day

                        # Get work history entries for the date range
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

                    # Group assignments by team and date
                    assignments_by_team_and_date = {}
                    for assignment in assignments:
                        team_id = assignment.employee.team_id
                        date_key = assignment.period.date

                        if team_id not in assignments_by_team_and_date:
                            assignments_by_team_and_date[team_id] = {}

                        if date_key not in assignments_by_team_and_date[team_id]:
                            assignments_by_team_and_date[team_id][date_key] = []

                        assignments_by_team_and_date[team_id][date_key].append(assignment)

                    # Print schedule for each team and date
                    for team_id, dates in assignments_by_team_and_date.items():
                        team = team_repository.get(team_id)
                        if team:
                            print(f"\n\n=== Schedule for Team: {team.name} ===")

                            # Get employees and workstations for this team
                            employees = employee_repository.get_by_team_id(team_id)
                            workstations = workstation_repository.get_by_team_id(team_id)

                            # Print schedule for each date for this team
                            for date_key in sorted(dates.keys()):
                                print(format_schedule_table(
                                    dates[date_key], 
                                    employees, 
                                    workstations, 
                                    args.periods, 
                                    date_key,
                                    args.call_ins,
                                    args.offline
                                ))
                                print()  # Add some space between dates

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
