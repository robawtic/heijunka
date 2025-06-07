# heijunka/domain/services/schedule_service.py
from typing import List, Dict, Set, Optional, Tuple, Any, TypeVar, cast
from datetime import date, timedelta
import logging

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


    def _create_schedule(self, team_id: int, start_date: date, periods_per_day: int,
                          call_ins: Optional[List[str]], offline: Optional[List[str]],
                          offline_dict: OfflineDict, force_complete: bool,
                          schedule_repository=None):
        """
        Create a Schedule entity either through the repository or directly.

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
        from domain.entities.schedule import Schedule

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




    def generate_schedule(self, employees: List[Employee], workstations: List[Workstation],
                          start_date: date, periods_per_day: int,
                          team_name: str, call_ins: List[str] = None, offline: List[str] = None,
                          force_complete: bool = False, session: Any = None, team_repository: Optional[Any] = None,
                          aro_assignment_repository: Optional[Any] = None, schedule_repository: Optional[Any] = None,
                          aro_service: Optional[Any] = None, aro_graph_service: Optional[Any] = None,
                          prefetched_data: Optional[Dict] = None) -> WorkAssignments:
        """
        Generate a schedule for the given employees, workstations, and time period

        This method orchestrates the schedule generation process by:
        1. Creating a Schedule entity
        2. Setting up the necessary parameters
        3. Delegating the actual generation to the Schedule entity
        4. Returning the generated assignments

        Args:
            employees: List of employees to schedule
            workstations: List of workstations to assign employees to
            start_date: The start date of the schedule
            periods_per_day: Number of periods per day
            team_name: Name of the team to generate the schedule for
            call_ins: List of employee names who called in (unavailable)
            offline: List of strings in format "employee:periods" specifying which employees are offline for which periods
            force_complete: Whether to force completion of the schedule
            session: Database session for accessing work history data
            team_repository: Optional repository for retrieving team information (optional for testing/offline use)
            aro_assignment_repository: Optional repository for retrieving ARO assignments (optional for testing/offline use)
            schedule_repository: Optional repository for creating/retrieving schedules (optional for testing/offline use)
            aro_service: Optional ARO service for finding and assigning AROs
            aro_graph_service: Optional ARO graph service for optimizing ARO assignments
            prefetched_data: Optional dictionary containing prefetched data to avoid database queries

        Returns:
            List of work assignments
        """
        # Parse offline parameter
        offline_dict = self._parse_offline(offline)

        # Get team_id from team_name (use prefetched data if available)
        # Set team_repository on team_lookup_service if it's provided
        if team_repository:
            self.team_lookup_service.team_repository = team_repository

        team_id = self.team_lookup_service.get_team_id(team_name, prefetched_data)

        # Handle ARO assignments (employees leaving/joining)
        # Set repositories on ARO roster service if they're provided
        if team_repository:
            self.aro_roster_service.team_repository = team_repository
        if aro_assignment_repository:
            self.aro_roster_service.aro_assignment_repository = aro_assignment_repository

        available_employees = self.aro_roster_service.handle_aro_assignments(
            employees, team_id, start_date, prefetched_data
        )

        # Create a Schedule entity
        schedule = self._create_schedule(
            team_id, start_date, periods_per_day, call_ins, offline, 
            offline_dict, force_complete, schedule_repository
        )

        # Generate assignments using the Schedule entity
        success = schedule.generate_assignments(
            available_employees, 
            workstations, 
            session=session,
            team_repository=team_repository,
            aro_service=aro_service,
            aro_graph_service=aro_graph_service,
            prefetched_data=prefetched_data
        )

        # Update schedule status based on generation result
        if schedule_repository:
            try:
                if success:
                    schedule_repository.update_status(schedule.id, "completed")
                    logger.info(f"Updated schedule {schedule.id} status to 'completed'")
                else:
                    schedule_repository.update_status(schedule.id, "failed", schedule.error_message)
                    logger.warning(f"Updated schedule {schedule.id} status to 'failed': {schedule.error_message}")
            except Exception as e:
                logger.error(f"Error updating schedule status: {str(e)}")

        if success:
            logger.info(f"Generated {len(schedule.assignments)} assignments")
            return schedule.assignments
        else:
            logger.warning(f"No solution found. Error: {schedule.error_message}")
            return []

    def generate_period_schedule(self, team_id: int, cp_input: Dict) -> WorkAssignments:
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

        Returns:
            List of work assignments for the specified team and period
        """
        try:
            # Extract data from cp_input
            employees = cp_input.get("employees", [])
            workstations = cp_input.get("workstations", [])
            period = cp_input.get("period")
            start_date = cp_input.get("start_date")
            aro_data = cp_input.get("aro_data", {})

            if not employees or not workstations or period is None or not start_date:
                logger.error(f"Missing required data for generate_period_schedule: team_id={team_id}, period={period}")
                return []

            # Get team name for logging
            team_name = "Unknown"
            if "teams_by_id" in cp_input and team_id in cp_input["teams_by_id"]:
                team = cp_input["teams_by_id"][team_id]
                if hasattr(team, "name"):
                    team_name = team.name

            logger.info(f"Generating schedule for team '{team_name}' period {period}")

            # Use the CP model builder to solve the model
            assignments = self.cp_model_builder.solve_one_period(
                employees=employees,
                workstations=workstations,
                period=period,
                team_id=team_id,
                start_date=start_date,
                aro_data=aro_data,
                team_name=team_name
            )

            if assignments:
                logger.info(f"Generated {len(assignments)} assignments for team '{team_name}' period {period}")
            else:
                logger.warning(f"No solution found for team '{team_name}' period {period}")

            return assignments

        except Exception as e:
            logger.error(f"Error generating period schedule for team {team_id}, period {cp_input.get('period')}: {str(e)}")
            return []

    def add_constraint(self, constraint: ScheduleConstraint):
        """Add a constraint to the schedule service"""
        self.constraints.append(constraint)
