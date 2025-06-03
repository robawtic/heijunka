import unittest
from unittest.mock import MagicMock, patch
from datetime import date

from domain.services.cache_invalidation_handler import CacheInvalidationHandler
from domain.contexts.assignment.services.aro_graph_service import AROGraphService
from domain.events import (
    AROAssignmentCreated, AROAssignmentRemoved, AROAssignmentUpdated,
    TeamMemberAdded, TeamMemberRemoved,
    WorkstationAddedToTeam, WorkstationRemovedFromTeam,
    QualificationAdded, QualificationRemoved
)

class TestCacheInvalidationHandler(unittest.TestCase):
    def setUp(self):
        # Create a mock ARO graph service
        self.aro_graph_service = MagicMock(spec=AROGraphService)
        self.aro_graph_service._graph_cache = {}
        self.aro_graph_service._edge_cost_cache = {}

        # Create the handler
        self.handler = CacheInvalidationHandler(self.aro_graph_service)

        # Test data
        self.test_date = date(2024, 6, 1)
        self.test_period = 3

        # Populate the caches with some test data
        self.aro_graph_service._graph_cache[(self.test_date, self.test_period)] = {"test": "data"}
        self.aro_graph_service._graph_cache[(self.test_date, None)] = {"test": "data2"}
        self.aro_graph_service._edge_cost_cache[(1, 2, (5,))] = 1.0
        self.aro_graph_service._edge_cost_cache[(2, 3, (6,))] = 2.0
        self.aro_graph_service._edge_cost_cache[(3, 1, (7,))] = 3.0

    def test_handle_aro_assignment_created(self):
        # Create an event
        event = AROAssignmentCreated(
            employee_id=1,
            from_team_id=1,
            to_team_id=2,
            assignment_date=self.test_date,
            period=self.test_period
        )

        # Call the handler
        with patch('domain.services.cache_invalidation_handler.logger') as mock_logger:
            self.handler.handle_aro_assignment_created(event)

            # Verify that the graph cache for the date/period was invalidated
            self.assertNotIn((self.test_date, self.test_period), self.aro_graph_service._graph_cache)

            # Verify that the edge cost cache for the teams was invalidated
            self.assertNotIn((1, 2, (5,)), self.aro_graph_service._edge_cost_cache)

            # Verify that other caches were not invalidated
            self.assertIn((self.test_date, None), self.aro_graph_service._graph_cache)
            self.assertIn((2, 3, (6,)), self.aro_graph_service._edge_cost_cache)
            self.assertIn((3, 1, (7,)), self.aro_graph_service._edge_cost_cache)

            # Verify that the logger was called
            mock_logger.info.assert_called_once()

    def test_handle_aro_assignment_removed(self):
        # Create an event
        event = AROAssignmentRemoved(
            employee_id=1,
            from_team_id=1,
            to_team_id=2,
            assignment_date=self.test_date,
            period=self.test_period
        )

        # Call the handler
        with patch('domain.services.cache_invalidation_handler.logger') as mock_logger:
            self.handler.handle_aro_assignment_removed(event)

            # Verify that the graph cache for the date/period was invalidated
            self.assertNotIn((self.test_date, self.test_period), self.aro_graph_service._graph_cache)

            # Verify that the edge cost cache for the teams was invalidated
            self.assertNotIn((1, 2, (5,)), self.aro_graph_service._edge_cost_cache)

            # Verify that other caches were not invalidated
            self.assertIn((self.test_date, None), self.aro_graph_service._graph_cache)
            self.assertIn((2, 3, (6,)), self.aro_graph_service._edge_cost_cache)
            self.assertIn((3, 1, (7,)), self.aro_graph_service._edge_cost_cache)

            # Verify that the logger was called
            mock_logger.info.assert_called_once()

    def test_handle_aro_assignment_updated(self):
        # Create an event
        event = AROAssignmentUpdated(
            employee_id=1,
            from_team_id=1,
            to_team_id=2,
            assignment_date=self.test_date,
            period=self.test_period
        )

        # Call the handler
        with patch('domain.services.cache_invalidation_handler.logger') as mock_logger:
            self.handler.handle_aro_assignment_updated(event)

            # Verify that the graph cache for the date/period was invalidated
            self.assertNotIn((self.test_date, self.test_period), self.aro_graph_service._graph_cache)

            # Verify that the edge cost cache for the teams was invalidated
            self.assertNotIn((1, 2, (5,)), self.aro_graph_service._edge_cost_cache)

            # Verify that other caches were not invalidated
            self.assertIn((self.test_date, None), self.aro_graph_service._graph_cache)
            self.assertIn((2, 3, (6,)), self.aro_graph_service._edge_cost_cache)
            self.assertIn((3, 1, (7,)), self.aro_graph_service._edge_cost_cache)

            # Verify that the logger was called
            mock_logger.info.assert_called_once()

    def test_handle_team_member_added(self):
        # Create an event
        event = TeamMemberAdded(
            team_id=2,
            employee_id=1,
            roles=[]
        )

        # Call the handler
        with patch('domain.services.cache_invalidation_handler.logger') as mock_logger:
            self.handler.handle_team_member_added(event)

            # Verify that all graph caches were invalidated
            self.assertEqual(len(self.aro_graph_service._graph_cache), 0)

            # Verify that the edge cost cache for the team was invalidated
            self.assertNotIn((1, 2, (5,)), self.aro_graph_service._edge_cost_cache)
            self.assertNotIn((2, 3, (6,)), self.aro_graph_service._edge_cost_cache)

            # Verify that other edge cost caches were not invalidated
            self.assertIn((3, 1, (7,)), self.aro_graph_service._edge_cost_cache)

            # Verify that the logger was called
            mock_logger.info.assert_called_once()

    def test_handle_qualification_added(self):
        # Create an event
        event = QualificationAdded(
            employee_id=1,
            qualification="H010"
        )

        # Call the handler
        with patch('domain.services.cache_invalidation_handler.logger') as mock_logger:
            self.handler.handle_qualification_added(event)

            # Verify that all caches were invalidated
            self.assertEqual(len(self.aro_graph_service._graph_cache), 0)
            self.assertEqual(len(self.aro_graph_service._edge_cost_cache), 0)

            # Verify that the logger was called
            mock_logger.info.assert_called_once()

if __name__ == '__main__':
    unittest.main()
