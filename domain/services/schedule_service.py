# heijunka/domain/services/schedule_service.py
from typing import List, Dict, Set, Optional, Tuple, Any, TypeVar, cast
from datetime import date, timedelta
import logging

from ortools.sat.python import cp_model

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment
from domain.value_objects.schedule_constraint import ScheduleConstraint, ConstraintType
from domain.events import AssignmentCreated
from domain.rules.context import RuleContext

# Type aliases for improved readability
WorkAssignments = List[WorkAssignment]
OfflineDict = Dict[str, List[int]]

# Logger for this module
logger = logging.getLogger(__name__)


class ScheduleService:
    # Default values as class constants
    DEFAULT_PERIODS_PER_DAY = 4
    DEFAULT_SCHEDULE_ID = 1

    def __init__(self, constraints: List[ScheduleConstraint] = None):
        self.constraints = constraints or []

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

    def _get_team_id(
            self,
            team_name: str,
            team_repository,
            prefetched_data: Optional[Dict] = None
    ) -> int:
        """
        Resolve team ID by team name only.
        First checks prefetched data if available, then falls back to repository.
        Raises ValueError if not found.

        Args:
            team_name: Name of the team to look up
            team_repository: Repository for retrieving team information
            prefetched_data: Optional dictionary containing prefetched data

        Returns:
            The team ID

        Raises:
            ValueError: If team not found or repository not provided
        """
        # First check if we have the team in prefetched data
        if prefetched_data and 'teams_by_name' in prefetched_data and team_name in prefetched_data['teams_by_name']:
            team = prefetched_data['teams_by_name'][team_name]
            if team and hasattr(team, 'id'):
                logger.debug(f"Found team_id={team.id} for team '{team_name}' via prefetched data")
                return team.id

        # Fall back to repository lookup
        if not team_repository:
            raise ValueError("team_repository is required to look up team_id by team name when not in prefetched data.")

        team = team_repository.get_by_name(team_name)
        if team and hasattr(team, 'id'):
            logger.debug(f"Found team_id={team.id} for team '{team_name}' via repository")
            return team.id

        error_msg = f"Could not resolve team_id for team '{team_name}'. No matching team found in prefetched data or repository."
        logger.error(error_msg)
        raise ValueError(error_msg)

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

    def _handle_aro_assignments(self, employees: List[Employee], team_id: int,
                               start_date: date, team_repository=None, 
                               aro_assignment_repository=None, prefetched_data: Optional[Dict] = None) -> List[Employee]:
        """
        Handle ARO (Assigned Relief Operator) assignments by:
        1. Removing employees leaving the team
        2. Adding employees joining the team

        Args:
            employees: List of employees to filter
            team_id: ID of the team
            start_date: Start date of the schedule
            team_repository: Optional repository for retrieving team information
            aro_assignment_repository: Optional repository for retrieving ARO assignments
            prefetched_data: Optional dictionary containing prefetched data

        Returns:
            List of available employees after ARO processing
        """
        # If no employees, return empty list
        if not employees:
            logger.warning(f"No employees provided for team {team_id}, skipping ARO processing")
            return []

        # If prefetched ARO data is available, use it
        if prefetched_data and prefetched_data.get('aro_assignments_by_team') and team_id in prefetched_data.get('aro_assignments_by_team', {}):
            try:
                logger.debug(f"Using prefetched ARO data for team {team_id}")

                # Initialize available employees with a copy of the original list
                available_employees = employees.copy()

                # Track which employees were processed for validation
                processed_employees = set()

                # Process full-day ARO assignments
                self._process_full_day_aro_assignments(
                    team_id, 
                    available_employees, 
                    prefetched_data, 
                    processed_employees,
                    team_repository
                )

                # Process period-specific ARO assignments if available
                if (prefetched_data.get('aro_assignments_by_team_period') and 
                    team_id in prefetched_data.get('aro_assignments_by_team_period', {}) and
                    prefetched_data.get('periods_per_day')):

                    self._process_period_specific_aro_assignments(
                        team_id, 
                        available_employees, 
                        prefetched_data, 
                        processed_employees,
                        team_repository
                    )

                # Validate ARO assignments
                if not available_employees:
                    logger.warning(
                        f"No available employees after ARO processing for team {team_id}. "
                        f"This may indicate an issue with ARO assignments."
                    )

                logger.info(
                    f"Processed ARO assignments for team {team_id}: "
                    f"{len(processed_employees)} employees processed, "
                    f"{len(available_employees)} employees available"
                )

                return available_employees

            except Exception as e:
                logger.error(
                    f"Error processing prefetched ARO assignments for team {team_id}: {str(e)}. "
                    f"Falling back to non-prefetched path."
                )
                # Fall through to non-prefetched path

        # If no prefetched data or ARO repository, return original employees
        if not aro_assignment_repository:
            logger.debug("No ARO assignment repository provided, skipping ARO processing")
            return employees.copy()

        # Get employees leaving as AROs
        aro_out_ids = []
        try:
            aro_out_ids = aro_assignment_repository.get_employees_leaving(team_id, start_date)
            if aro_out_ids:
                logger.info(f"Found {len(aro_out_ids)} employees leaving team {team_id} as AROs")
        except Exception as e:
            logger.error(f"Error getting employees leaving as AROs: {str(e)}")

        # Get employees joining as AROs
        aro_in_ids = []
        try:
            aro_in_ids = aro_assignment_repository.get_employees_joining(team_id, start_date)
            if aro_in_ids:
                logger.info(f"Found {len(aro_in_ids)} employees joining team {team_id} as AROs")
        except Exception as e:
            logger.error(f"Error getting employees joining as AROs: {str(e)}")

        # Filter out employees leaving as AROs
        available_employees = [e for e in employees if e.id not in aro_out_ids]

        # Add employees joining as AROs
        if aro_in_ids and team_repository:
            for aro_id in aro_in_ids:
                try:
                    # Get the employee from their original team
                    aro_assignments = aro_assignment_repository.get_by_employee_id(aro_id, start_date)
                    if aro_assignments:
                        assignment = aro_assignments[0]  # Take the first assignment if multiple exist
                        from_team = team_repository.get(assignment.from_team_id)
                        if from_team:
                            for emp in from_team.members:
                                if emp.id == aro_id:
                                    available_employees.append(emp)
                                    logger.debug(f"Added ARO employee {emp.name} (ID: {emp.id}) from team {from_team.name}")
                                    break
                except Exception as e:
                    logger.error(f"Error processing ARO employee {aro_id}: {str(e)}")

        # Validate ARO assignments
        if not available_employees:
            logger.warning(
                f"No available employees after ARO processing for team {team_id}. "
                f"This may indicate an issue with ARO assignments."
            )

        return available_employees

    def _process_full_day_aro_assignments(
        self, 
        team_id: int, 
        available_employees: List[Employee], 
        prefetched_data: Dict, 
        processed_employees: Set[int],
        team_repository=None
    ) -> None:
        """
        Process full-day ARO assignments for a team.

        Args:
            team_id: ID of the team
            available_employees: List of available employees to modify
            prefetched_data: Dictionary containing prefetched data
            processed_employees: Set to track which employees were processed
            team_repository: Optional repository for retrieving team information
        """
        # Safely get ARO data
        if 'aro_assignments_by_team' not in prefetched_data or team_id not in prefetched_data['aro_assignments_by_team']:
            logger.warning(f"No ARO data found for team {team_id} in prefetched data")
            return

        aro_data = prefetched_data['aro_assignments_by_team'][team_id]

        # Get employees leaving as AROs from prefetched data
        aro_out_ids = aro_data.get('out', [])
        if aro_out_ids:
            logger.info(f"Found {len(aro_out_ids)} employees leaving team {team_id} as AROs (from prefetched data)")

            # Filter out employees leaving as AROs
            available_employees[:] = [e for e in available_employees if e.id not in aro_out_ids]

            # Add to processed employees
            processed_employees.update(aro_out_ids)

        # Get employees joining as AROs from prefetched data
        aro_in_ids = aro_data.get('in', [])
        if aro_in_ids:
            logger.info(f"Found {len(aro_in_ids)} employees joining team {team_id} as AROs (from prefetched data)")

            # Add employees joining as AROs
            self._add_aro_employees(aro_in_ids, available_employees, prefetched_data, processed_employees, team_repository)

    def _process_period_specific_aro_assignments(
        self, 
        team_id: int, 
        available_employees: List[Employee], 
        prefetched_data: Dict, 
        processed_employees: Set[int],
        team_repository=None
    ) -> None:
        """
        Process period-specific ARO assignments for a team.

        Args:
            team_id: ID of the team
            available_employees: List of available employees to modify
            prefetched_data: Dictionary containing prefetched data
            processed_employees: Set to track which employees were processed
            team_repository: Optional repository for retrieving team information
        """
        # Safely get period-specific ARO data
        if 'aro_assignments_by_team_period' not in prefetched_data or team_id not in prefetched_data['aro_assignments_by_team_period']:
            logger.warning(f"No period-specific ARO data found for team {team_id} in prefetched data")
            return

        if 'periods_per_day' not in prefetched_data:
            logger.warning(f"No periods_per_day found in prefetched data")
            return

        periods_data = prefetched_data['aro_assignments_by_team_period'][team_id]
        periods_per_day = prefetched_data['periods_per_day']

        for period in range(1, periods_per_day + 1):
            if period not in periods_data:
                continue

            period_data = periods_data[period]

            # Get employees leaving as AROs for this period
            period_out_ids = period_data.get('out', [])
            if period_out_ids:
                logger.info(f"Found {len(period_out_ids)} employees leaving team {team_id} as AROs for period {period} (from prefetched data)")

                # Filter out employees leaving as AROs for this period
                # Note: For period-specific assignments, we don't remove the employee entirely,
                # but this information would be used during the actual scheduling
                processed_employees.update(period_out_ids)

            # Get employees joining as AROs for this period
            period_in_ids = period_data.get('in', [])
            if period_in_ids:
                logger.info(f"Found {len(period_in_ids)} employees joining team {team_id} as AROs for period {period} (from prefetched data)")

                # Add employees joining as AROs for this period
                self._add_aro_employees(period_in_ids, available_employees, prefetched_data, processed_employees, team_repository)

    def _add_aro_employees(
        self, 
        aro_ids: List[int], 
        available_employees: List[Employee], 
        prefetched_data: Dict,
        processed_employees: Set[int],
        team_repository=None
    ) -> None:
        """
        Add ARO employees to the list of available employees.

        Args:
            aro_ids: List of ARO employee IDs to add
            available_employees: List of available employees to modify
            prefetched_data: Dictionary containing prefetched data
            processed_employees: Set to track which employees were processed
            team_repository: Optional repository for retrieving team information
        """

        # Track existing employee IDs to avoid duplicates
        existing_employee_ids = {e.id for e in available_employees}

        for aro_id in aro_ids:
            # Skip if already processed
            if aro_id in processed_employees:
                continue

            try:
                # First try to get employee from prefetched employees_by_id
                if prefetched_data.get('employees_by_id') and aro_id in prefetched_data.get('employees_by_id', {}):
                    emp = prefetched_data['employees_by_id'][aro_id]

                    # Add only if not already in the list
                    if emp.id not in existing_employee_ids:
                        available_employees.append(emp)
                        existing_employee_ids.add(emp.id)
                        logger.debug(f"Added ARO employee {emp.name} (ID: {emp.id}) from prefetched data")

                # If not found, try to get from ARO assignments and team repository
                elif prefetched_data.get('aro_assignments_by_employee') and aro_id in prefetched_data.get('aro_assignments_by_employee', {}):
                    aro_assignments = prefetched_data['aro_assignments_by_employee'][aro_id]

                    if aro_assignments and aro_id not in existing_employee_ids:
                        assignment = aro_assignments[0]  # Take the first assignment if multiple exist

                        # Try to get the team from prefetched data first
                        from_team = None
                        if prefetched_data.get('teams_by_id') and assignment.from_team_id in prefetched_data.get('teams_by_id', {}):
                            from_team = prefetched_data['teams_by_id'][assignment.from_team_id]
                        elif team_repository:
                            from_team = team_repository.get(assignment.from_team_id)

                        if from_team and hasattr(from_team, 'members'):
                            for emp in from_team.members:
                                if emp.id == aro_id and emp.id not in existing_employee_ids:
                                    available_employees.append(emp)
                                    existing_employee_ids.add(emp.id)
                                    logger.debug(f"Added ARO employee {emp.name} (ID: {emp.id}) from team {from_team.name}")
                                    break

                # Mark as processed
                processed_employees.add(aro_id)

            except Exception as e:
                logger.error(f"Error adding ARO employee {aro_id}: {str(e)}")


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
        team_id = self._get_team_id(team_name, team_repository, prefetched_data)

        # Handle ARO assignments (employees leaving/joining)
        available_employees = self._handle_aro_assignments(
            employees, team_id, start_date, team_repository, aro_assignment_repository, prefetched_data
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

            # Create CP model
            model = cp_model.CpModel()

            # Define decision variables
            assign = {}
            for e, employee in enumerate(employees):
                for w, workstation in enumerate(workstations):
                    assign[(e, w, period-1)] = model.NewBoolVar(
                        f'assign_e{e}_w{w}_p{period-1}')

            # Each employee is assigned to at most one workstation per period
            for e in range(len(employees)):
                model.Add(sum(assign[(e, w, period-1)] for w in range(len(workstations))) <= 1)

            # Each workstation is assigned to at most one employee per period
            for w in range(len(workstations)):
                model.Add(sum(assign[(e, w, period-1)] for e in range(len(employees))) <= 1)

            # Handle employee availability based on ARO assignments
            for e, employee in enumerate(employees):
                is_available = True

                # Check if employee is available for this period based on ARO data
                key_exact = (employee.id, period)
                key_fullday = (employee.id, None)  # Check for full-day ARO assignments

                if key_fullday in aro_data:
                    aro_list = aro_data[key_fullday]
                    # If employee has a full-day ARO assignment, check if they're available
                    for aro in aro_list:
                        if aro.to_team_id != team_id:  # Employee is assigned elsewhere
                            is_available = False
                            break
                elif key_exact in aro_data:
                    aro_list = aro_data[key_exact]
                    # If employee has a period-specific ARO assignment, check if they're available
                    for aro in aro_list:
                        if aro.to_team_id != team_id:  # Employee is assigned elsewhere
                            is_available = False
                            break

                # If employee is not available, ensure they're not assigned
                if not is_available:
                    for w in range(len(workstations)):
                        model.Add(assign[(e, w, period-1)] == 0)

            # Objective: Maximize the number of assignments
            objective_terms = []
            for e in range(len(employees)):
                for w in range(len(workstations)):
                    objective_terms.append(assign[(e, w, period-1)])

            model.Maximize(sum(objective_terms))

            # Create solver and solve the model
            solver = cp_model.CpSolver()
            status = solver.Solve(model)

            # Process the solution
            assignments = []
            if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
                for e, employee in enumerate(employees):
                    for w, workstation in enumerate(workstations):
                        if solver.Value(assign[(e, w, period-1)]) == 1:
                            # Create a schedule period
                            schedule_period = SchedulePeriod(
                                date=start_date,
                                period=period
                            )

                            # Create a work assignment
                            assignment = WorkAssignment(
                                employee=employee,
                                workstation=workstation,
                                period=schedule_period
                                # team_id=team_id # team_id is part of workstation
                            )

                            assignments.append(assignment)

                logger.info(f"Generated {len(assignments)} assignments for team '{team_name}' period {period}")
            else:
                logger.warning(f"No solution found for team '{team_name}' period {period}. Status: {status}")

            return assignments

        except Exception as e:
            logger.error(f"Error generating period schedule for team {team_id}, period {cp_input.get('period')}: {str(e)}")
            return []

    def add_constraint(self, constraint: ScheduleConstraint):
        """Add a constraint to the schedule service"""
        self.constraints.append(constraint)
