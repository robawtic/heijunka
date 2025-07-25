# domain/contexts/assignment/entities/work_assignment.py
from dataclasses import dataclass
from typing import TYPE_CHECKING
from domain.contexts.scheduling.value_objects.schedule_period import SchedulePeriod

if TYPE_CHECKING:
    from domain.contexts.employee_management.entities.employee import Employee
    from domain.contexts.workstation_management.entities.workstation import Workstation

@dataclass(frozen=True)
class WorkAssignment:
    employee: "Employee"
    workstation: "Workstation"
    period: SchedulePeriod
