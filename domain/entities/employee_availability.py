# heijunka/domain/entities/employee_availability.py
from dataclasses import dataclass, frozen
from datetime import date
from typing import NewType, Optional
from enum import Enum


EmployeeId = NewType('EmployeeId', int)


class AvailabilityStatus(Enum):
    AVAILABLE = "available"       # Fully available
    PARTIAL = "partial"           # Available for some periods but not others
    CALL_IN = "call_in"           # Called in sick/unavailable
    ARO = "aro"                   # Annual Required Off
    OFFLINE = "offline"           # Offline for specific period(s)


@dataclass(frozen=True)
class EmployeeAvailability:
    employee_id: int
    date: date
    period: Optional[int] = None  # Can be None for full-day statuses like CALL_IN or ARO
    status: AvailabilityStatus = AvailabilityStatus.AVAILABLE
