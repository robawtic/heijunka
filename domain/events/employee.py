from dataclasses import dataclass
from datetime import date
from typing import Optional
from .base import DomainEvent

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
    work_date: date
    period: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.work_date, date):
            raise ValueError("work_date must be a date object")
        if not isinstance(self.period, int) or not 1 <= self.period <= 5:
            raise ValueError("period must be an integer between 1 and 5")