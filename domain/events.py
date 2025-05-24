from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional
import uuid
from domain.value_objects.schedule_period import SchedulePeriod

@dataclass
class DomainEvent:
    """Base class for all domain events"""
    occurred_on: datetime = field(default_factory=datetime.utcnow, init=False)

    def __post_init__(self):
        if self.occurred_on is None:
            self.occurred_on = datetime.utcnow()


@dataclass
class ScheduleEvent(DomainEvent):
    """Base class for schedule-related events"""
    schedule_id: str  # non-default

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.schedule_id, str):
            raise TypeError("schedule_id must be a string")
        if not self.schedule_id or self.schedule_id.isspace():
            raise ValueError("schedule_id cannot be empty or whitespace")

@dataclass
class AssignmentCreated(DomainEvent):
    """Event raised when a new work assignment is created"""
    employee_id: int
    workstation_id: int
    schedule_period: SchedulePeriod

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.employee_id, int):
            raise TypeError("id must be an integer")
        if not isinstance(self.workstation_id, int):
            raise TypeError("workstation_id must be an integer")
        if not isinstance(self.schedule_period, SchedulePeriod):
            raise TypeError("schedule_period must be a SchedulePeriod instance")
        if self.employee_id <= 0:
            raise ValueError("id must be positive")
        if self.workstation_id <= 0:
            raise ValueError("workstation_id must be positive")

@dataclass
class QualificationAdded(DomainEvent):
    """Event raised when a qualification is added to an employee"""
    employee_id: int
    qualification: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.qualification, str) or not self.qualification:
            raise ValueError("qualification must be a non-empty string")

@dataclass
class QualificationRemoved(DomainEvent):
    """Event raised when a qualification is removed from an employee"""
    employee_id: int
    qualification: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.qualification, str) or not self.qualification:
            raise ValueError("qualification must be a non-empty string")

@dataclass
class RoleAssigned(DomainEvent):
    """Event raised when a role is assigned to an employee"""
    employee_id: int
    role: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.role, str) or not self.role:
            raise ValueError("role must be a non-empty string")

@dataclass
class TeamRoleAssigned(DomainEvent):
    """Event raised when a team role is assigned to an employee"""
    employee_id: int
    team_id: int
    role: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.team_id, int) or self.team_id <= 0:
            raise ValueError("team_id must be a positive integer")
        if not isinstance(self.role, str) or not self.role:
            raise ValueError("role must be a non-empty string")

@dataclass
class WorkHistoryEntryAdded(DomainEvent):
    """Event raised when a work history entry is added to an employee"""
    employee_id: int
    workstation_id: int
    worked_date: date
    work_period: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.worked_date, date):
            raise ValueError("worked_date must be a date object")
        if not isinstance(self.work_period, int) or not 1 <= self.work_period <= 5:
            raise ValueError("work_period must be an integer between 1 and 5")
