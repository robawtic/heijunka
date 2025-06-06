# heijunka/domain/entities/team_aro.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class TeamAro:
    """
    Domain entity representing an employee's eligibility to serve as an ARO for a team.

    Attributes:
        id: Optional unique identifier for the TeamAro relationship.
        employee_id: The ID of the employee.
        team_id: The ID of the team the employee can ARO for.
        status: The status of the eligibility ('active' or 'inactive').
    """
    id: Optional[int]
    employee_id: int
    team_id: int
    status: str

    def is_active(self) -> bool:
        """Return True if this ARO relationship is active."""
        return self.status == 'active'

    def is_inactive(self) -> bool:
        """Return True if this ARO relationship is inactive."""
        return self.status == 'inactive'