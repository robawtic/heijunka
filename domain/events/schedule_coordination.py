from dataclasses import dataclass
from datetime import date
from domain.events.base import DomainEvent

@dataclass
class AROTransferRequested(DomainEvent):
    """Event raised when an ARO transfer is requested between teams."""
    employee_id: int
    from_team_id: int
    to_team_id: int
    assignment_date: date
    period: int = None  # None means full day

@dataclass
class ScheduleGenerationCompleted(DomainEvent):
    """Event raised when a schedule generation is completed."""
    team_id: int
    start_date: date
    periods_per_day: int
    assignment_count: int

@dataclass
class ScheduleRegenerationNeeded(DomainEvent):
    """Event raised when a schedule needs to be regenerated."""
    team_id: int
    reason: str