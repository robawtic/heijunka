# heijunka/domain/entities/schedule/events.py
from domain.events import (
    ScheduleCreated,
    ScheduleUpdated,
    ScheduleStatusChanged,
    AssignmentAdded,
    AssignmentRemoved,
    ScheduleValidationFailed,
    DomainEvent
)