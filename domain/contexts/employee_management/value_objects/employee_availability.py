# heijunka/domain/contexts/employee_management/value_objects/employee_availability.py
from dataclasses import dataclass
from datetime import date
from typing import NewType, Optional
from enum import Enum


EmployeeId = NewType('EmployeeId', int)


class AvailabilityStatus(Enum):
    AVAILABLE = "available"       # Fully available
    PARTIAL = "partial"           # Available for some periods but not others
    CALL_IN = "call_in"           # Called in sick/unavailable
    ARO = "aro"                   # Auxiliary Relief Operator
    OFFLINE = "offline"           # Offline for specific period(s)


@dataclass(frozen=True)
class EmployeeAvailability:
    """
    Value object representing an employee's availability for a specific date and period.
    """
    employee_id: int
    date: date
    period: Optional[int] = None  # Can be None for full-day statuses like CALL_IN or ARO
    status: AvailabilityStatus = AvailabilityStatus.AVAILABLE

    def __post_init__(self):
        """Validate the employee availability."""
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.date, date):
            raise ValueError("date must be a date object")
        if self.period is not None and (not isinstance(self.period, int) or not 1 <= self.period <= 5):
            raise ValueError("period must be None or an integer between 1 and 5")
        if not isinstance(self.status, AvailabilityStatus):
            raise ValueError("status must be an AvailabilityStatus enum value")