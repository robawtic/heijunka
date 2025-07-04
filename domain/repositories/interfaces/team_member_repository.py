from abc import abstractmethod
from typing import List, Optional

from domain.contexts.employee_management.entities.team_member import TeamMember
from domain.repositories.interfaces.base_repository import BaseRepository


class TeamMemberRepositoryInterface(BaseRepository[TeamMember]):
    """
    Interface for team member repository operations.
    """

    @abstractmethod
    def get_by_team_id(self, team_id: int) -> List[TeamMember]:
        """
        Retrieve all team members for a specific team.

        Args:
            team_id: The ID of the team.

        Returns:
            A list of team members that belong to the team.
        """
        pass

    @abstractmethod
    def get_by_employee_id(self, employee_id: int) -> List[TeamMember]:
        """
        Retrieve all team memberships for a specific employee.

        Args:
            employee_id: The ID of the employee.

        Returns:
            A list of team members that represent the employee's team memberships.
        """
        pass

    @abstractmethod
    def add_role(self, team_member_id: int, role_name: str) -> bool:
        """
        Add a role to a team member.

        Args:
            team_member_id: The ID of the team member.
            role_name: The name of the role to add.

        Returns:
            True if the role was added successfully, False otherwise.
        """
        pass

    @abstractmethod
    def remove_role(self, team_member_id: int, role_name: str) -> bool:
        """
        Remove a role from a team member.

        Args:
            team_member_id: The ID of the team member.
            role_name: The name of the role to remove.

        Returns:
            True if the role was removed successfully, False otherwise.
        """
        pass

    @abstractmethod
    def get_roles(self, team_member_id: int) -> List[str]:
        """
        Get all roles assigned to a team member.

        Args:
            team_member_id: The ID of the team member.

        Returns:
            A list of role names assigned to the team member.
        """
        pass

    @abstractmethod
    def get_by_team_and_employee(self, team_id: int, employee_id: int) -> Optional[TeamMember]:
        """
        Retrieve a team member by team ID and employee ID.

        Args:
            team_id: The ID of the team.
            employee_id: The ID of the employee.

        Returns:
            The team member if found, None otherwise.
        """
        pass
