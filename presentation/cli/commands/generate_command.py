"""
Generate schedule command handling for the CLI application.
"""
import sys
import time
from typing import Optional, Any, Dict, List, Tuple, Union
from datetime import datetime
from sqlalchemy.orm import Session

from domain.entities.employee import Employee

from application.commands.generate_schedule_command import GenerateScheduleCommand
from application.commands.generate_schedule_handler import GenerateScheduleHandler
from domain.repositories.implementations.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from domain.repositories.implementations.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from domain.repositories.implementations.sqlalchemy_team_repository import SqlAlchemyTeamRepository
from domain.repositories.implementations.sqlalchemy_assignment_repository import SqlAlchemyAssignmentRepository
from domain.repositories.implementations.sqlalchemy_employee_work_history_repository import SqlAlchemyEmployeeWorkHistoryRepository
from domain.repositories.implementations.sqlalchemy_schedule_repository import SqlAlchemyScheduleRepository
from domain.repositories.implementations.sqlalchemy_aro_assignment_repository import SqlAlchemyAROAssignmentRepository
from domain.services.schedule_service import ScheduleService
from domain.services.aro_service import AROService
from domain.contexts.assignment.services.aro_graph_service import AROGraphService
from infrastructure.scheduling.schedule_data_service import ScheduleDataService
from infrastructure.scheduling.schedule_coordinator import ScheduleCoordinator
from domain.events.publisher import DomainEventPublisher
from presentation.cli.utils.formatting import format_schedule_table
from utilities.logging_factory import get_logger

# Create a logger for this module
logger = get_logger("presentation.cli.commands.generate_command", rate_limit=True)

def handle_generate(
    args: Any, 
    dependencies: Tuple[
        Session,  # session
        SqlAlchemyEmployeeRepository,  # employee_repository
        SqlAlchemyWorkstationRepository,  # workstation_repository
        SqlAlchemyTeamRepository,  # team_repository
        ScheduleService,  # schedule_service
        SqlAlchemyAssignmentRepository,  # assignment_repository
        SqlAlchemyEmployeeWorkHistoryRepository,  # work_history_repository
        Any,  # aro_repository
        AROService,  # aro_service
        AROGraphService,  # aro_graph_service
        SqlAlchemyScheduleRepository  # schedule_repository
    ],
    query_count: int = 0
) -> bool:
    """
    Handle the generate schedule command.

    Args:
        args: Command line arguments
        dependencies: Tuple of dependencies
        query_count: Initial query count for performance measurement

    Returns:
        bool: True if the operation was successful, False otherwise
    """
    logger.info(
        f"Handling generate command", 
        event_type="generate", 
        identifier="start"
    )

    try:
        # Unpack dependencies
        (
            session, 
            employee_repository, 
            workstation_repository, 
            team_repository, 
            schedule_service, 
            assignment_repository, 
            work_history_repository, 
            aro_repository, 
            aro_service, 
            aro_graph_service, 
            schedule_repository
        ) = dependencies

        # Parse start_date if it's a string
        start_date = args.start_date
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                error_msg = f"Error: Invalid start date format. Use YYYY-MM-DD"
                logger.error(
                    error_msg, 
                    event_type="generate", 
                    identifier="date_parsing"
                )
                print(error_msg, file=sys.stderr)
                return False

        # Get teams based on the provided arguments
        teams = get_teams_for_generation(args, team_repository)
        if not teams:
            return False

        # Start performance measurement
        start_time = time.time()
        logger.info(
            f"Starting performance measurement", 
            event_type="performance_measurement", 
            identifier="start"
        )

        # Create the necessary services and components
        logger.debug(
            "Creating services and components", 
            event_type="initialization", 
            identifier="services"
        )

        # Create a domain event publisher
        event_publisher = DomainEventPublisher()

        # Create a schedule data service
        schedule_data_service = ScheduleDataService(
            employee_repository=employee_repository,
            workstation_repository=workstation_repository,
            team_repository=team_repository,
            aro_repository=aro_repository,
            session=session
        )

        # Create a handler
        handler = GenerateScheduleHandler(
            employee_repository=employee_repository,
            workstation_repository=workstation_repository,
            team_repository=team_repository,
            assignment_repository=assignment_repository,
            schedule_service=schedule_service,
            schedule_repository=schedule_repository,
            session=session,
            aro_service=aro_service,
            aro_graph_service=aro_graph_service
        )

        # Create a schedule coordinator
        coordinator = ScheduleCoordinator(
            schedule_handler=handler,
            schedule_data_service=schedule_data_service,
            event_publisher=event_publisher
        )

        # Create commands for each team
        commands = []
        for team in teams:
            command = GenerateScheduleCommand(
                team_id=team.id,
                start_date=start_date,
                periods_per_day=args.periods,
                call_ins=args.call_ins,
                offline=args.offline,
                force_complete=args.force_complete
            )
            commands.append(command)

        # Generate schedules using the coordinator
        logger.info(
            f"Generating schedules for {len(teams)} teams", 
            event_type="schedule_generation", 
            identifier="start"
        )
        print(f"Generating schedules for {len(teams)} teams...")

        all_assignments_by_team = coordinator.generate_schedules(commands)

        # Flatten assignments for saving
        all_assignments = []
        for team_assignments in all_assignments_by_team.values():
            all_assignments.extend(team_assignments)

        # Save all assignments in a single batch
        logger.info(
            f"Saving {len(all_assignments)} assignments", 
            event_type="save_assignments", 
            identifier="start"
        )
        save_success = assignment_repository.save_all(all_assignments)

        # Update work history repository with these assignments
        logger.info(
            f"Updating work history for {len(all_assignments)} assignments", 
            event_type="update_work_history", 
            identifier="start"
        )
        for assignment in all_assignments:
            try:
                work_history_repository.create(
                    employee_id=assignment.employee.id,
                    workstation_id=assignment.workstation.id,
                    date_obj=start_date,
                    period=assignment.period.period,
                    is_generated=True
                )
            except Exception as e:
                logger.error(
                    f"Error adding work history entry: {e}",
                    event_type="work_history_entry_error",
                    identifier=f"employee_{assignment.employee.id}_period_{assignment.period.period}"
                )

        # Calculate and log performance metrics
        end_time = time.time()
        execution_time = end_time - start_time

        logger.info(
            f"Performance metrics: {query_count} queries in {execution_time:.2f} seconds",
            event_type="performance_measurement",
            identifier="complete"
        )

        print(f"\nPerformance: {query_count} queries executed in {execution_time:.2f} seconds")
        print(f"Generated {len(all_assignments)} assignments for {len(teams)} teams using event-based coordination")

        # Prefetch data for display
        prefetched_data = schedule_data_service.prefetch_for_teams(
            team_ids=[team.id for team in teams],
            start_date=start_date,
            periods=args.periods
        )

        # Display the generated schedules
        display_generation_results(
            all_assignments,
            teams,
            team_repository,
            employee_repository,
            workstation_repository,
            args,
            work_history_repository,
            start_date,
            prefetched_data['aro_assignments_by_team'],
            prefetched_data['aro_assignments_by_team_period'],
            prefetched_data['aro_assignments_by_employee'],
            prefetched_data['employees_by_id']
        )

        return True

    except Exception as e:
        error_msg = f"Error generating schedule: {e}"
        logger.error(
            error_msg,
            event_type="generate",
            identifier="exception"
        )
        return False

def get_teams_for_generation(args: Any, team_repository: SqlAlchemyTeamRepository) -> List[Any]:
    """
    Get teams based on the provided arguments.

    Args:
        args: Command line arguments
        team_repository: Repository for team data

    Returns:
        List of teams to generate schedules for
    """
    teams = []

    if args.team:
        # Get team by name
        try:
            team = team_repository.get_by_name(args.team)
            if not team:
                error_msg = f"Error: Team '{args.team}' not found"
                logger.error(
                    error_msg, 
                    event_type="team_lookup", 
                    identifier=args.team
                )
                print(error_msg, file=sys.stderr)
                return []
            teams = [team]
        except ValueError as e:
            error_msg = f"Error: {e}"
            logger.error(
                error_msg, 
                event_type="team_lookup", 
                identifier=args.team
            )
            print(error_msg, file=sys.stderr)
            return []
    elif args.group:
        # Get teams by group name
        teams = team_repository.get_by_group_name(args.group)
        if not teams:
            error_msg = f"Error: No teams found in group '{args.group}'"
            logger.error(
                error_msg, 
                event_type="group_lookup", 
                identifier=args.group
            )
            print(error_msg, file=sys.stderr)
            return []
        logger.info(
            f"Generating schedules for {len(teams)} teams in group '{args.group}'", 
            event_type="schedule_generation", 
            identifier=args.group
        )
        print(f"Generating schedules for {len(teams)} teams in group '{args.group}'")
    elif args.department:
        # Get teams by department name
        teams = team_repository.get_by_department_name(args.department)
        if not teams:
            error_msg = f"Error: No teams found in department '{args.department}'"
            logger.error(
                error_msg, 
                event_type="department_lookup", 
                identifier=args.department
            )
            print(error_msg, file=sys.stderr)
            return []
        logger.info(
            f"Generating schedules for {len(teams)} teams in department '{args.department}'", 
            event_type="schedule_generation", 
            identifier=args.department
        )
        print(f"Generating schedules for {len(teams)} teams in department '{args.department}'")

    return teams

def display_generation_results(
    assignments: List[Any],
    teams: List[Any],
    team_repository: SqlAlchemyTeamRepository,
    employee_repository: SqlAlchemyEmployeeRepository,
    workstation_repository: SqlAlchemyWorkstationRepository,
    args: Any,
    work_history_repository: SqlAlchemyEmployeeWorkHistoryRepository,
    start_date: datetime.date,
    aro_assignments_by_team: Optional[Dict[int, Dict[str, List[int]]]] = None,
    aro_assignments_by_team_period: Optional[Dict[int, Dict[int, Dict[str, List[int]]]]] = None,
    aro_assignments_by_employee: Optional[Dict[int, List[Any]]] = None,
    employees_by_id: Optional[Dict[int, Employee]] = None
) -> None:
    """
    Display the results of schedule generation.

    Args:
        assignments: List of generated assignments
        teams: List of teams
        team_repository: Repository for team data
        employee_repository: Repository for employee data
        workstation_repository: Repository for workstation data
        args: Command line arguments
        work_history_repository: Repository for work history data
        start_date: Start date of the schedule
    """
    if not assignments:
        print("\nNo assignments generated.")
        return

    print(f"\nGenerated a total of {len(assignments)} assignments across all teams")
    print("Assignments have been saved to the employee_work_history table.")

    # Verify assignments were saved to the database
    try:
        logger.debug(
            "Verifying assignments in database", 
            event_type="verification", 
            identifier="assignments"
        )

        # Get the start date from the first team's command
        end_date = start_date  # For now, just verify the first day

        # Get work history entries for the date range
        work_history_entries = work_history_repository.get_by_date_range(start_date, end_date)
        saved_count = len(work_history_entries)
        logger.debug(
            f"Found {saved_count} work history entries for date range", 
            event_type="verification", 
            identifier="assignments"
        )

        # Print some debug information about the work history entries
        print(f"\nDEBUG: Found {saved_count} work history entries in the database for date range {start_date} to {end_date}")
        for i, entry in enumerate(work_history_entries[:5]):  # Print first 5 entries
            print(f"  Entry {i+1}: Employee ID: {entry.employee_id}, Workstation ID: {entry.workstation_id}, Date: {entry.worked_date}, Period: {entry.work_period}")
        if saved_count > 5:
            print(f"  ... and {saved_count - 5} more entries")

        # Print some debug information about the assignments
        print(f"\nDEBUG: Generated {len(assignments)} assignments")
        for i, a in enumerate(assignments[:5]):  # Print first 5 assignments
            print(f"  Assignment {i+1}: Employee ID: {a.employee.id}, Workstation ID: {a.workstation.id}, Date: {a.period.date}, Period: {a.period.period}")
        if len(assignments) > 5:
            print(f"  ... and {len(assignments) - 5} more assignments")

        # Count only the entries that were generated by the scheduler
        generated_entries = [entry for entry in work_history_entries
                            if any(entry.employee_id == a.employee.id and
                                   entry.workstation_id == a.workstation.id and
                                   entry.worked_date == a.period.date and
                                   entry.work_period == a.period.period
                                   for a in assignments)]

        verification_msg = f"Verified {len(generated_entries)} of {len(assignments)} assignments in the database."
        logger.info(
            verification_msg, 
            event_type="verification", 
            identifier="assignments"
        )
        print(verification_msg)

        if len(generated_entries) != len(assignments):
            warning_msg = "Warning: Not all assignments were saved to the database."
            logger.warning(
                warning_msg, 
                event_type="verification", 
                identifier="assignments"
            )
            print(warning_msg)

            # Print some debug information about the missing assignments
            print("\nDEBUG: Checking which assignments are missing from the database")
            missing_count = 0
            for a in assignments:
                found = False
                for entry in work_history_entries:
                    if (entry.employee_id == a.employee.id and
                        entry.workstation_id == a.workstation.id and
                        entry.worked_date == a.period.date and
                        entry.work_period == a.period.period):
                        found = True
                        break
                if not found:
                    missing_count += 1
                    if missing_count <= 5:  # Print first 5 missing assignments
                        print(f"  Missing: Employee ID: {a.employee.id} ({a.employee.name}), Workstation ID: {a.workstation.id} ({a.workstation.name}), Date: {a.period.date}, Period: {a.period.period}")
            if missing_count > 5:
                print(f"  ... and {missing_count - 5} more missing assignments")
    except Exception as e:
        warning_msg = f"Warning: Could not verify assignments in database: {e}"
        logger.warning(
            warning_msg, 
            event_type="verification", 
            identifier="assignments"
        )
        print(warning_msg)

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
                    args.offline,
                    aro_assignments_by_team,
                    aro_assignments_by_team_period,
                    aro_assignments_by_employee,
                    employees_by_id,
                    team_id
                ))
                print()  # Add some space between dates
