import logging
from typing import Dict, Any, Optional
from datetime import date
from utilities.secure_logging import redact_log_message

from domain.events import (
    AROAssignmentCreated, AROAssignmentRemoved, AROAssignmentUpdated,
    TeamMemberAdded, TeamMemberRemoved,
    WorkstationAddedToTeam, WorkstationRemovedFromTeam,
    QualificationAdded, QualificationRemoved
)
from domain.contexts.assignment.services.aro_graph_service import AROGraphService

# Configure logging
logger = logging.getLogger("heijunka.cache")

class CacheInvalidationHandler:
    """
    Handler for invalidating caches when domain events occur.

    This handler is responsible for selectively invalidating portions of the cache
    when events occur that might affect the cached data, rather than clearing
    the entire cache.
    """

    def __init__(self, aro_graph_service: AROGraphService):
        """
        Initialize the handler with the necessary services.

        Args:
            aro_graph_service: The ARO graph service whose cache needs to be managed
        """
        self.aro_graph_service = aro_graph_service

    def handle_aro_assignment_created(self, event: AROAssignmentCreated) -> None:
        """
        Handle an ARO assignment created event.

        Args:
            event: The event containing the ARO assignment details
        """
        self._invalidate_graph_cache_for_date(event.assignment_date, event.period)
        self._invalidate_edge_cost_cache_for_teams(event.from_team_id, event.to_team_id)
        logger.info(redact_log_message(
            f"Cache invalidated for ARO assignment created: {event.employee_id} from team {event.from_team_id} to team {event.to_team_id} on {event.assignment_date}",
            employee_ids=[str(event.employee_id)],
            team_ids=[str(event.from_team_id), str(event.to_team_id)],
            dates=[str(event.assignment_date)]
        ))

    def handle_aro_assignment_removed(self, event: AROAssignmentRemoved) -> None:
        """
        Handle an ARO assignment removed event.

        Args:
            event: The event containing the ARO assignment details
        """
        self._invalidate_graph_cache_for_date(event.assignment_date, event.period)
        self._invalidate_edge_cost_cache_for_teams(event.from_team_id, event.to_team_id)
        logger.info(redact_log_message(
            f"Cache invalidated for ARO assignment removed: {event.employee_id} from team {event.from_team_id} to team {event.to_team_id} on {event.assignment_date}",
            employee_ids=[str(event.employee_id)],
            team_ids=[str(event.from_team_id), str(event.to_team_id)],
            dates=[str(event.assignment_date)]
        ))

    def handle_aro_assignment_updated(self, event: AROAssignmentUpdated) -> None:
        """
        Handle an ARO assignment updated event.

        Args:
            event: The event containing the ARO assignment details
        """
        self._invalidate_graph_cache_for_date(event.assignment_date, event.period)
        self._invalidate_edge_cost_cache_for_teams(event.from_team_id, event.to_team_id)
        logger.info(redact_log_message(
            f"Cache invalidated for ARO assignment updated: {event.employee_id} from team {event.from_team_id} to team {event.to_team_id} on {event.assignment_date}",
            employee_ids=[str(event.employee_id)],
            team_ids=[str(event.from_team_id), str(event.to_team_id)],
            dates=[str(event.assignment_date)]
        ))

    def handle_team_member_added(self, event: TeamMemberAdded) -> None:
        """
        Handle a team member added event.

        Args:
            event: The event containing the team member details
        """
        self._invalidate_graph_cache_for_team(event.team_id)
        logger.info(redact_log_message(
            f"Cache invalidated for team member added: {event.employee_id} to team {event.team_id}",
            employee_ids=[str(event.employee_id)],
            team_ids=[str(event.team_id)]
        ))

    def handle_team_member_removed(self, event: TeamMemberRemoved) -> None:
        """
        Handle a team member removed event.

        Args:
            event: The event containing the team member details
        """
        self._invalidate_graph_cache_for_team(event.team_id)
        logger.info(redact_log_message(
            f"Cache invalidated for team member removed: {event.employee_id} from team {event.team_id}",
            employee_ids=[str(event.employee_id)],
            team_ids=[str(event.team_id)]
        ))

    def handle_workstation_added_to_team(self, event: WorkstationAddedToTeam) -> None:
        """
        Handle a workstation added to team event.

        Args:
            event: The event containing the workstation details
        """
        self._invalidate_graph_cache_for_team(event.team_id)
        logger.info(redact_log_message(
            f"Cache invalidated for workstation added: {event.workstation_id} to team {event.team_id}",
            workstation_names=[str(event.workstation_id)],
            team_ids=[str(event.team_id)]
        ))

    def handle_workstation_removed_from_team(self, event: WorkstationRemovedFromTeam) -> None:
        """
        Handle a workstation removed from team event.

        Args:
            event: The event containing the workstation details
        """
        self._invalidate_graph_cache_for_team(event.team_id)
        logger.info(redact_log_message(
            f"Cache invalidated for workstation removed: {event.workstation_id} from team {event.team_id}",
            workstation_names=[str(event.workstation_id)],
            team_ids=[str(event.team_id)]
        ))

    def handle_qualification_added(self, event: QualificationAdded) -> None:
        """
        Handle a qualification added event.

        Args:
            event: The event containing the qualification details
        """
        # Since we don't know which team the employee belongs to, we need to invalidate all graph caches
        self._invalidate_all_graph_caches()
        logger.info(redact_log_message(
            f"All graph caches invalidated for qualification added: {event.qualification} to employee {event.employee_id}",
            employee_ids=[str(event.employee_id)],
            custom_data={"qualification": [event.qualification]}
        ))

    def handle_qualification_removed(self, event: QualificationRemoved) -> None:
        """
        Handle a qualification removed event.

        Args:
            event: The event containing the qualification details
        """
        # Since we don't know which team the employee belongs to, we need to invalidate all graph caches
        self._invalidate_all_graph_caches()
        logger.info(redact_log_message(
            f"All graph caches invalidated for qualification removed: {event.qualification} from employee {event.employee_id}",
            employee_ids=[str(event.employee_id)],
            custom_data={"qualification": [event.qualification]}
        ))

    def _invalidate_graph_cache_for_date(self, assignment_date: date, period: Optional[int] = None) -> None:
        """
        Invalidate the graph cache for a specific date and period.

        Args:
            assignment_date: The date to invalidate
            period: Optional period of the day
        """
        # Create a cache key
        cache_key = (assignment_date, period)

        # Remove the entry from the graph cache
        if cache_key in self.aro_graph_service._graph_cache:
            del self.aro_graph_service._graph_cache[cache_key]
            logger.debug(redact_log_message(
                f"Graph cache invalidated for date {assignment_date}, period {period}",
                dates=[str(assignment_date)]
            ))

    def _invalidate_edge_cost_cache_for_teams(self, from_team_id: int, to_team_id: int) -> None:
        """
        Invalidate the edge cost cache for specific teams.

        Args:
            from_team_id: The ID of the source team
            to_team_id: The ID of the destination team
        """
        # Since edge cost cache keys include employee IDs, which we don't know here,
        # we need to iterate through the cache and remove entries for these teams
        keys_to_remove = []
        for key in self.aro_graph_service._edge_cost_cache.keys():
            if key[0] == from_team_id or key[0] == to_team_id or key[1] == from_team_id or key[1] == to_team_id:
                keys_to_remove.append(key)

        # Remove the entries
        for key in keys_to_remove:
            del self.aro_graph_service._edge_cost_cache[key]
            logger.debug(redact_log_message(
                f"Edge cost cache invalidated for key {key}",
                team_ids=[str(key[0]), str(key[1])]
            ))

    def _invalidate_graph_cache_for_team(self, team_id: int) -> None:
        """
        Invalidate all graph caches that involve a specific team.

        Args:
            team_id: The ID of the team
        """
        # Since we don't know which dates/periods are affected, we need to clear all graph caches
        self.aro_graph_service._graph_cache.clear()
        logger.debug(redact_log_message(
            f"All graph caches invalidated for team {team_id}",
            team_ids=[str(team_id)]
        ))

        # Also clear edge cost caches for this team
        keys_to_remove = []
        for key in self.aro_graph_service._edge_cost_cache.keys():
            if key[0] == team_id or key[1] == team_id:
                keys_to_remove.append(key)

        # Remove the entries
        for key in keys_to_remove:
            del self.aro_graph_service._edge_cost_cache[key]
            logger.debug(redact_log_message(
                f"Edge cost cache invalidated for key {key}",
                team_ids=[str(key[0]), str(key[1])]
            ))

    def _invalidate_all_graph_caches(self) -> None:
        """
        Invalidate all graph and edge cost caches.
        """
        self.aro_graph_service._graph_cache.clear()
        self.aro_graph_service._edge_cost_cache.clear()
        logger.debug(redact_log_message("All graph and edge cost caches invalidated"))
