# domain/value_objects/employee_training.py
from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass(frozen=True)
class EmployeeTraining:
    """
    Value object representing an employee's training record for a specific workstation.
    """
    employee_id: int
    workstation_id: int
    required_training: bool = True
    date_completed: Optional[date] = None

    def __post_init__(self):
        """Validate the employee training record."""
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.required_training, bool):
            raise ValueError("required_training must be a boolean")
        if self.date_completed is not None and not isinstance(self.date_completed, date):
            raise ValueError("date_completed must be a date object or None")