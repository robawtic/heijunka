# heijunka/domain/contexts/employee_management/value_objects/workstation_assignment.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class WorkstationAssignment:
    """
    Value object representing an assignment of an employee to a workstation.
    """
    employee_id: int
    workstation_id: int
    workstation_name: str

    def __post_init__(self):
        """Validate the workstation assignment."""
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.workstation_name, str) or not self.workstation_name:
            raise ValueError("workstation_name must be a non-empty string")