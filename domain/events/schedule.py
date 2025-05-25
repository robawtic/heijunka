from dataclasses import dataclass
from datetime import date
from typing import List, Optional
from .base import DomainEvent

@dataclass
class ScheduleEvent(DomainEvent):
    """Base class for schedule-related events"""
    schedule_id: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.schedule_id, str):
            raise TypeError("schedule_id must be a string")
        if not self.schedule_id or self.schedule_id.isspace():
            raise ValueError("schedule_id cannot be empty or whitespace")

@dataclass
class ScheduleCreated(DomainEvent):
    """Event raised when a new schedule is created"""
    schedule_id: int
    team_id: int
    start_date: date
    periods_per_day: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.schedule_id, int) or self.schedule_id <= 0:
            raise ValueError("schedule_id must be a positive integer")
        if not isinstance(self.team_id, int) or self.team_id <= 0:
            raise ValueError("team_id must be a positive integer")
        if not isinstance(self.start_date, date):
            raise ValueError("start_date must be a date object")
        if not isinstance(self.periods_per_day, int) or self.periods_per_day <= 0:
            raise ValueError("periods_per_day must be a positive integer")

@dataclass
class ScheduleUpdated(DomainEvent):
    """Event raised when a schedule is updated"""
    schedule_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.schedule_id, int) or self.schedule_id <= 0:
            raise ValueError("schedule_id must be a positive integer")

@dataclass
class ScheduleStatusChanged(DomainEvent):
    """Event raised when a schedule's status is changed"""
    schedule_id: int
    old_status: str
    new_status: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.schedule_id, int) or self.schedule_id <= 0:
            raise ValueError("schedule_id must be a positive integer")
        if not isinstance(self.old_status, str):
            raise ValueError("old_status must be a string")
        if not isinstance(self.new_status, str) or not self.new_status:
            raise ValueError("new_status must be a non-empty string")

@dataclass
class ScheduleValidationFailed(DomainEvent):
    """Event raised when schedule validation fails"""
    schedule_id: int
    validation_errors: List[str]

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.schedule_id, int) or self.schedule_id <= 0:
            raise ValueError("schedule_id must be a positive integer")
        if not isinstance(self.validation_errors, list):
            raise ValueError("validation_errors must be a list")
        if not all(isinstance(error, str) for error in self.validation_errors):
            raise ValueError("All validation errors must be strings")