# heijunka/domain/entities/schedule.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Tuple
from datetime import date, timedelta

from ortools.sat.python import cp_model

from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment
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

        # Register creation event
        if self.id > 0 and isinstance(self.team_id, int) and self.team_id > 0:  # Only register if this is a real entity with valid team_id
            try:
                self.register_domain_event(ScheduleCreated(
                    schedule_id=self.id,
                    team_id=self.team_id,
                    start_date=self.start_date,
                    periods_per_day=self.periods_per_day
                ))
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
        end_date = self.start_date
        if period.date < self.start_date or period.date > end_date:
            raise ValueError(f"Period {period} is outside schedule date range")

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

        if error_message is not None or error_message is None and self.error_message is not None:
            updated = self.set_error_message(error_message) or updated

        if task_id is not None or task_id is None and self.task_id is not None:
            updated = self.set_task_id(task_id) or updated

        if updated:
            self.register_domain_event(ScheduleUpdated(schedule_id=self.id))

    def generate_assignments(self, employees: List["Employee"], workstations: List["Workstation"],
                            rule_context: Optional[Any] = None, session=None, team_repository=None) -> bool:
        """
        Generate assignments for this schedule using constraint programming.

        Args:
            employees: List of employees available for scheduling
            workstations: List of workstations to be staffed
            rule_context: Optional pre-configured rule context
            session: Database session for accessing work history data
            team_repository: Optional repository for retrieving team information

        Returns:
            True if assignments were successfully generated, False otherwise
        """
        from domain.rules.registry import get_rules_for_team, create_context_for_team

        # Clear existing assignments if any
        self._assignments = []

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

        # Create or use rule context
        if rule_context is None:
            # Get team name from team_id
            team_name = "default"  # Default if no repository is provided
            if team_repository and self.team_id:
                team = team_repository.get(self.team_id)
                if team:
                    team_name = team.name.lower()

            ctx = create_context_for_team(
                team_name=team_name,
                model=model,
                assign=assign,
                employees=employees,
                workstations=workstations,
                periods=self.periods_per_day,
                start_date=self.start_date,
                lookback=3,  # Default lookback of 3 days
                session=session,
                call_ins=self.call_ins,
                employee_offline_periods=employee_offline_periods,
                backup_idx=next((i for i, e in enumerate(employees) if e.has_role("Backup")), None),
                offline_periods={},  # No offline periods for now
                scheduled=[]  # No scheduled assignments for now
            )
        else:
            ctx = rule_context

        # Apply rules
        rules = get_rules_for_team(team_name)
        objective_terms = []

        # Define weights for different rule types
        rule_weights = {
            "add_rotation_penalties": 1000,
            "add_repeat_station_penalties": 100,
            "add_workload_deviation": 200,
            "add_compound_fatigue_penalty_daylevel": 2000,
            "add_compound_fatigue_repetition_penalty": 5000,
            "add_cross_day_repeat_penalties": 500,
            "add_consecutive_day_combo_penalties": 100,
            "add_historical_station_fairness": 10000
        }

        for rule in rules:
            result = rule(ctx)
            # If the rule returns penalty variables, add them to the objective
            if isinstance(result, list) and result:
                # Get the weight for this rule (default to 10 if not specified)
                weight = rule_weights.get(rule.__name__, 10)
                for penalty in result:
                    objective_terms.append(weight * penalty)

        # Set objective function
        if objective_terms:
            model.Minimize(sum(objective_terms))

        # Solve the model
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = min(30 / 10, 300)
        status = solver.Solve(model)

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
                                self.register_domain_event(ScheduleValidationFailed(
                                    schedule_id=self.id,
                                    validation_errors=[str(e)]
                                ))

            # Update schedule status
            self.set_status("generated")
            return True
        else:
            # No solution found
            self.set_status("failed")
            self.set_error_message(f"No solution found. Status: {solver.StatusName(status)}")
            return False

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
        validation_errors = []

        # 1. Basic schedule property validation
        try:
            if not isinstance(self.team_id, int) or self.team_id <= 0:
                validation_errors.append("Team ID must be a positive integer")
            if not isinstance(self.start_date, date):
                validation_errors.append("Start date must be a date object")
            if not isinstance(self.periods_per_day, int) or self.periods_per_day <= 0:
                validation_errors.append("Periods per day must be a positive integer")
            if not isinstance(self.status, str) or not self.status:
                validation_errors.append("Status must be a non-empty string")
        except Exception as e:
            validation_errors.append(f"Error validating basic properties: {str(e)}")

        # Calculate the end date of the schedule
        try:
            end_date = self.start_date
        except Exception:
            validation_errors.append("Cannot calculate end date")
            end_date = None

        # Skip assignment validations if there are no assignments
        if not self._assignments:
            if validation_errors:
                self.register_domain_event(ScheduleValidationFailed(
                    schedule_id=self.id,
                    validation_errors=validation_errors
                ))
                if not self.force_complete:
                    raise ValueError(f"Schedule validation failed: {', '.join(validation_errors)}")
                return False
            return True

        # 2. Check for assignment overlaps
        try:
            # Dictionary to track employee assignments by date and period
            employee_assignments = {}

            for assignment in self._assignments:
                key = (assignment.employee.id, assignment.period.date, assignment.period.period)
                if key in employee_assignments:
                    existing = employee_assignments[key]
                    validation_errors.append(
                        f"Employee {assignment.employee.name} (ID: {assignment.employee.id}) is assigned to multiple workstations "
                        f"({existing.workstation.name} and {assignment.workstation.name}) "
                        f"on {assignment.period.date} during period {assignment.period.period}"
                    )
                else:
                    employee_assignments[key] = assignment
        except Exception as e:
            validation_errors.append(f"Error checking assignment overlaps: {str(e)}")

        # 3. Check employee eligibility/qualification
        try:
            for assignment in self._assignments:
                # Check if employee is qualified for the workstation
                if not assignment.employee.can_work(assignment.workstation):
                    validation_errors.append(
                        f"Employee {assignment.employee.name} (ID: {assignment.employee.id}) is not qualified to work at "
                        f"workstation {assignment.workstation.name} (ID: {assignment.workstation.id})"
                    )

                # Check if employee can handle workstation type (heavy, key skill, etc.)
                if not assignment.employee.can_handle_workstation_type(assignment.workstation):
                    validation_errors.append(
                        f"Employee {assignment.employee.name} (ID: {assignment.employee.id}) cannot handle workstation type "
                        f"for {assignment.workstation.name} (ID: {assignment.workstation.id})"
                    )

                # Check if employee is qualified for the line type
                if not assignment.employee.is_qualified_for_line(assignment.workstation.line_type):
                    validation_errors.append(
                        f"Employee {assignment.employee.name} (ID: {assignment.employee.id}) is not qualified for line type "
                        f"{assignment.workstation.line_type} at workstation {assignment.workstation.name}"
                    )

                # Check if employee is available for the assigned period
                if not assignment.employee.is_available_for_period(
                    assignment.period.date, assignment.period.period
                ):
                    validation_errors.append(
                        f"Employee {assignment.employee.name} (ID: {assignment.employee.id}) is not available on "
                        f"{assignment.period.date} during period {assignment.period.period}"
                    )
        except Exception as e:
            validation_errors.append(f"Error checking employee eligibility: {str(e)}")

        # 4. Check valid date ranges and periods
        try:
            if end_date:
                for assignment in self._assignments:
                    # Check if assignment date is within schedule range
                    if assignment.period.date < self.start_date or assignment.period.date > end_date:
                        validation_errors.append(
                            f"Assignment for employee {assignment.employee.name} at workstation {assignment.workstation.name} "
                            f"on {assignment.period.date} is outside the schedule date range "
                            f"({self.start_date} to {end_date})"
                        )

                    # Check if period is valid for this schedule
                    if assignment.period.period < 1 or assignment.period.period > self.periods_per_day:
                        validation_errors.append(
                            f"Assignment for employee {assignment.employee.name} at workstation {assignment.workstation.name} "
                            f"has invalid period {assignment.period.period} (valid range: 1-{self.periods_per_day})"
                        )
        except Exception as e:
            validation_errors.append(f"Error checking date ranges and periods: {str(e)}")

        # Register validation failure event if there are errors
        if validation_errors:
            self.register_domain_event(ScheduleValidationFailed(
                schedule_id=self.id,
                validation_errors=validation_errors
            ))

            # If force_complete is False, raise an error with all validation failures
            if not self.force_complete:
                raise ValueError(f"Schedule validation failed: {', '.join(validation_errors)}")
            return False

        return True
