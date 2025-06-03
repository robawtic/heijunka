# heijunka/domain/entities/schedule.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Tuple
from datetime import date, timedelta
import logging

from ortools.sat.python import cp_model

# Logger for this module
logger = logging.getLogger(__name__)

from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment
from domain.value_objects.employee_availability import AvailabilityStatus
from domain.events import (
    DomainEvent, ScheduleCreated, ScheduleUpdated, ScheduleStatusChanged,
    AssignmentAdded, AssignmentRemoved, ScheduleValidationFailed
)


@dataclass
class Schedule:
    """
    Schedule aggregate root entity.

    Represents a work schedule for a team, containing assignments of employees to workstations.
    """
    # Class constants
    DEFAULT_SOLVER_TIME_LIMIT = 3.0  # 30/10 seconds
    MAX_SOLVER_TIME_LIMIT = 300.0    # 5 minutes
    DEFAULT_LOOKBACK_DAYS = 3        # Default lookback of 3 days

    # Rule weights for different rule types
    RULE_WEIGHTS = {
        # Current soft rules
        "add_same_day_repeat_penalties": 100,
        "add_lookback_any_period_penalties": 1000,
        "add_lookback_same_period_penalties": 500,

        # Backward compatibility
        "add_rotation_penalties": 1000
    }

    # Instance attributes
    id: int
    team_id: int
    start_date: date
    periods_per_day: int
    status: str
    call_ins: List[str] = field(default_factory=list)
    offline: Dict[str, List[int]] = field(default_factory=dict)
    force_complete: bool = False
    error_message: Optional[str] = None
    task_id: Optional[str] = None
    _assignments: List[WorkAssignment] = field(default_factory=list, repr=False)
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)
    end_date: Optional[date] = None

    def __post_init__(self):
        """Initialize collections if they are None and validate the schedule."""
        if self._assignments is None:
            self._assignments = []
        if self._domain_events is None:
            self._domain_events = []
        if self.call_ins is None:
            self.call_ins = []
        if self.offline is None:
            self.offline = {}
        if self.end_date is None:
            self.end_date = self.start_date

        # Register creation event
        if self.id > 0 and isinstance(self.team_id, int) and self.team_id > 0:  # Only register if this is a real entity with valid team_id
            try:
                self.register_domain_event(ScheduleCreated(
                    schedule_id=self.id,
                    team_id=self.team_id,
                    start_date=self.start_date,
                    periods_per_day=self.periods_per_day
                ))

                # Validate the schedule if it's a real entity (not a placeholder)
                try:
                    self.validate()
                except ValueError as e:
                    logger.warning(f"New schedule failed validation: {e}")
                    # Don't raise - just log the warning
            except ValueError:
                # If there's an error creating the event (e.g., invalid start_date), don't register it
                pass

    @property
    def assignments(self) -> List[WorkAssignment]:
        """Get a copy of the assignments list to prevent direct modification."""
        return self._assignments.copy()

    @property
    def domain_events(self) -> List[DomainEvent]:
        """Get a copy of the domain events list."""
        return self._domain_events.copy()

    def clear_domain_events(self) -> None:
        """Clear all domain events after they've been processed."""
        self._domain_events.clear()

    def register_domain_event(self, event: DomainEvent) -> None:
        """Register a domain event."""
        self._domain_events.append(event)

    def add_assignment(self, assignment: WorkAssignment) -> bool:
        """
        Add an assignment to the schedule.

        Args:
            assignment: The assignment to add.

        Returns:
            True if the assignment was added, False if it was already in the schedule.

        Raises:
            ValueError: If the assignment is invalid.
        """
        if not isinstance(assignment, WorkAssignment):
            raise ValueError("assignment must be a WorkAssignment instance")

        # Check if this assignment already exists
        for existing in self._assignments:
            if (existing.employee.id == assignment.employee.id and
                existing.workstation.id == assignment.workstation.id and
                existing.period.date == assignment.period.date and
                existing.period.period == assignment.period.period):
                return False

        # Add the assignment to the schedule
        self._assignments.append(assignment)

        # Register the domain event
        self.register_domain_event(AssignmentAdded(
            schedule_id=self.id,
            employee_id=assignment.employee.id,
            workstation_id=assignment.workstation.id,
            period=assignment.period
        ))

        return True

    def create_assignment(self, employee: "Employee", workstation: "Workstation", 
                         period: SchedulePeriod) -> WorkAssignment:
        """
        Create and add a new assignment to the schedule.

        Args:
            employee: The employee to assign
            workstation: The workstation to assign the employee to
            period: The period for the assignment

        Returns:
            The created work assignment

        Raises:
            ValueError: If the assignment is invalid
        """
        # Validate employee can work at this workstation
        if not employee.can_work(workstation):
            raise ValueError(f"{employee.name} cannot work at {workstation.name}")

        # Validate employee is available for this period
        if not employee.is_available_for_period(period.date, period.period):
            raise ValueError(f"{employee.name} is not available on {period}")

        # Validate period is within schedule range
        if period.date < self.start_date or period.date > self.end_date:
            raise ValueError(f"Period {period} is outside schedule date range ({self.start_date} to {self.end_date})")

        # Validate period number is valid
        if period.period < 1 or period.period > self.periods_per_day:
            raise ValueError(f"Period {period.period} is outside valid range (1-{self.periods_per_day})")

        # Create the assignment
        assignment = WorkAssignment(
            employee=employee,
            workstation=workstation,
            period=period
        )

        # Add to schedule
        self.add_assignment(assignment)

        return assignment

    def remove_assignment(self, employee_id: int, workstation_id: int, period: SchedulePeriod) -> bool:
        """
        Remove an assignment from the schedule.

        Args:
            employee_id: The ID of the employee.
            workstation_id: The ID of the workstation.
            period: The period of the assignment.

        Returns:
            True if the assignment was removed, False if it wasn't in the schedule.
        """
        # Find the assignment in the schedule
        for i, assignment in enumerate(self._assignments):
            if (assignment.employee.id == employee_id and
                assignment.workstation.id == workstation_id and
                assignment.period.date == period.date and
                assignment.period.period == period.period):
                # Remove the assignment from the schedule
                self._assignments.pop(i)

                # Register the domain event
                self.register_domain_event(AssignmentRemoved(
                    schedule_id=self.id,
                    employee_id=employee_id,
                    workstation_id=workstation_id,
                    period=period
                ))

                return True

        return False

    def get_assignments_for_date(self, date_obj: date) -> List[WorkAssignment]:
        """
        Get all assignments for a specific date.

        Args:
            date_obj: The date to get assignments for.

        Returns:
            A list of assignments for the date.
        """
        return [a for a in self._assignments if a.period.date == date_obj]

    def get_assignments_for_employee(self, employee_id: int) -> List[WorkAssignment]:
        """
        Get all assignments for a specific employee.

        Args:
            employee_id: The ID of the employee.

        Returns:
            A list of assignments for the employee.
        """
        return [a for a in self._assignments if a.employee.id == employee_id]

    def get_assignments_for_workstation(self, workstation_id: int) -> List[WorkAssignment]:
        """
        Get all assignments for a specific workstation.

        Args:
            workstation_id: The ID of the workstation.

        Returns:
            A list of assignments for the workstation.
        """
        return [a for a in self._assignments if a.workstation.id == workstation_id]

    def set_status(self, new_status: str) -> bool:
        """
        Set the status of the schedule.

        Args:
            new_status: The new status.

        Returns:
            True if the status was changed, False if it's the same.

        Raises:
            ValueError: If the new status is invalid.
        """
        if not isinstance(new_status, str) or not new_status:
            raise ValueError("Status must be a non-empty string")

        if self.status == new_status:
            return False

        old_status = self.status
        self.status = new_status

        self.register_domain_event(ScheduleStatusChanged(
            schedule_id=self.id,
            old_status=old_status,
            new_status=new_status
        ))

        return True

    def set_error_message(self, error_message: Optional[str]) -> bool:
        """
        Set the error message of the schedule.

        Args:
            error_message: The new error message, or None to clear it.

        Returns:
            True if the error message was changed, False if it's the same.
        """
        if self.error_message == error_message:
            return False

        self.error_message = error_message
        return True

    def set_task_id(self, task_id: Optional[str]) -> bool:
        """
        Set the task ID of the schedule.

        Args:
            task_id: The new task ID, or None to clear it.

        Returns:
            True if the task ID was changed, False if it's the same.
        """
        if self.task_id == task_id:
            return False

        self.task_id = task_id
        return True

    def update(self, status: Optional[str] = None, error_message: Optional[str] = None,
               task_id: Optional[str] = None) -> None:
        """
        Update multiple properties of the schedule at once.

        Args:
            status: The new status (if provided).
            error_message: The new error message (if provided).
            task_id: The new task ID (if provided).

        Raises:
            ValueError: If any of the provided values are invalid.
        """
        updated = False

        if status is not None:
            updated = self.set_status(status) or updated

        # Update error_message if:
        # 1. A new error_message is provided, or
        # 2. error_message is explicitly set to None and we currently have an error_message
        if (error_message is not None) or (error_message is None and self.error_message is not None):
            updated = self.set_error_message(error_message) or updated

        # Update task_id if:
        # 1. A new task_id is provided, or
        # 2. task_id is explicitly set to None and we currently have a task_id
        if (task_id is not None) or (task_id is None and self.task_id is not None):
            updated = self.set_task_id(task_id) or updated

        if updated:
            self.register_domain_event(ScheduleUpdated(schedule_id=self.id))

    def _request_aros_from_service(
        self, 
        needed_count: int, 
        aro_service: "AROService", 
        aro_graph_service: "AROGraphService"
    ) -> Optional[List["Employee"]]:
        """
        Request AROs through the ARO service.

        Args:
            needed_count: Number of AROs needed
            aro_service: ARO service for finding and assigning AROs
            aro_graph_service: ARO graph service for optimizing ARO assignments

        Returns:
            List of employees including AROs if successful, empty list if no AROs found, None if service failed
        """
        if not aro_service or not aro_graph_service:
            logger.warning(f"Team {self.team_id}: No ARO service or graph service available")
            return []

        logger.info(f"Team {self.team_id}: Requesting {needed_count} AROs through ARO service")

        try:
            # Request AROs through the ARO service
            aro_assignments = aro_graph_service.assign_optimal_aros(
                understaffed_team_id=self.team_id,
                needed_aros=needed_count,
                assignment_date=self.start_date,
                period=None  # Full day assignment
            )

            if not aro_assignments:
                logger.warning(f"Team {self.team_id}: No ARO assignments returned from ARO service")
                return []

            logger.info(f"Team {self.team_id}: ARO service returned {len(aro_assignments)} ARO assignments")

            # Get updated employee list including AROs
            updated_employees = aro_service.get_employees_for_team_and_period(
                team_id=self.team_id,
                assignment_date=self.start_date,
                period=None
            )

            logger.info(f"Team {self.team_id}: Updated employee list has {len(updated_employees)} employees")
            return updated_employees

        except Exception as e:
            logger.error(f"Team {self.team_id}: Error using ARO service: {str(e)}")
            return None

    def _find_additional_employees_direct(
        self, 
        needed_count: int, 
        workstations: List["Workstation"], 
        session: Any, 
        team_repository: "TeamRepositoryInterface", 
        prefetched_data: Optional[Dict[str, Any]] = None
    ) -> List["Employee"]:
        """
        Find additional employees from other teams using the direct method.

        Args:
            needed_count: Number of additional employees needed
            workstations: List of workstations that need to be staffed
            session: Database session for accessing employee data
            team_repository: Repository for retrieving team information
            prefetched_data: Optional dictionary containing prefetched data to avoid database queries

        Returns:
            List of additional employees found
        """
        if not team_repository or not session:
            logger.warning(f"Team {self.team_id}: No team_repository or session available for direct method")
            return []

        # Get the current team (use prefetched data if available)
        team = None
        if prefetched_data and 'teams_by_id' in prefetched_data and self.team_id in prefetched_data['teams_by_id']:
            team = prefetched_data['teams_by_id'][self.team_id]
        else:
            team = team_repository.get(self.team_id)

        if not team:
            logger.warning(f"Team {self.team_id}: Team not found for direct method")
            return []

        # Find employees from other teams who can work on this team's workstations
        additional_employees = self._find_employees_from_other_teams(
            team, workstations, needed_count, session, team_repository, prefetched_data
        )

        if additional_employees:
            logger.info(f"Team {self.team_id}: Found {len(additional_employees)} additional employees using direct method")
        else:
            logger.warning(f"Team {self.team_id}: No additional employees found using direct method")

        return additional_employees

    def _handle_force_complete(
        self, 
        available_count: int, 
        needed_count: int
    ) -> bool:
        """
        Handle the case when force_complete is set but not enough employees are available.

        Args:
            available_count: Number of available employees
            needed_count: Number of workstations that need to be staffed

        Returns:
            True if we should continue with schedule generation, False if we should fail
        """
        if self.force_complete:
            # If force_complete is set, continue with the available employees
            logger.info(
                f"Team {self.team_id}: Not enough employees ({available_count}/{needed_count}), "
                f"but force_complete is set. Continuing with available employees."
            )
            self.set_status("partial")
            self.set_error_message(
                f"Not enough employees to cover all workstations. "
                f"Available: {available_count}, Needed: {needed_count}. "
                f"Generating partial schedule with force_complete=True."
            )
            return True
        else:
            # If force_complete is not set, fail
            logger.warning(
                f"Team {self.team_id}: Not enough employees ({available_count}/{needed_count}) "
                f"and force_complete is not set. Failing."
            )
            self.set_status("failed")
            self.set_error_message(
                f"Not enough employees to cover all workstations. "
                f"Available: {available_count}, Needed: {needed_count}. "
                f"Call-ins: {', '.join(self.call_ins) if self.call_ins else 'None'}. "
                f"Try reducing the number of call-ins or use --force-complete to generate a partial schedule."
            )
            return False

    def _check_employee_availability(
        self, 
        employees: List["Employee"]
    ) -> Tuple[int, int, List["Employee"]]:
        """
        Check if there are enough employees to cover all workstations.

        Args:
            employees: List of employees available for scheduling

        Returns:
            Tuple containing:
            - Number of available non-ARO employees
            - Number of ARO employees
            - List of non-ARO employees
        """
        # Filter out AROs, called-in employees, and team leaders from the count
        aro_employees = [e for e in employees if any(
            av.status == AvailabilityStatus.ARO 
            for av in e.available_periods 
            if av.date == self.start_date
        )]

        # Filter out employees who are unavailable (called in) or team leaders
        non_aro_employees = [e for e in employees if 
            e.is_available_for_period(self.start_date, None) and  # Filter out called-in employees
            not e.has_role("Team Lead") and  # Filter out team leaders
            e.name not in (self.call_ins or []) and  # Filter out explicitly called-in employees
            not any(av.status == AvailabilityStatus.ARO for av in e.available_periods if av.date == self.start_date)  # Filter out AROs
        ]

        available_count = len(non_aro_employees)
        aro_count = len(aro_employees)

        logger.debug(
            f"Team {self.team_id}: {available_count} available employees, {aro_count} ARO employees, "
            f"{len(employees) - available_count - aro_count} unavailable employees"
        )

        return available_count, aro_count, non_aro_employees

    def _handle_employee_shortage(
        self, 
        employees: List["Employee"], 
        workstations: List["Workstation"],
        available_count: int, 
        session: Optional[Any] = None, 
        team_repository: Optional["TeamRepositoryInterface"] = None,
        aro_service: Optional["AROService"] = None, 
        aro_graph_service: Optional["AROGraphService"] = None, 
        prefetched_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List["Employee"]]:
        """
        Handle the case when there aren't enough employees to cover all workstations.

        Args:
            employees: List of employees available for scheduling
            workstations: List of workstations to be staffed
            available_count: Number of available employees
            session: Database session for accessing work history data
            team_repository: Optional repository for retrieving team information
            aro_service: Optional ARO service for finding and assigning AROs
            aro_graph_service: Optional ARO graph service for optimizing ARO assignments
            prefetched_data: Optional dictionary containing prefetched data to avoid database queries

        Returns:
            Tuple containing:
            - Boolean indicating whether to continue with schedule generation
            - Updated list of employees (may include additional employees)
        """
        needed_count = len(workstations) - available_count

        # Set initial status
        self.set_status("pending_aro")
        self.set_error_message(f"Not enough employees to cover all workstations. "
                          f"Available: {available_count}, Needed: {len(workstations)}")

        logger.info(f"Team {self.team_id}: Not enough employees ({available_count}/{len(workstations)}), "
                   f"need {needed_count} more")

        # Try to get additional employees
        updated_employees = employees.copy()

        # First try ARO service if available
        if aro_service and aro_graph_service:
            aro_employees = self._request_aros_from_service(needed_count, aro_service, aro_graph_service)
            if aro_employees is None:
                logger.warning(f"Team {self.team_id}: ARO service failed, falling back to direct method")
            elif aro_employees:  # Non-empty list means AROs were found
                logger.info(f"Team {self.team_id}: Using {len(aro_employees)} employees from ARO service")
                return True, aro_employees
            else:
                logger.info(f"Team {self.team_id}: No AROs found from ARO service, falling back to direct method")

        # If ARO service failed or isn't available, try direct method
        additional_employees = self._find_additional_employees_direct(
            needed_count, workstations, session, team_repository, prefetched_data
        )

        if additional_employees:
            # Add the additional employees to our list
            updated_employees.extend(additional_employees)
            return True, updated_employees

        # If we still don't have enough employees, check force_complete
        return self._handle_force_complete(available_count, len(workstations)), updated_employees

    def generate_assignments(self, employees: List["Employee"], workstations: List["Workstation"],
                            rule_context: Optional[Any] = None, session=None, team_repository=None,
                            aro_service=None, aro_graph_service=None, prefetched_data: Optional[Dict] = None) -> bool:
        """
        Generate assignments for this schedule using constraint programming.

        Args:
            employees: List of employees available for scheduling
            workstations: List of workstations to be staffed
            rule_context: Optional pre-configured rule context
            session: Database session for accessing work history data
            team_repository: Optional repository for retrieving team information
            aro_service: Optional ARO service for finding and assigning AROs
            aro_graph_service: Optional ARO graph service for optimizing ARO assignments
            prefetched_data: Optional dictionary containing prefetched data to avoid database queries

        Returns:
            True if assignments were successfully generated, False otherwise
        """
        from domain.rules.registry import get_rules_for_team, create_context_for_team

        # Clear existing assignments if any
        self._assignments = []

        # Check if we have enough employees to cover all workstations
        available_count, aro_count, non_aro_employees = self._check_employee_availability(employees)

        # Handle employee shortage if needed
        if available_count < len(workstations):
            continue_generation, employees = self._handle_employee_shortage(
                employees, workstations, available_count, session, team_repository,
                aro_service, aro_graph_service, prefetched_data
            )

            if not continue_generation:
                return False

        # Setup the constraint model
        model, assign, team_name, ctx = self._setup_constraint_model(
            employees, workstations, rule_context, session, team_repository, prefetched_data
        )

        # Apply rules and set up objective function
        model = self._apply_rules(model, ctx, team_name)

        # Solve the model
        status, solver = self._solve_model(model)

        # Process the solution
        return self._process_solution(status, solver, assign, employees, workstations)

    def _setup_constraint_model(
        self, 
        employees: List["Employee"], 
        workstations: List["Workstation"],
        rule_context: Optional["RuleContext"] = None, 
        session: Optional[Any] = None, 
        team_repository: Optional["TeamRepositoryInterface"] = None, 
        prefetched_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[Any, Dict[Tuple[int, int, int], Any], str, "RuleContext"]:
        """
        Set up the constraint model and define decision variables.

        Args:
            employees: List of employees available for scheduling
            workstations: List of workstations to be staffed
            rule_context: Optional pre-configured rule context
            session: Database session for accessing work history data
            team_repository: Optional repository for retrieving team information
            prefetched_data: Optional dictionary containing prefetched data to avoid database queries

        Returns:
            Tuple containing:
            - CP model
            - Dictionary of decision variables
            - Team name
            - Rule context
        """
        from domain.rules.registry import create_context_for_team

        # Create CP model
        model = cp_model.CpModel()

        # Define decision variables
        assign = {}
        for e, employee in enumerate(employees):
            for w, workstation in enumerate(workstations):
                for p in range(self.periods_per_day):
                    assign[(e, w, p)] = model.NewBoolVar(
                        f'assign_e{e}_w{w}_p{p}')

        # Parse offline parameter
        employee_offline_periods = {}
        if self.offline:
            for emp_name, periods in self.offline.items():
                employee_offline_periods[emp_name] = set(periods)

        # Get team name from team_id
        team_name = "default"  # Default if no repository is provided
        if self.team_id:
            # Try to get team from prefetched data first
            team = None
            if prefetched_data and 'teams_by_id' in prefetched_data and self.team_id in prefetched_data['teams_by_id']:
                team = prefetched_data['teams_by_id'][self.team_id]
            elif team_repository:
                team = team_repository.get(self.team_id)

            if team:
                team_name = team.name.lower()

        # Create or use rule context
        if rule_context is None:
            ctx = create_context_for_team(
                team_name=team_name,
                model=model,
                assign=assign,
                employees=employees,
                workstations=workstations,
                periods=self.periods_per_day,
                start_date=self.start_date,
                lookback=self.DEFAULT_LOOKBACK_DAYS,
                session=session,
                call_ins=self.call_ins,
                employee_offline_periods=employee_offline_periods,
                backup_idx=next((i for i, e in enumerate(employees) if e.has_role("Backup")), None),
                offline_periods={},  # No offline periods for now
                scheduled=[]  # No scheduled assignments for now
            )
        else:
            ctx = rule_context

        return model, assign, team_name, ctx

    def _apply_rules(
        self, 
        model: Any, 
        ctx: "RuleContext", 
        team_name: str
    ) -> Any:
        """
        Apply rules and set up objective function.

        Args:
            model: CP model
            ctx: Rule context
            team_name: Team name

        Returns:
            Updated CP model
        """
        from domain.rules.registry import get_rules_for_team

        # Apply rules
        rules = get_rules_for_team(team_name)
        objective_terms = []

        for rule in rules:
            result = rule(ctx)
            # If the rule returns penalty variables, add them to the objective
            if isinstance(result, list) and result:
                # Get the weight for this rule (default to 10 if not specified)
                weight = self.RULE_WEIGHTS.get(rule.__name__, 10)
                for penalty in result:
                    objective_terms.append(weight * penalty)

        # Set objective function
        if objective_terms:
            model.Minimize(sum(objective_terms))

        return model

    def _solve_model(self, model, time_limit: Optional[float] = None) -> Tuple[int, Any]:
        """
        Solve the constraint model.

        Args:
            model: CP model
            time_limit: Optional custom time limit (overrides default)

        Returns:
            Tuple containing:
            - Status code
            - Solver
        """
        # Solve the model
        solver = cp_model.CpSolver()

        # Use provided time_limit, or default to DEFAULT_SOLVER_TIME_LIMIT
        # but never exceed MAX_SOLVER_TIME_LIMIT
        effective_time_limit = min(
            time_limit or self.DEFAULT_SOLVER_TIME_LIMIT,
            self.MAX_SOLVER_TIME_LIMIT
        )

        solver.parameters.max_time_in_seconds = effective_time_limit
        logger.debug(f"Setting solver time limit to {effective_time_limit} seconds")

        status = solver.Solve(model)

        return status, solver

    def _process_solution(
        self, 
        status: int, 
        solver: Any, 
        assign: Dict[Tuple[int, int, int], Any], 
        employees: List["Employee"], 
        workstations: List["Workstation"]
    ) -> bool:
        """
        Process the solution and create assignments.

        Args:
            status: Status code from solver
            solver: CP solver
            assign: Dictionary of decision variables
            employees: List of employees available for scheduling
            workstations: List of workstations to be staffed

        Returns:
            True if assignments were successfully generated, False otherwise
        """
        # Extract results if solution found
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            # Extract assignments
            current_date = self.start_date
            for period in range(self.periods_per_day):
                for emp_idx, employee in enumerate(employees):
                    for ws_idx, workstation in enumerate(workstations):
                        if solver.Value(assign[(emp_idx, ws_idx, period)]) == 1:
                            # Create a SchedulePeriod for this assignment
                            schedule_period = SchedulePeriod(date=current_date, period=period + 1)

                            # Create and add assignment
                            try:
                                self.create_assignment(employee, workstation, schedule_period)
                            except ValueError as e:
                                # Log error but continue with other assignments
                                logger.warning(f"Team {self.team_id}: Error creating assignment: {str(e)}")
                                self.register_domain_event(ScheduleValidationFailed(
                                    schedule_id=self.id,
                                    validation_errors=[str(e)]
                                ))

            # Update schedule status
            self.set_status("generated")
            logger.info(f"Team {self.team_id}: Generated {len(self._assignments)} assignments")
            return True
        else:
            self.set_status("failed")
            # Get more details about why it failed
            status_name = solver.StatusName(status)
            employee_count = len(employees)
            workstation_count = len(workstations)
            call_ins_count = len(self.call_ins) if self.call_ins else 0

            error_msg = (
                f"No solution found. Status: {status_name}. "
                f"Available employees: {employee_count}, Workstations: {workstation_count}. "
                f"Call-ins: {call_ins_count}. "
                f"Try reducing the number of call-ins or use --force-complete to generate a partial schedule."
            )

            self.set_error_message(error_msg)
            logger.warning(f"Team {self.team_id}: No solution found. Status: {solver.StatusName(status)}")
            return False

    def _find_employees_from_other_teams(
        self, 
        team: "Team", 
        workstations: List["Workstation"], 
        needed_count: int, 
        session: Any, 
        team_repository: "TeamRepositoryInterface", 
        prefetched_data: Optional[Dict[str, Any]] = None
    ) -> List["Employee"]:
        """
        Find employees from other teams who can work on this team's workstations.

        Args:
            team: The team that needs additional employees
            workstations: The workstations that need to be staffed
            needed_count: The number of additional employees needed
            session: Database session for accessing employee data
            team_repository: Repository for retrieving team information
            prefetched_data: Optional dictionary containing prefetched data to avoid database queries

        Returns:
            List of employees from other teams who can work on this team's workstations
        """
        additional_employees = []

        # Get all teams in the same department
        # Since Team doesn't have a direct department_id attribute, we need to get it through the team's group
        # Get the team's group first (use prefetched data if available)
        group = None
        if prefetched_data and 'groups_by_team' in prefetched_data and team.id in prefetched_data['groups_by_team']:
            group = prefetched_data['groups_by_team'][team.id]
        else:
            group = team_repository.get_group(team.id)

        if group and hasattr(group, 'department_id'):
            # Get all teams in the same department (use prefetched data if available)
            department_teams = []
            if prefetched_data and 'teams_by_department' in prefetched_data and group.department_id in prefetched_data['teams_by_department']:
                department_teams = prefetched_data['teams_by_department'][group.department_id]
            else:
                department_teams = team_repository.get_by_department_id(group.department_id)

            # Exclude the current team
            other_teams = [t for t in department_teams if t.id != team.id]
        else:
            # If we can't determine the department, just return an empty list
            other_teams = []

        # For each team, find employees who know the workstations we need
        for other_team in other_teams:
            # Skip if we already have enough employees
            if len(additional_employees) >= needed_count:
                break

            # Get employees from this team (use prefetched data if available)
            team_employees = []
            if prefetched_data and 'employees_by_team' in prefetched_data and other_team.id in prefetched_data['employees_by_team']:
                team_employees = prefetched_data['employees_by_team'][other_team.id]
            else:
                team_employees = team_repository.get_members(other_team.id)

            for employee in team_employees:
                # Skip if we already have enough employees
                if len(additional_employees) >= needed_count:
                    break

                # Check if this employee knows any of our workstations
                for workstation in workstations:
                    if employee.can_work(workstation):
                        # This employee can work on one of our workstations
                        additional_employees.append(employee)
                        break

        return additional_employees

    def _validate_basic_properties(self) -> List[str]:
        """
        Validate basic schedule properties.

        Returns:
            List of validation error messages
        """
        errors = []

        try:
            if not isinstance(self.team_id, int) or self.team_id <= 0:
                errors.append("Team ID must be a positive integer")
            if not isinstance(self.start_date, date):
                errors.append("Start date must be a date object")
            if not isinstance(self.periods_per_day, int) or self.periods_per_day <= 0:
                errors.append("Periods per day must be a positive integer")
            if not isinstance(self.status, str) or not self.status:
                errors.append("Status must be a non-empty string")
        except Exception as e:
            errors.append(f"Error validating basic properties: {str(e)}")

        return errors

    def _validate_assignment_overlaps(self) -> List[str]:
        """
        Check for assignment overlaps (same employee assigned to multiple workstations in the same period).

        Returns:
            List of validation error messages
        """
        errors = []

        try:
            # Dictionary to track employee assignments by date and period
            employee_assignments = {}

            for assignment in self._assignments:
                key = (assignment.employee.id, assignment.period.date, assignment.period.period)
                if key in employee_assignments:
                    existing = employee_assignments[key]
                    errors.append(
                        f"Employee {assignment.employee.name} (ID: {assignment.employee.id}) is assigned to multiple workstations "
                        f"({existing.workstation.name} and {assignment.workstation.name}) "
                        f"on {assignment.period.date} during period {assignment.period.period}"
                    )
                else:
                    employee_assignments[key] = assignment
        except Exception as e:
            errors.append(f"Error checking assignment overlaps: {str(e)}")

        return errors

    def _validate_employee_eligibility(self) -> List[str]:
        """
        Validate employee eligibility/qualification for assigned workstations.

        Returns:
            List of validation error messages
        """
        errors = []

        try:
            for assignment in self._assignments:
                # Check if employee is qualified for the workstation
                if not assignment.employee.can_work(assignment.workstation):
                    errors.append(
                        f"Employee {assignment.employee.name} (ID: {assignment.employee.id}) is not qualified to work at "
                        f"workstation {assignment.workstation.name} (ID: {assignment.workstation.id})"
                    )

                # Check if employee can handle workstation type (heavy, key skill, etc.)
                if not assignment.employee.can_handle_workstation_type(assignment.workstation):
                    errors.append(
                        f"Employee {assignment.employee.name} (ID: {assignment.employee.id}) cannot handle workstation type "
                        f"for {assignment.workstation.name} (ID: {assignment.workstation.id})"
                    )

                # Check if employee is qualified for the line type
                if not assignment.employee.is_qualified_for_line(assignment.workstation.line_type):
                    errors.append(
                        f"Employee {assignment.employee.name} (ID: {assignment.employee.id}) is not qualified for line type "
                        f"{assignment.workstation.line_type} at workstation {assignment.workstation.name}"
                    )

                # Check if employee is available for the assigned period
                if not assignment.employee.is_available_for_period(
                    assignment.period.date, assignment.period.period
                ):
                    errors.append(
                        f"Employee {assignment.employee.name} (ID: {assignment.employee.id}) is not available on "
                        f"{assignment.period.date} during period {assignment.period.period}"
                    )
        except Exception as e:
            errors.append(f"Error checking employee eligibility: {str(e)}")

        return errors

    def _validate_date_ranges(self) -> List[str]:
        """
        Validate date ranges and periods for assignments.

        Returns:
            List of validation error messages
        """
        errors = []

        try:
            for assignment in self._assignments:
                # Check if assignment date is within schedule range
                if assignment.period.date < self.start_date or assignment.period.date > self.end_date:
                    errors.append(
                        f"Assignment for employee {assignment.employee.name} at workstation {assignment.workstation.name} "
                        f"on {assignment.period.date} is outside the schedule date range "
                        f"({self.start_date} to {self.end_date})"
                    )

                # Check if period is valid for this schedule
                if assignment.period.period < 1 or assignment.period.period > self.periods_per_day:
                    errors.append(
                        f"Assignment for employee {assignment.employee.name} at workstation {assignment.workstation.name} "
                        f"has invalid period {assignment.period.period} (valid range: 1-{self.periods_per_day})"
                    )
        except Exception as e:
            errors.append(f"Error checking date ranges and periods: {str(e)}")

        return errors

    def _handle_validation_result(self, validation_errors: List[str]) -> bool:
        """
        Handle the result of validation.

        Args:
            validation_errors: List of validation error messages

        Returns:
            True if validation passes, False otherwise

        Raises:
            ValueError: If validation fails and force_complete is False
        """
        if validation_errors:
            # Log validation errors
            for error in validation_errors:
                logger.warning(f"Team {self.team_id}: Validation error: {error}")

            # Register validation failure event
            self.register_domain_event(ScheduleValidationFailed(
                schedule_id=self.id,
                validation_errors=validation_errors
            ))

            # If force_complete is False, raise an error with all validation failures
            if not self.force_complete:
                raise ValueError(f"Schedule validation failed: {', '.join(validation_errors)}")
            return False

        return True

    def validate(self) -> bool:
        """
        Validates the schedule entity and its assignments.

        Checks:
        1. Basic schedule properties
        2. Assignment overlaps (same employee assigned to multiple workstations in the same period)
        3. Employee eligibility/qualification for assigned workstations
        4. Valid date ranges and periods for assignments

        Returns:
            True if validation passes, False otherwise

        Raises:
            ValueError: If validation fails and force_complete is False
        """
        # Validate basic properties
        validation_errors = self._validate_basic_properties()

        # Skip assignment validations if there are no assignments
        if not self._assignments:
            return self._handle_validation_result(validation_errors)

        # Validate assignments
        validation_errors.extend(self._validate_assignment_overlaps())
        validation_errors.extend(self._validate_employee_eligibility())
        validation_errors.extend(self._validate_date_ranges())

        # Handle validation result
        return self._handle_validation_result(validation_errors)
