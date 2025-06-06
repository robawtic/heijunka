from abc import abstractmethod
from typing import Optional, List

from domain.entities.team_aro import TeamAro
from domain.repositories.interfaces.base_repository import BaseRepository

class TeamAroRepositoryInterface(BaseRepository[TeamAro]):
    """
    Interface for TeamAro repository operations.
    """

    @abstractmethod
    def get(self, team_aro_id: int) -> Optional[TeamAro]:
        """
        Retrieve a TeamAro relationship by its ID.

        Args:
            team_aro_id: The ID of the TeamAro relationship to retrieve.

        Returns:
            A TeamAro object if found, None otherwise.
        """

    @abstractmethod
    def get_by_employee_id(self, employee_id: int) -> List[TeamAro]:
        """
        Retrieve all TeamAro relationships for a specific employee.

        Args:
            employee_id: The ID of the employee.

        Returns:
            A list of TeamAro relationships for the employee.
        """
        pass

    @abstractmethod
    def get_by_team_id(self, team_id: int) -> List[TeamAro]:
        """
        Retrieve all TeamAro relationships for a specific team.

        Args:
            team_id: The ID of the team.

        Returns:
            A list of TeamAro relationships for the team.
        """
        pass

    @abstractmethod
    def get_by_status(self, status: str) -> List[TeamAro]:
        """
        Retrieve all TeamAro relationships with a specific status.

        Args:
            status: The status to filter by (e.g., "active", "inactive").

        Returns:
            A list of TeamAro relationships with the specified status.
        """
        pass

    @abstractmethod
    def add(self, team_aro: TeamAro) -> TeamAro:
        """
        Add a new TeamAro relationship.

        Args:
            team_aro: The TeamAro entity to add.

        Returns:
            The added TeamAro entity (possibly with an assigned ID).
        """
        pass

    @abstractmethod
    def update_status(self, team_aro_id: int, new_status: str) -> bool:
        """
        Update the status of a TeamAro relationship.

        Args:
            team_aro_id: The ID of the TeamAro relationship.
            new_status: The new status to set.

        Returns:
            True if the status was updated, False otherwise.
        """
        pass

    @abstractmethod
    def remove(self, team_aro_id: int) -> bool:
        """
        Remove a TeamAro relationship by its ID.

        Args:
            team_aro_id: The ID of the TeamAro relationship to remove.

        Returns:
            True if the relationship was removed, False otherwise.
        """
        pass