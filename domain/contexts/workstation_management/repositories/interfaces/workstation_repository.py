from abc import abstractmethod
from typing import List, Optional

from domain.contexts.workstation_management.entities.workstation import Workstation
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
                skip: int = 0, limit: int = 100) -> List[Workstation]:
        """
        Get all workstations with filtering and pagination.

        Args:
            team_id: Filter by team ID
            is_active: Filter by active status
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

    @abstractmethod
    def get_by_line_type(self, line_type: str) -> List[Workstation]:
        """
        Retrieve all workstations for a specific line type.

        Args:
            line_type: The line type to filter by.

        Returns:
            A list of workstations with the specified line type.
        """
        pass

    @abstractmethod
    def get_by_capacity_range(self, min_capacity: int, max_capacity: int) -> List[Workstation]:
        """
        Retrieve workstations within a capacity range.

        Args:
            min_capacity: Minimum capacity requirement
            max_capacity: Maximum capacity requirement

        Returns:
            A list of workstations within the capacity range.
        """
        pass

    @abstractmethod
    def get_heavy_job_workstations(self) -> List[Workstation]:
        """
        Retrieve all workstations that are designated as heavy job stations.

        Returns:
            A list of heavy job workstations.
        """
        pass

    @abstractmethod
    def get_key_skill_workstations(self) -> List[Workstation]:
        """
        Retrieve all workstations that require key skills.

        Returns:
            A list of key skill workstations.
        """
        pass