# heijunka/domain/contexts/employee_management/value_objects/work_history_entry.py
from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass(frozen=True)
class WorkHistoryEntry:
    """
    Value object representing an entry in an employee's work history.
    """
    employee_id: int
    workstation_id: int
    worked_date: date
    work_period: int
    end_flag: bool = False

    def __post_init__(self):
        """Validate the work history entry."""
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.worked_date, date):
            raise ValueError("worked_date must be a date object")
        if not isinstance(self.work_period, int) or not 1 <= self.work_period <= 5:
            raise ValueError("work_period must be an integer between 1 and 5")
        if not isinstance(self.end_flag, bool):
            raise ValueError("end_flag must be a boolean")