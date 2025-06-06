# domain/services/team_lookup_service.py
from typing import Optional, Dict
import logging

# Logger for this module
logger = logging.getLogger(__name__)

class TeamLookupService:
    def __init__(self, team_repository=None):
        self.team_repository = team_repository
    
    def get_team_id(self, team_name: str, prefetched_data: Optional[Dict] = None) -> int:
        """
        Resolve team ID by team name only.
        First checks prefetched data if available, then falls back to repository.
        Raises ValueError if not found.

        Args:
            team_name: Name of the team to look up
            prefetched_data: Optional dictionary containing prefetched data

        Returns:
            The team ID

        Raises:
            ValueError: If team not found or repository not provided
        """
        # First check if we have the team in prefetched data
        if prefetched_data and 'teams_by_name' in prefetched_data and team_name in prefetched_data['teams_by_name']:
            team = prefetched_data['teams_by_name'][team_name]
            if team and hasattr(team, 'id'):
                logger.debug(f"Found team_id={team.id} for team '{team_name}' via prefetched data")
                return team.id

        # Fall back to repository lookup
        if not self.team_repository:
            raise ValueError("team_repository is required to look up team_id by team name when not in prefetched data.")

        team = self.team_repository.get_by_name(team_name)
        if team and hasattr(team, 'id'):
            logger.debug(f"Found team_id={team.id} for team '{team_name}' via repository")
            return team.id

        error_msg = f"Could not resolve team_id for team '{team_name}'. No matching team found in prefetched data or repository."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    def get_team_name(self, team_id: int, prefetched_data: Optional[Dict] = None) -> str:
        """
        Resolve team name from team ID.
        First checks prefetched data if available, then falls back to repository.
        Raises ValueError if not found.

        Args:
            team_id: ID of the team to look up
            prefetched_data: Optional dictionary containing prefetched data

        Returns:
            The team name

        Raises:
            ValueError: If team not found or repository not provided
        """
        # First check if we have the team in prefetched data
        if prefetched_data and 'teams_by_id' in prefetched_data and team_id in prefetched_data['teams_by_id']:
            team = prefetched_data['teams_by_id'][team_id]
            if team and hasattr(team, 'name'):
                logger.debug(f"Found team name='{team.name}' for team_id={team_id} via prefetched data")
                return team.name

        # Fall back to repository lookup
        if not self.team_repository:
            raise ValueError("team_repository is required to look up team name by team_id when not in prefetched data.")

        team = self.team_repository.get(team_id)
        if team and hasattr(team, 'name'):
            logger.debug(f"Found team name='{team.name}' for team_id={team_id} via repository")
            return team.name

        error_msg = f"Could not resolve team name for team_id={team_id}. No matching team found in prefetched data or repository."
        logger.error(error_msg)
        raise ValueError(error_msg)