from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass(frozen=True)
class AROAssignment:
    """
    Value object representing an employee's ARO assignment to another team.
    """
    employee_id: int
    from_team_id: int
    to_team_id: int
    assignment_date: date
    period: Optional[int] = None  # Can be None for full-day assignments
    
    def __post_init__(self):
        """Validate the ARO assignment."""
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.from_team_id, int) or self.from_team_id <= 0:
            raise ValueError("from_team_id must be a positive integer")
        if not isinstance(self.to_team_id, int) or self.to_team_id <= 0:
            raise ValueError("to_team_id must be a positive integer")
        if not isinstance(self.assignment_date, date):
            raise ValueError("assignment_date must be a date object")
        if self.period is not None and (not isinstance(self.period, int) or not 1 <= self.period <= 5):
            raise ValueError("period must be None or an integer between 1 and 5")