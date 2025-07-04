from abc import abstractmethod
from typing import Optional, List

from domain.contexts.user_management.value_objects.role import Role
from domain.repositories.interfaces.base_repository import BaseRepository


class RoleRepositoryInterface(BaseRepository[Role]):
    """
    Interface for role repository operations.
    """

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Role]:
        """
        Retrieve a role by its name.

        Args:
            name: The name of the role to retrieve.

        Returns:
            The role if found, None otherwise.
        """
        pass

    @abstractmethod
    def name_exists(self, name: str) -> bool:
        """
        Check if a role name already exists.

        Args:
            name: The role name to check.

        Returns:
            True if the role name exists, False otherwise.
        """
        pass

    @abstractmethod
    def get_all_roles(self) -> List[Role]:
        """
        Get all roles in the system.

        Returns:
            A list of all roles.
        """
        pass

    @abstractmethod
    def create_role(self, name: str, description: str = None) -> Role:
        """
        Create a new role.

        Args:
            name: The name of the role.
            description: Optional description of the role.

        Returns:
            The created role.
        """
        pass

    @abstractmethod
    def update_role(self, role_id: int, name: str = None, description: str = None) -> Optional[Role]:
        """
        Update an existing role.

        Args:
            role_id: The ID of the role to update.
            name: Optional new name for the role.
            description: Optional new description for the role.

        Returns:
            The updated role if successful, None otherwise.
        """
        pass

    @abstractmethod
    def delete_role(self, role_id: int) -> bool:
        """
        Delete a role.

        Args:
            role_id: The ID of the role to delete.

        Returns:
            True if the role was deleted successfully, False otherwise.
        """
        pass

    @abstractmethod
    def get_roles_for_team_member(self, team_member_id: int) -> List[Role]:
        """
        Get all roles assigned to a team member.
        
        Note: This method creates a cross-context dependency with Employee Management.
        Consider moving to a domain service or using domain events for loose coupling.

        Args:
            team_member_id: The ID of the team member.

        Returns:
            A list of roles assigned to the team member.
        """
        pass

    @abstractmethod
    def assign_role_to_team_member(self, team_member_id: int, role_id: int) -> bool:
        """
        Assign a role to a team member.
        
        Note: This method creates a cross-context dependency with Employee Management.
        Consider moving to a domain service or using domain events for loose coupling.

        Args:
            team_member_id: The ID of the team member.
            role_id: The ID of the role to assign.

        Returns:
            True if the role was assigned successfully, False otherwise.
        """
        pass

    @abstractmethod
    def remove_role_from_team_member(self, team_member_id: int, role_id: int) -> bool:
        """
        Remove a role from a team member.
        
        Note: This method creates a cross-context dependency with Employee Management.
        Consider moving to a domain service or using domain events for loose coupling.

        Args:
            team_member_id: The ID of the team member.
            role_id: The ID of the role to remove.

        Returns:
            True if the role was removed successfully, False otherwise.
        """
        pass