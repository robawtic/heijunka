from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TeamMember:
    team_member_id: int
    team_id: int
    employee_id: int
    roles: List[str] = None  # List of role names assigned to the team member
    team: Optional['Team'] = None  # Back-reference to the team
    employee: Optional['Employee'] = None  # Back-reference to the employee

    def __post_init__(self):
        if self.roles is None:
            self.roles = []

    def add_role(self, role_name: str) -> bool:
        """
        Add a role to the team member.

        Args:
            role_name: The name of the role to add.

        Returns:
            True if the role was added, False if it already exists.
        """
        if role_name in self.roles:
            return False
        self.roles.append(role_name)
        return True

    def remove_role(self, role_name: str) -> bool:
        """
        Remove a role from the team member.

        Args:
            role_name: The name of the role to remove.

        Returns:
            True if the role was removed, False if it didn't exist.
        """
        if role_name not in self.roles:
            return False
        self.roles.remove(role_name)
        return True

    def has_role(self, role_name: str) -> bool:
        """
        Check if the team member has a specific role.

        Args:
            role_name: The name of the role to check.

        Returns:
            True if the team member has the role, False otherwise.
        """
        return role_name in self.roles