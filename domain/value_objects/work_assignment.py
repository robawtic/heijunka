# domain/value_objects/work_assignment.py
from dataclasses import dataclass
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from .schedule_period import SchedulePeriod

@dataclass(frozen=True)
class WorkAssignment:
    employee: Employee
    workstation: Workstation
    period: SchedulePeriod


