# heijunka/domain/entities/schedule.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import date

from domain.events import (
    DomainEvent, AssignmentCreated, ScheduleCreated, ScheduleUpdated,
    ScheduleStatusChanged, AssignmentAdded, AssignmentRemoved
)
from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment


@dataclass
class Schedule:
    """
    Schedule aggregate root entity.

    Represents a work schedule for a team, containing assignments of employees to workstations
    for specific periods.
    """
    id: int
    team_id: int
    start_date: date
    days: int = 1
    periods_per_day: int = 4
    status: str = "pending"
    call_ins: Optional[List[str]] = None
    offline: Optional[Dict[str, List[int]]] = None
    force_complete: bool = False
    error_message: Optional[str] = None
    task_id: Optional[str] = None
    _assignments: List[WorkAssignment] = field(default_factory=list, repr=False)
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Initialize collections if they are None."""
        if self._assignments is None:
            self._assignments = []
        if self._domain_events is None:
            self._domain_events = []
        if self.call_ins is None:
            self.call_ins = []
        if self.offline is None:
            self.offline = {}

        # Register creation event
        if self.id > 0:  # Only register if this is a real entity (not a placeholder)
            self.register_domain_event(ScheduleCreated(
                schedule_id=self.id,
                team_id=self.team_id,
                start_date=self.start_date,
                days=self.days,
                periods_per_day=self.periods_per_day
            ))

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

        # Check if the assignment is already in the schedule
        for existing_assignment in self._assignments:
            if (existing_assignment.employee.id == assignment.employee.id and
                existing_assignment.workstation.id == assignment.workstation.id and
                existing_assignment.period.date == assignment.period.date and
                existing_assignment.period.period == assignment.period.period):
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
                removed_assignment = self._assignments.pop(i)

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

    def update(self, 
               status: Optional[str] = None,
               error_message: Optional[str] = None,
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

        if error_message is not None:
            updated = self.set_error_message(error_message) or updated

        if task_id is not None:
            if self.task_id != task_id:
                self.task_id = task_id
                updated = True

        if updated:
            self.register_domain_event(ScheduleUpdated(schedule_id=self.id))

    def validate(self) -> None:
        """
        Validates the schedule entity.
        Raises ValueError if validation fails.
        """
        if not isinstance(self.team_id, int) or self.team_id <= 0:
            raise ValueError("Team ID must be a positive integer")
        if not isinstance(self.start_date, date):
            raise ValueError("Start date must be a date object")
        if not isinstance(self.days, int) or self.days <= 0:
            raise ValueError("Days must be a positive integer")
        if not isinstance(self.periods_per_day, int) or self.periods_per_day <= 0:
            raise ValueError("Periods per day must be a positive integer")
        if not isinstance(self.status, str) or not self.status:
            raise ValueError("Status must be a non-empty string")

