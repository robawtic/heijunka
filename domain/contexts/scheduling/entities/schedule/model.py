# heijunka/domain/contexts/scheduling/entities/schedule/model.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, cast
from datetime import date
import logging

# Logger for this module
logger = logging.getLogger(__name__)

from domain.contexts.scheduling.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment
from domain.contexts.employee_management.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.contexts.scheduling.entities.schedule.events import ScheduleValidationFailed
from domain.contexts.scheduling.entities.schedule.assignment import create_and_add_assignment
from .events import (
    DomainEvent, ScheduleCreated, ScheduleUpdated, ScheduleStatusChanged
)

@dataclass
class Schedule:
    """
    Schedule aggregate root entity.

    Represents a work schedule for a team, containing assignments of employees to workstations.
    """
    # Instance attributes
    id: int
    team_id: int
    start_date: date
    periods_per_day: int
    status: str
    call_ins: List[str] = field(default_factory=list)
    offline: dict = field(default_factory=dict)
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
        from domain.contexts.scheduling.entities.schedule.assignment import add_assignment
        return add_assignment(self, assignment)

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
        from domain.contexts.scheduling.entities.schedule.assignment import remove_assignment
        return remove_assignment(self, employee_id, workstation_id, period)

    def create_and_add_assignment(self, employee: Employee, workstation: "Workstation", 
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
        return create_and_add_assignment(self, employee, workstation, period)

    def get_assignments_for_date(self, date_obj: date) -> List[WorkAssignment]:
        """
        Get all assignments for a specific date.

        Args:
            date_obj: The date to get assignments for.

        Returns:
            A list of assignments for the date.
        """
        from domain.contexts.scheduling.entities.schedule.assignment import get_assignments_for_date
        return get_assignments_for_date(self, date_obj)

    def get_assignments_for_employee(self, employee_id: int) -> List[WorkAssignment]:
        """
        Get all assignments for a specific employee.

        Args:
            employee_id: The ID of the employee.

        Returns:
            A list of assignments for the employee.
        """
        from domain.contexts.scheduling.entities.schedule.assignment import get_assignments_for_employee
        return get_assignments_for_employee(self, employee_id)

    def get_assignments_for_workstation(self, workstation_id: int) -> List[WorkAssignment]:
        """
        Get all assignments for a specific workstation.

        Args:
            workstation_id: The ID of the workstation.

        Returns:
            A list of assignments for the workstation.
        """
        from domain.contexts.scheduling.entities.schedule.assignment import get_assignments_for_workstation
        return get_assignments_for_workstation(self, workstation_id)

    def validate(self) -> List[str]:
        """
        Validate the schedule and return a list of validation errors.

        Returns:
            A list of validation error messages. Empty list if valid.
        """
        from domain.contexts.scheduling.entities.schedule.validation import (
            validate_basic_properties, validate_assignment_overlaps, validate_employee_eligibility
        )
        
        errors = []
        errors.extend(validate_basic_properties(self))
        errors.extend(validate_assignment_overlaps(self))
        errors.extend(validate_employee_eligibility(self))
        
        if errors:
            self.register_domain_event(ScheduleValidationFailed(
                schedule_id=self.id,
                errors=errors
            ))
        
        return errors

    def is_valid(self) -> bool:
        """
        Check if the schedule is valid.

        Returns:
            True if the schedule is valid, False otherwise.
        """
        return len(self.validate()) == 0

    def get_period_assignments(self, date_obj: date, period: int) -> List[WorkAssignment]:
        """
        Get all assignments for a specific date and period.

        Args:
            date_obj: The date to get assignments for.
            period: The period to get assignments for.

        Returns:
            A list of assignments for the date and period.
        """
        return [a for a in self._assignments 
                if a.period.date == date_obj and a.period.period == period]

    def get_employee_assignment(self, employee_id: int, date_obj: date, period: int) -> Optional[WorkAssignment]:
        """
        Get the assignment for a specific employee on a specific date and period.

        Args:
            employee_id: The ID of the employee.
            date_obj: The date to check.
            period: The period to check.

        Returns:
            The assignment if found, None otherwise.
        """
        for assignment in self._assignments:
            if (assignment.employee.id == employee_id and 
                assignment.period.date == date_obj and 
                assignment.period.period == period):
                return assignment
        return None

    def get_workstation_assignment(self, workstation_id: int, date_obj: date, period: int) -> Optional[WorkAssignment]:
        """
        Get the assignment for a specific workstation on a specific date and period.

        Args:
            workstation_id: The ID of the workstation.
            date_obj: The date to check.
            period: The period to check.

        Returns:
            The assignment if found, None otherwise.
        """
        for assignment in self._assignments:
            if (assignment.workstation.id == workstation_id and 
                assignment.period.date == date_obj and 
                assignment.period.period == period):
                return assignment
        return None

    def has_assignment(self, employee_id: int, workstation_id: int, date_obj: date, period: int) -> bool:
        """
        Check if there's an assignment for the given parameters.

        Args:
            employee_id: The ID of the employee.
            workstation_id: The ID of the workstation.
            date_obj: The date to check.
            period: The period to check.

        Returns:
            True if an assignment exists, False otherwise.
        """
        for assignment in self._assignments:
            if (assignment.employee.id == employee_id and 
                assignment.workstation.id == workstation_id and 
                assignment.period.date == date_obj and 
                assignment.period.period == period):
                return True
        return False

    def get_assignment_count(self) -> int:
        """
        Get the total number of assignments in the schedule.

        Returns:
            The number of assignments.
        """
        return len(self._assignments)

    def get_assignments_by_date(self) -> Dict[date, List[WorkAssignment]]:
        """
        Get assignments grouped by date.

        Returns:
            A dictionary mapping dates to lists of assignments.
        """
        assignments_by_date = {}
        for assignment in self._assignments:
            date_obj = assignment.period.date
            if date_obj not in assignments_by_date:
                assignments_by_date[date_obj] = []
            assignments_by_date[date_obj].append(assignment)
        return assignments_by_date

    def get_assignments_by_employee(self) -> Dict[int, List[WorkAssignment]]:
        """
        Get assignments grouped by employee ID.

        Returns:
            A dictionary mapping employee IDs to lists of assignments.
        """
        assignments_by_employee = {}
        for assignment in self._assignments:
            employee_id = assignment.employee.id
            if employee_id not in assignments_by_employee:
                assignments_by_employee[employee_id] = []
            assignments_by_employee[employee_id].append(assignment)
        return assignments_by_employee

    def get_assignments_by_workstation(self) -> Dict[int, List[WorkAssignment]]:
        """
        Get assignments grouped by workstation ID.

        Returns:
            A dictionary mapping workstation IDs to lists of assignments.
        """
        assignments_by_workstation = {}
        for assignment in self._assignments:
            workstation_id = assignment.workstation.id
            if workstation_id not in assignments_by_workstation:
                assignments_by_workstation[workstation_id] = []
            assignments_by_workstation[workstation_id].append(assignment)
        return assignments_by_workstation

    def clear_assignments(self) -> None:
        """Clear all assignments from the schedule."""
        self._assignments.clear()

    def __repr__(self) -> str:
        return (f"<Schedule(id={self.id}, team_id={self.team_id}, "
                f"start_date={self.start_date}, status={self.status}, "
                f"assignments={len(self._assignments)})>")