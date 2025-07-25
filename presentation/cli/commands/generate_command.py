import sys
from typing import Optional, Any, Dict, List, Tuple, cast
from datetime import datetime, date
from collections import defaultdict

from domain.contexts.employee_management.entities.employee import Employee
from infrastructure.repositories.employee_management.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from infrastructure.repositories.workstation_management.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from infrastructure.repositories.employee_management.sqlalchemy_team_repository import SqlAlchemyTeamRepository
from infrastructure.repositories.assignment.sqlalchemy_assignment_repository import SqlAlchemyAssignmentRepository
from infrastructure.repositories.employee_management.sqlalchemy_employee_work_history_repository import SqlAlchemyEmployeeWorkHistoryRepository
from domain.models.EmployeeWorkHistoryModel import WorkHistoryStatus
from infrastructure.repositories.scheduling.sqlalchemy_schedule_repository import SqlAlchemyScheduleRepository
from domain.services.schedule_service import ScheduleService
from domain.services.aro_service import AROService
from domain.contexts.assignment.services.aro_graph_service import AROGraphService
from infrastructure.scheduling.schedule_data_service import ScheduleDataService
from presentation.cli.utils.formatting import format_schedule_table
from utilities.logging_factory import get_logger, RateLimitedLogger

logger = cast(RateLimitedLogger, get_logger("presentation.cli.commands.generate_command", rate_limit=True))

def handle_generate(
    args: Any, 
    dependencies: Tuple[
        Any,  # session_factory
        SqlAlchemyEmployeeRepository,
        SqlAlchemyWorkstationRepository,
        SqlAlchemyTeamRepository,
        ScheduleService,
        SqlAlchemyAssignmentRepository,
        SqlAlchemyEmployeeWorkHistoryRepository,
        Any,
        AROService,
        AROGraphService,
        SqlAlchemyScheduleRepository
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
        "generate",
        "start"
    )

    try:
        (
            session_factory, 
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

        teams = schedule_service._get_teams_for_generation(args, team_repository)

        start_date = args.start_date
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Invalid start date format. Use YYYY-MM-DD")

        # Prefetch data for teams
        schedule_data_service = ScheduleDataService(
            employee_repository=employee_repository,
            workstation_repository=workstation_repository,
            team_repository=team_repository,
            aro_repository=aro_repository,
            session_factory=session_factory,
            work_history_repository=work_history_repository
        )

        prefetched_data = schedule_data_service.prefetch_for_teams(
            team_ids=[team.id for team in teams],
            start_date=start_date,
            periods=args.periods
        )

        # Call the schedule service to handle all orchestration
        result = schedule_service.orchestrate_team_schedule_generation(
            args=args,
            teams=teams,
            prefetched_data=prefetched_data
        )

        # Diagnostic: Print assignment counts per team before saving
        assignments_by_team = defaultdict(list)
        for assignment in result["assignments"]:
            assignments_by_team[getattr(assignment, 'team_id', getattr(assignment, 'employee', None) and getattr(assignment.employee, 'team_id', None))].append(assignment)
        print(f"\n[DIAGNOSTIC] Total assignments to save: {len(result['assignments'])}")
        for team_id, assignments in assignments_by_team.items():
            print(f"[DIAGNOSTIC] Team {team_id}: {len(assignments)} assignments")
        print(f"[DIAGNOSTIC] Team IDs in assignments: {list(assignments_by_team.keys())}")

        if result["success"]:
            try:
                logger.info(
                    f"Starting save_all operation for {len(result['assignments'])} assignments (batch_size: 200)",
                    "save_all_start",
                    f"assignments_{len(result['assignments'])}"
                )
                print("[DIAGNOSTIC] Calling save_all...")
                
                # Validate assignment data consistency before save_all
                logger.info("Validating assignment data consistency before save_all", "assignment_validation", "pre_save_validation")
                for i, assignment in enumerate(result["assignments"][:5]):  # Log first 5 for debugging
                    logger.debug(
                        f"Assignment {i+1}: Employee {getattr(assignment.employee, 'id', 'MISSING')} ({getattr(assignment.employee, 'name', 'MISSING')}) -> Workstation {getattr(assignment.workstation, 'id', 'MISSING')} ({getattr(assignment.workstation, 'name', 'MISSING')}) on {getattr(assignment.period, 'date', 'MISSING')} period {getattr(assignment.period, 'period', 'MISSING')}",
                        "assignment_data_validation",
                        f"assignment_{i+1}"
                    )
                
                # Check return value
                save_success = assignment_repository.save_all(result["assignments"], batch_size=200)
                
                if save_success:
                    logger.info(
                        f"save_all completed successfully - all {len(result['assignments'])} assignments saved",
                        "save_all_success",
                        f"assignments_{len(result['assignments'])}"
                    )
                    print("[DIAGNOSTIC] save_all completed successfully - all assignments saved.")
                else:
                    logger.warning(
                        f"save_all completed but not all assignments were saved (total: {len(result['assignments'])})",
                        "save_all_partial_failure",
                        f"assignments_{len(result['assignments'])}"
                    )
                    print("[DIAGNOSTIC] save_all completed but some assignments failed validation or saving.")
                    
            except Exception as e:
                logger.error(
                    f"Exception during save_all: {e} (type: {type(e).__name__}, assignments: {len(result['assignments'])})",
                    "save_all_exception",
                    f"assignments_{len(result['assignments'])}"
                )
                print(f"[DIAGNOSTIC] Exception during save_all: {e}")
                import traceback
                traceback.print_exc()

        if not result["success"]:
            print(f"Error: {result['error']}", file=sys.stderr)
            return False

        # Display performance metrics
        print(f"\nPerformance: Generated in {result['metrics']['execution_time']:.2f} seconds")
        print(f"Generated {result['metrics']['assignment_count']} assignments for {result['metrics']['team_count']} teams")

        # Display the generated schedules
        display_generation_results(
            result["assignments"],
            result["teams"],
            team_repository,
            employee_repository,
            workstation_repository,
            args,
            work_history_repository,
            start_date,
            prefetched_data['aro_assignments_by_team'],
            prefetched_data['aro_assignments_by_team_period'],
            prefetched_data['aro_assignments_by_employee'],
            prefetched_data['employees_by_id'],
            result["schedule_metadata"],
            aro_service
        )

        return True

    except Exception as e:
        error_msg = f"Error in CLI handler: {e}"
        logger.error(
            error_msg,
            "generate",
            "exception"
        )
        print(error_msg, file=sys.stderr)
        return False

# Function removed as it's now handled by ScheduleService._get_teams_for_generation

def display_generation_results(
    assignments: List[Any],
    teams: List[Any],
    team_repository: SqlAlchemyTeamRepository,
    employee_repository: SqlAlchemyEmployeeRepository,
    workstation_repository: SqlAlchemyWorkstationRepository,
    args: Any,
    work_history_repository: SqlAlchemyEmployeeWorkHistoryRepository,
    start_date: date,
    aro_assignments_by_team: Optional[Dict[int, Dict[str, List[int]]]] = None,
    aro_assignments_by_team_period: Optional[Dict[int, Dict[int, Dict[str, List[int]]]]] = None,
    aro_assignments_by_employee: Optional[Dict[int, List[Any]]] = None,
    employees_by_id: Optional[Dict[int, Employee]] = None,
    schedule_metadata: Optional[List[Dict]] = None,
    aro_service: Optional[Any] = None
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
        :param start_date:
        :param work_history_repository:
        :param args:
        :param workstation_repository:
        :param employee_repository:
        :param teams:
        :param team_repository:
        :param assignments:
        :param employees_by_id:
        :param aro_assignments_by_employee:
        :param aro_assignments_by_team_period:
        :param aro_assignments_by_team:
    """
    if not assignments:
        print("\nNo assignments generated.")
        return

    try:
        logger.debug(
            "Verifying assignments in database", 
            event_type="verification", 
            identifier="assignments"
        )

        # Get the start date from the first team's command
        end_date = start_date  # For now, just verify the first day

        # Get work history entries for the date range that were generated in the current run
        work_history_entries, total_count = work_history_repository.get_filtered(
            start_date=start_date,
            end_date=end_date,
            status=WorkHistoryStatus.GENERATED,
            limit=10000  # Set high limit to capture all assignments
        )
        saved_count = len(work_history_entries)
        logger.debug(
            f"Found {saved_count} work history entries for date range that were generated in the current run", 
            event_type="verification", 
            identifier="assignments"
        )
        """
        # Print some debug information about the work history entries
        print(f"\nDEBUG: Found {saved_count} work history entries in the database for date range {start_date} to {end_date} that were generated in the current run")
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
        """

        # Since we're already filtering by status=GENERATED, we just need to match the entries with assignments
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

    # Group assignments by workstation's team and date (not employee's team)
    # This ensures ARO assignments are displayed with the team they're working for
    assignments_by_team_and_date = {}
    for assignment in assignments:
        # Use workstation's team_id instead of employee's team_id
        workstation_team_id = assignment.workstation.team_id
        date_key = assignment.period.date

        if workstation_team_id not in assignments_by_team_and_date:
            assignments_by_team_and_date[workstation_team_id] = {}

        if date_key not in assignments_by_team_and_date[workstation_team_id]:
            assignments_by_team_and_date[workstation_team_id][date_key] = []

        assignments_by_team_and_date[workstation_team_id][date_key].append(assignment)

    # Print schedule for each team and date
    for team_id, dates in assignments_by_team_and_date.items():
        team = team_repository.get(team_id)
        if team:
            print(f"\n\n=== Schedule: 1 for Team: {team.name} ===")

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

    # Display available AROs for teams that failed to find solutions
    if schedule_metadata and aro_service:
        failed_teams = [metadata for metadata in schedule_metadata if metadata.get("status") == "failed"]
        
        if failed_teams:
            print("\n" + "="*80)
            print("AVAILABLE AROs FOR TEAMS AFFECTED BY CALL-INS")
            print("="*80)
            
            for failed_metadata in failed_teams:
                team_id = failed_metadata.get("team_id")
                team_name = failed_metadata.get("team_name", f"Team {team_id}")
                error_message = failed_metadata.get("error_message", "No solution found")
                
                print(f"\n--- Team: {team_name} (ID: {team_id}) ---")
                print(f"Issue: {error_message}")
                
                # Get workstations for this team
                workstations = workstation_repository.get_by_team_id(team_id)
                
                if workstations:
                    # Get available AROs for this team's workstations
                    try:
                        aro_mapping = aro_service.get_workstation_aro_mapping(
                            team_id=team_id,
                            period=1,  # Check for period 1 as an example
                            assignment_date=start_date,
                            empty_workstations=workstations
                        )
                        
                        if aro_mapping:
                            print("Available ARO employees by workstation:")
                            for workstation_id, aro_employee_ids in aro_mapping.items():
                                # Find the workstation name
                                workstation = next((ws for ws in workstations if ws.id == workstation_id), None)
                                workstation_name = workstation.name if workstation else f"Workstation {workstation_id}"
                                
                                if aro_employee_ids:
                                    print(f"  {workstation_name}:")
                                    for emp_id in aro_employee_ids:
                                        if employees_by_id and emp_id in employees_by_id:
                                            employee = employees_by_id[emp_id]
                                            home_team = team_repository.get(employee.team_id)
                                            home_team_name = home_team.name if home_team else f"Team {employee.team_id}"
                                            print(f"    - {employee.name} (from {home_team_name})")
                                        else:
                                            # Fallback: get employee from repository
                                            employee = employee_repository.get(emp_id)
                                            if employee:
                                                home_team = team_repository.get(employee.team_id)
                                                home_team_name = home_team.name if home_team else f"Team {employee.team_id}"
                                                print(f"    - {employee.name} (from {home_team_name})")
                        else:
                            print("No available ARO employees found for this team's workstations.")
                            
                    except Exception as e:
                        print(f"Error getting ARO suggestions: {e}")
                else:
                    print("No workstations found for this team.")
            
            print("\n" + "="*80)
