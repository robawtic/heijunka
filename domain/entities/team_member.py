from dataclasses import dataclass, field
from typing import List, Optional

from domain.contexts.user_management.value_objects.role import Role


@dataclass
class TeamMember:
    team_member_id: Optional[int] = None  # Assigned by repository/persistence layer
    team_id: int = 0
    employee_id: int = 0
    roles: List[Role] = field(default_factory=list)  # List of roles assigned to the team member
    team: Optional['Team'] = None  # Back-reference to the team
    employee: Optional['Employee'] = None  # Back-reference to the employee

    def __post_init__(self):
        if self.roles is None:
            self.roles = []

    def add_role(self, role: Role) -> bool:
        """
        Add a role to the team member.

        Args:
            role: The role to add.

        Returns:
            True if the role was added, False if it already exists.
        """
        if any(r.name == role.name for r in self.roles):
            return False
        self.roles.append(role)
        return True

    def remove_role(self, role_name: str) -> bool:
        """
        Remove a role from the team member.

        Args:
            role_name: The name of the role to remove.

        Returns:
            True if the role was removed, False if it didn't exist.
        """
        initial_length = len(self.roles)
        self.roles = [role for role in self.roles if role.name != role_name]
        return len(self.roles) < initial_length

    def has_role(self, role_name: str) -> bool:
        """
        Check if the team member has a specific role.

        Args:
            role_name: The name of the role to check.

        Returns:
            True if the team member has the role, False otherwise.
        """
        return any(role.name == role_name for role in self.roles)
