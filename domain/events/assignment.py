from dataclasses import dataclass
from typing import Optional
from .base import DomainEvent
from domain.value_objects.schedule_period import SchedulePeriod

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
class AssignmentAdded(DomainEvent):
    """Event raised when an assignment is added to a schedule"""
    schedule_id: int
    employee_id: int
    workstation_id: int
    period: SchedulePeriod

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.schedule_id, int) or self.schedule_id <= 0:
            raise ValueError("schedule_id must be a positive integer")
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.period, SchedulePeriod):
            raise ValueError("period must be a SchedulePeriod instance")

@dataclass
class AssignmentRemoved(DomainEvent):
    """Event raised when an assignment is removed from a schedule"""
    schedule_id: int
    employee_id: int
    workstation_id: int
    period: SchedulePeriod

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.schedule_id, int) or self.schedule_id <= 0:
            raise ValueError("schedule_id must be a positive integer")
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.period, SchedulePeriod):
            raise ValueError("period must be a SchedulePeriod instance")