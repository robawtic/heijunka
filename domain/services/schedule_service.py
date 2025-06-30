# heijunka/domain/services/schedule_service.py
from typing import List, Dict, Set, Optional, Tuple, Any, TypeVar, cast
from datetime import date, timedelta, datetime
import logging
import time
import sys

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment
from domain.value_objects.schedule_constraint import ScheduleConstraint, ConstraintType
from domain.events import AssignmentCreated
from domain.rules.context import RuleContext
from domain.services.cp_model_builder import CPModelBuilder
from domain.services.aro_roster_service import ARORosterService
from domain.services.team_lookup_service import TeamLookupService
from domain.events.publisher import DomainEventPublisher
from application.commands.generate_schedule_command import GenerateScheduleCommand
from infrastructure.scheduling.schedule_data_service import ScheduleDataService
from domain.models.EmployeeWorkHistoryModel import WorkHistoryStatus

# Type aliases for improved readability
WorkAssignments = List[WorkAssignment]
OfflineDict = Dict[str, List[int]]

# Logger for this module
logger = logging.getLogger(__name__)


class ScheduleService:
    # Default values as class constants
    DEFAULT_PERIODS_PER_DAY = 4
    DEFAULT_SCHEDULE_ID = 1

    def __init__(self, constraints: List[ScheduleConstraint] = None,
                cp_model_builder: CPModelBuilder = None,
                aro_roster_service: ARORosterService = None,
                team_lookup_service: TeamLookupService = None):
        self.constraints = constraints or []
        self.cp_model_builder = cp_model_builder or CPModelBuilder()
        self.aro_roster_service = aro_roster_service or ARORosterService()
        self.team_lookup_service = team_lookup_service or TeamLookupService()

    def assign_employee(self, employee: Employee, workstation: Workstation,
                        period: SchedulePeriod, schedule_id: int = None,
                        schedule_repository=None) -> WorkAssignment:
        """
        Assign an employee to a workstation for a specific period

        This method delegates to the Schedule entity's create_assignment method.
        If no schedule_id is provided, a temporary schedule is created.

        Args:
            employee: The employee to assign
            workstation: The workstation to assign the employee to
            period: The period for the assignment
            schedule_id: Optional ID of an existing schedule
            schedule_repository: Optional repository for retrieving/creating schedules
                                (optional for testing/offline use)

        Returns:
            The created work assignment

        Raises:
            ValueError: If the assignment is invalid or schedule not found
        """
        from domain.entities.schedule import Schedule

        # If a schedule_id is provided, load the schedule from the repository
        if schedule_id:
            if schedule_repository:
                # Get the schedule from the repository
                schedule = schedule_repository.get_by_id(schedule_id)
                if not schedule:
                    error_msg = f"Schedule with ID {schedule_id} not found"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            else:
                # Fallback if no repository is provided
                logger.warning(f"No schedule repository provided, creating temporary schedule with ID {schedule_id}")
                schedule = Schedule(
                    id=schedule_id,
                    team_id=employee.team_id,
                    start_date=period.date,
                    periods_per_day=self.DEFAULT_PERIODS_PER_DAY,
                    status="active"
                )
        else:
            # Create a temporary schedule
            if schedule_repository:
                # Create a new schedule in the repository
                schedule = schedule_repository.create_schedule(
                    team_id=employee.team_id,
                    start_date=period.date,
                    periods_per_day=self.DEFAULT_PERIODS_PER_DAY,
                    force_complete=False
                )
            else:
                logger.warning("No schedule repository provided and no schedule_id specified, "
                              "creating in-memory schedule")
                schedule = Schedule(
                    id=self.DEFAULT_SCHEDULE_ID,
                    team_id=employee.team_id,
                    start_date=period.date,
                    periods_per_day=self.DEFAULT_PERIODS_PER_DAY,
                    status="active"
                )

        # Use the Schedule entity's create_assignment method
        return schedule.create_assignment(employee, workstation, period)

    def _parse_offline(self, offline: Optional[List[str]]) -> OfflineDict:
        """
        Parse the offline parameter to convert to the format expected by the Schedule entity.

        Args:
            offline: List of strings in format "employee:periods" specifying which 
                    employees are offline for which periods

        Returns:
            Dictionary mapping employee names to lists of period numbers
        """
        offline_dict: OfflineDict = {}
        if offline:
            for offline_str in offline:
                parts = offline_str.split(':')
                if len(parts) == 2:
                    emp_name, periods_str = parts
                    try:
                        periods = [int(p) for p in periods_str.split(',')]
                        offline_dict[emp_name] = periods
                    except ValueError:
                        logger.warning(f"Invalid period format in offline string: {offline_str}")
        return offline_dict


    def _create_schedule_entity(self, team_id: int, start_date: date, periods_per_day: int,
                          call_ins: Optional[List[str]], offline: Optional[List[str]],
                          offline_dict: OfflineDict, force_complete: bool):
        """
        Create a Schedule entity directly in memory.

        Args:
            team_id: ID of the team
            start_date: Start date of the schedule
            periods_per_day: Number of periods per day
            call_ins: List of employee names who called in (unavailable)
            offline: List of strings in format "employee:periods"
            offline_dict: Parsed offline dictionary
            force_complete: Whether to force completion of the schedule

        Returns:
            A Schedule entity
        """
        from domain.entities.schedule import Schedule

        # Create an in-memory schedule
        schedule = Schedule(
            id=self.DEFAULT_SCHEDULE_ID,
            team_id=team_id,
            start_date=start_date,
            periods_per_day=periods_per_day,
            status="active",
            call_ins=call_ins,
            offline=offline_dict,
            force_complete=force_complete
        )
        return schedule

    def _create_schedule(self, team_id: int, start_date: date, periods_per_day: int,
                          call_ins: Optional[List[str]], offline: Optional[List[str]],
                          offline_dict: OfflineDict, force_complete: bool,
                          schedule_repository=None):
        """
        Create a Schedule entity either through the repository or directly.

        @deprecated: Use _create_schedule_entity instead and handle persistence in the application layer.

        Args:
            team_id: ID of the team
            start_date: Start date of the schedule
            periods_per_day: Number of periods per day
            call_ins: List of employee names who called in (unavailable)
            offline: List of strings in format "employee:periods"
            offline_dict: Parsed offline dictionary
            force_complete: Whether to force completion of the schedule
            schedule_repository: Optional repository for creating/retrieving schedules

        Returns:
            A Schedule entity
        """
        if schedule_repository:
            # Create a new schedule in the repository
            try:
                schedule = schedule_repository.create_schedule(
                    team_id=team_id,
                    start_date=start_date,
                    periods_per_day=periods_per_day,
                    call_ins=call_ins,
                    offline=offline,
                    force_complete=force_complete
                )
                logger.info(f"Created schedule in repository with ID {schedule.id}")
                return schedule
            except Exception as e:
                logger.error(f"Error creating schedule in repository: {str(e)}")
                # Fall through to create in-memory schedule

        # Create an in-memory schedule if repository is not provided or repository creation failed
        logger.warning("Creating in-memory schedule because repository is not provided or repository creation failed")
        return self._create_schedule_entity(
            team_id=team_id,
            start_date=start_date,
            periods_per_day=periods_per_day,
            call_ins=call_ins,
            offline=offline,
            offline_dict=offline_dict,
            force_complete=force_complete
        )




    def generate_schedule(self, employees: List[Employee], workstations: List[Workstation],
                          start_date: date, periods_per_day: int,
                          team_name: str, team_id: int, call_ins: List[str] = None, offline: List[str] = None,
                          force_complete: bool = False, prefetched_data: Optional[Dict] = None) -> Tuple[List[WorkAssignment], Dict[str, Any]]:
        """
        Generate a schedule for the given employees, workstations, and time period

        This method orchestrates the schedule generation process by:
        1. Creating a Schedule entity
        2. Setting up the necessary parameters
        3. Delegating the actual generation to the Schedule entity
        4. Returning the generated assignments and work history entries

        Args:
            employees: List of employees to schedule
            workstations: List of workstations to assign employees to
            start_date: The start date of the schedule
            periods_per_day: Number of periods per day
            team_name: Name of the team to generate the schedule for
            team_id: ID of the team to generate the schedule for
            call_ins: List of employee names who called in (unavailable)
            offline: List of strings in format "employee:periods" specifying which employees are offline for which periods
            force_complete: Whether to force completion of the schedule
            prefetched_data: Optional dictionary containing prefetched data to avoid database queries

        Returns:
            Tuple containing:
            - List of work assignments
            - Dictionary with schedule metadata (id, status, etc.)
        """
        # Parse offline parameter
        offline_dict = self._parse_offline(offline)

        # Handle ARO assignments (employees leaving/joining)
        available_employees = self.aro_roster_service.handle_aro_assignments(
            employees, team_id, start_date, prefetched_data
        )

        # Create a Schedule entity
        schedule = self._create_schedule_entity(
            team_id, start_date, periods_per_day, call_ins, offline, 
            offline_dict, force_complete
        )

        # Generate assignments using the Schedule entity (DDD-compliant version)
        success = schedule.generate_assignments_ddd(
            available_employees, 
            workstations, 
            prefetched_data=prefetched_data,
            work_history_data=prefetched_data.get('work_history_data') if prefetched_data else None
        )

        # Prepare schedule metadata
        schedule_metadata = {
            "id": schedule.id,
            "status": "completed" if success else "failed",
            "error_message": schedule.error_message if not success else None,
            "team_id": team_id,
            "start_date": start_date,
            "periods_per_day": periods_per_day
        }

        if success:
            logger.info(f"Generated {len(schedule.assignments)} assignments")
            return schedule.assignments, schedule_metadata
        else:
            logger.warning(f"No solution found. Error: {schedule.error_message}")
            return [], schedule_metadata

    def generate_period_schedule(self, team_id: int, cp_input: Dict, work_history_data: Optional[Dict] = None) -> Tuple[List[WorkAssignment], Dict[str, Any]]:
        """
        Generate a schedule for a specific team and period.

        This method is used when we need to regenerate a schedule for a specific period
        after an ARO has been assigned or removed.

        Args:
            team_id: The ID of the team to generate a schedule for
            cp_input: Dictionary containing all necessary data for the CP solver:
                - employees: List of employees available for this period
                - workstations: List of workstations for this team
                - period: The period to generate a schedule for
                - start_date: The date of the schedule
                - aro_data: Dictionary of ARO assignments by employee and period
                - teams_by_id: Dictionary of teams by ID (optional)
                - work_history_data: Optional work history data for employees (required for same-day repeat penalties)
            work_history_data: Optional work history data for employees (required for same-day repeat penalties)
                This should be a dictionary mapping employee IDs to their work history entries

        Returns:
            Tuple containing:
            - List of work assignments for the specified team and period
            - Dictionary with metadata about the generation process
        """
        try:
            # Extract data from cp_input
            employees = cp_input.get("employees", [])
            workstations = cp_input.get("workstations", [])
            period = cp_input.get("period")
            start_date = cp_input.get("start_date")
            aro_data = cp_input.get("aro_data", {})

            # Use work_history_data from cp_input if provided and not passed as separate argument
            if work_history_data is None and "work_history_data" in cp_input:
                work_history_data = cp_input.get("work_history_data", {})

            if not employees or not workstations or period is None or not start_date:
                logger.error(f"Missing required data for generate_period_schedule: team_id={team_id}, period={period}")
                return [], {"success": False, "error": "Missing required data"}

            # Get team name for logging
            team_name = "Unknown"
            if "teams_by_id" in cp_input and team_id in cp_input["teams_by_id"]:
                team = cp_input["teams_by_id"][team_id]
                if hasattr(team, "name"):
                    team_name = team.name

            logger.info(f"Generating schedule for team '{team_name}' period {period}")

            # Add work history data to cp_input if provided
            if work_history_data:
                cp_input["work_history_data"] = work_history_data

            # Use the CP model builder to solve the model
            assignments = self.cp_model_builder.solve_one_period(
                employees=employees,
                workstations=workstations,
                period=period,
                team_id=team_id,
                start_date=start_date,
                aro_data=aro_data,
                team_name=team_name,
                work_history_data=work_history_data
            )

            # Prepare metadata
            metadata = {
                "success": len(assignments) > 0,
                "team_id": team_id,
                "team_name": team_name,
                "period": period,
                "start_date": start_date,
                "assignment_count": len(assignments)
            }

            if assignments:
                logger.info(f"Generated {len(assignments)} assignments for team '{team_name}' period {period}")
            else:
                logger.warning(f"No solution found for team '{team_name}' period {period}")
                metadata["error"] = "No solution found"

            return assignments, metadata

        except Exception as e:
            error_msg = f"Error generating period schedule for team {team_id}, period {cp_input.get('period')}: {str(e)}"
            logger.error(error_msg)
            return [], {"success": False, "error": error_msg}

    def generate_period_schedules(self, teams: List[Any], period: int, 
                             available_by_team_and_period: Dict,
                             prefetched_data: Dict) -> List[WorkAssignment]:
        """Generate schedules for all teams for a specific period.

        Args:
            teams: List of teams to generate schedules for
            period: The period to generate schedules for
            available_by_team_and_period: Dictionary mapping team IDs to lists of available employees for each period
            prefetched_data: Dictionary containing prefetched data to avoid database queries

        Returns:
            List of work assignments for all teams for the specified period
        """
        all_assignments = []

        # Process each team for this period
        for team in teams:
            team_id = team.id

            # Skip if no available employees for this team and period
            if team_id not in available_by_team_and_period or period not in available_by_team_and_period[team_id]:
                logger.info(f"No available employees for team {team_id} in period {period}, skipping")
                continue

            # Get available employees for this team and period
            available_employees = available_by_team_and_period[team_id][period]

            # Get workstations for this team
            workstations = team.workstations

            # Skip if no workstations
            if not workstations:
                logger.info(f"No workstations for team {team_id}, skipping")
                continue

            # Prepare input for CP model
            cp_input = {
                "employees": available_employees,
                "workstations": workstations,
                "period": period,
                "start_date": prefetched_data.get("start_date"),
                "aro_data": prefetched_data.get("aro_data", {}),
                "teams_by_id": prefetched_data.get("teams_by_id", {})
            }

            # Generate schedule for this team and period
            team_assignments = self.generate_period_schedule(
                team_id=team_id,
                cp_input=cp_input,
                employee_history_repo=prefetched_data.get("employee_history_repo")
            )

            # Add assignments to the result
            all_assignments.extend(team_assignments)

        return all_assignments

    def add_constraint(self, constraint: ScheduleConstraint):
        """Add a constraint to the schedule service"""
        self.constraints.append(constraint)

    def _get_teams_for_generation(self, args: Any, team_repository: Any) -> List[Any]:
        """
        Get teams based on the provided arguments.

        Args:
            args: Command line arguments or API request parameters
            team_repository: Repository for team data

        Returns:
            List of teams to generate schedules for
        """
        teams = []

        if hasattr(args, 'team') and args.team:
            # Get team by name
            try:
                team = team_repository.get_by_name(args.team)
                if not team:
                    return []
                teams = [team]
            except ValueError:
                return []
        elif hasattr(args, 'group') and args.group:
            # Get teams by group name
            teams = team_repository.get_by_group_name(args.group)
            if not teams:
                return []
        elif hasattr(args, 'department') and args.department:
            # Get teams by department name
            teams = team_repository.get_by_department_name(args.department)
            if not teams:
                return []

        return teams

    def generate_schedule_flow(
        self,
        args: Any,
        teams: List[Any],
        prefetched_data: Optional[Dict] = None,
        work_history_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Orchestrate the schedule generation flow without repository dependencies.

        This method handles:
        - Argument validation
        - Schedule generation for multiple teams
        - Performance metrics collection

        Args:
            args: Command line arguments or API request parameters
            teams: List of teams for which to generate schedules
            prefetched_data: Optional dictionary containing prefetched data
            work_history_data: Optional dictionary containing work history data

        Returns:
            Dictionary containing:
            - success: Boolean indicating if the operation was successful
            - assignments: List of generated assignments
            - teams: List of teams for which schedules were generated
            - metrics: Performance metrics
            - error: Error message if any
            - schedule_metadata: Metadata about each generated schedule
        """
        result = {
            "success": False,
            "assignments": [],
            "teams": teams,
            "metrics": {},
            "error": None,
            "schedule_metadata": []
        }

        start_time = time.time()

        try:
            # Parse start_date if it's a string
            start_date = args.start_date
            if isinstance(start_date, str):
                try:
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                except ValueError:
                    result["error"] = "Invalid start date format. Use YYYY-MM-DD"
                    return result

            if not teams:
                result["error"] = "No teams provided for schedule generation"
                return result

            # Generate schedules for each team
            all_assignments = []
            all_metadata = []

            for team in teams:
                # Get employees and workstations from prefetched data if available
                employees = []
                workstations = []

                if prefetched_data:
                    if 'employees_by_team' in prefetched_data and team.id in prefetched_data['employees_by_team']:
                        employees = prefetched_data['employees_by_team'][team.id]
                    if 'workstations_by_team' in prefetched_data and team.id in prefetched_data['workstations_by_team']:
                        workstations = prefetched_data['workstations_by_team'][team.id]

                # Skip teams with no employees or workstations
                if not employees or not workstations:
                    continue

                # Generate schedule for this team
                assignments, metadata = self.generate_schedule(
                    employees=employees,
                    workstations=workstations,
                    start_date=start_date,
                    periods_per_day=args.periods,
                    team_name=team.name,
                    team_id=team.id,
                    call_ins=args.call_ins,
                    offline=args.offline,
                    force_complete=args.force_complete,
                    prefetched_data=prefetched_data
                )

                # Add team info to metadata
                metadata["team_name"] = team.name
                metadata["team_id"] = team.id

                all_assignments.extend(assignments)
                all_metadata.append(metadata)

            # Calculate performance metrics
            end_time = time.time()
            execution_time = end_time - start_time

            result["assignments"] = all_assignments
            result["schedule_metadata"] = all_metadata
            result["metrics"] = {
                "execution_time": execution_time,
                "assignment_count": len(all_assignments),
                "team_count": len(teams)
            }
            result["success"] = True

            return result

        except Exception as e:
            result["error"] = f"Error generating schedule: {str(e)}"
            return result

    def generate_schedule_flow_legacy(
        self,
        args: Any,
        session: Any,
        employee_repository: Any,
        workstation_repository: Any,
        team_repository: Any,
        assignment_repository: Any,
        work_history_repository: Any,
        aro_repository: Any,
        aro_service: Any,
        aro_graph_service: Any,
        schedule_repository: Any
    ) -> Dict[str, Any]:
        """
        Orchestrate the complete schedule generation flow with repository dependencies.

        @deprecated: Use generate_schedule_flow instead and handle persistence in the application layer.

        This method handles:
        - Argument validation
        - Team lookup
        - Schedule generation
        - Work history updates
        - Performance metrics collection

        Args:
            args: Command line arguments or API request parameters
            session: Database session
            employee_repository: Repository for employee data
            workstation_repository: Repository for workstation data
            team_repository: Repository for team data
            assignment_repository: Repository for assignment data
            work_history_repository: Repository for work history data
            aro_repository: Repository for ARO assignment data
            aro_service: Service for ARO operations
            aro_graph_service: Service for ARO graph operations
            schedule_repository: Repository for schedule data

        Returns:
            Dictionary containing:
            - success: Boolean indicating if the operation was successful
            - assignments: List of generated assignments
            - teams: List of teams for which schedules were generated
            - metrics: Performance metrics
            - error: Error message if any
            - prefetched_data: Prefetched data for display or further processing
        """
        result = {
            "success": False,
            "assignments": [],
            "teams": [],
            "metrics": {},
            "error": None,
            "prefetched_data": {}
        }

        start_time = time.time()
        query_count = 0  # This would be tracked properly in a real implementation

        try:
            # Parse start_date if it's a string
            start_date = args.start_date
            if isinstance(start_date, str):
                try:
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                except ValueError:
                    result["error"] = "Invalid start date format. Use YYYY-MM-DD"
                    return result

            # Get teams based on the provided arguments
            teams = self._get_teams_for_generation(args, team_repository)
            if not teams:
                result["error"] = f"No teams found for the specified criteria"
                return result

            result["teams"] = teams

            # Create a domain event publisher
            event_publisher = DomainEventPublisher()

            # Create a schedule data service
            schedule_data_service = ScheduleDataService(
                employee_repository=employee_repository,
                workstation_repository=workstation_repository,
                team_repository=team_repository,
                aro_repository=aro_repository,
                session=session,
                work_history_repository=work_history_repository
            )
            # Import handler and coordinator here to avoid circular import
            from application.commands.generate_schedule_handler import GenerateScheduleHandler

            # Create a handler
            handler = GenerateScheduleHandler(
                employee_repository=employee_repository,
                workstation_repository=workstation_repository,
                team_repository=team_repository,
                assignment_repository=assignment_repository,
                schedule_service=self,
                schedule_repository=schedule_repository,
                session=session,
                aro_service=aro_service,
                aro_graph_service=aro_graph_service,
                work_history_repository=work_history_repository
            )

            # Import coordinator here to avoid circular import
            from infrastructure.scheduling.schedule_coordinator import ScheduleCoordinator

            # Create a schedule coordinator
            coordinator = ScheduleCoordinator(
                schedule_handler=handler,
                schedule_data_service=schedule_data_service,
                event_publisher=event_publisher,
                work_history_repository=work_history_repository
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
            all_assignments_by_team = coordinator.generate_schedules(commands)

            # Flatten assignments for saving
            all_assignments = []
            for team_assignments in all_assignments_by_team.values():
                all_assignments.extend(team_assignments)

            result["assignments"] = all_assignments

            # Save all assignments in a single batch
            save_success = assignment_repository.save_all(all_assignments)

            # Calculate performance metrics
            end_time = time.time()
            execution_time = end_time - start_time

            result["metrics"] = {
                "query_count": query_count,
                "execution_time": execution_time,
                "assignment_count": len(all_assignments),
                "team_count": len(teams)
            }

            # Prefetch data for display or further processing
            prefetched_data = schedule_data_service.prefetch_for_teams(
                team_ids=[team.id for team in teams],
                start_date=start_date,
                periods=args.periods
            )

            result["prefetched_data"] = prefetched_data
            result["success"] = True

            return result

        except Exception as e:
            result["error"] = f"Error generating schedule: {str(e)}"
            return result
