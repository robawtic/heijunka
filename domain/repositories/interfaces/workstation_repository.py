from abc import abstractmethod
from typing import List, Optional

from domain.entities.workstation import Workstation
from domain.repositories.interfaces.base_repository import BaseRepository


class WorkstationRepositoryInterface(BaseRepository[Workstation]):
    """
    Interface for workstation repository operations.
    """

    @abstractmethod
    def get_by_team_id(self, team_id: int) -> List[Workstation]:
        """
        Retrieve all workstations for a specific team.

        Args:
            team_id: The ID of the team.

        Returns:
            A list of workstations belonging to the team.
        """
        pass

    @abstractmethod
    def get_all(self, team_id: Optional[int] = None, is_active: Optional[bool] = None,
                required_qualification: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Workstation]:
        """
        Get all workstations with filtering and pagination.

        Args:
            team_id: Filter by team ID
            is_active: Filter by active status
            required_qualification: Filter by required qualification
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            A list of workstations that match the filters
        """
        pass

    @abstractmethod
    def get_by_team_ids(self, team_ids: List[int]) -> List[Workstation]:
        """
        Retrieve all workstations for multiple teams in a single query.

        Args:
            team_ids: List of team IDs to fetch workstations for.

        Returns:
            A list of workstations belonging to any of the specified teams.
        """
        pass
