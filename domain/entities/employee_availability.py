# heijunka/domain/entities/employee_availability.py
from dataclasses import dataclass
from datetime import date
from typing import NewType


EmployeeId = NewType('EmployeeId', int)
AvailabilityId = NewType('AvailabilityId', int)


@dataclass
class EmployeeAvailability:
    id: int
    employee_id: int
    date: date
    period: int
    is_partial: bool = False
    is_call_in: bool = False
    is_aro: bool = False
    is_offline: bool = False
