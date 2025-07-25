import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch, call
import time
from sqlalchemy.exc import OperationalError

from domain.contexts.employee_management.entities.employee import Employee
from domain.contexts.employee_management.entities.team import Team
from domain.contexts.workstation_management.entities.workstation import Workstation
from domain.contexts.assignment.services.aro_graph_service import AROGraphService
from domain.services.aro_service import AROService
from domain.contexts.assignment.aro_assignment import AROAssignment

class TestAROGraphService(unittest.TestCase):
    def setUp(self):
        # Create mock repositories and services
        self.aro_repository = MagicMock()
        self.employee_repository = MagicMock()
        self.team_repository = MagicMock()
        self.workstation_repository = MagicMock()
        self.aro_service = MagicMock(spec=AROService)

        # Create the service
        from domain.events.publisher import DomainEventPublisher
        self.event_publisher = MagicMock(spec=DomainEventPublisher)
        self.aro_graph_service = AROGraphService(
            aro_service=self.aro_service,
            aro_repository=self.aro_repository,
            employee_repository=self.employee_repository,
            team_repository=self.team_repository,
            workstation_repository=self.workstation_repository,
            event_publisher=self.event_publisher
        )

        # Create test data
        self.team_a = Team(id=1, name="Team A")
        self.team_b = Team(id=2, name="Team B")
        self.team_c = Team(id=3, name="Team C")

        self.employee_a1 = Employee(id=1, name="Employee A1", team_id=1, is_active=True)
        self.employee_a2 = Employee(id=2, name="Employee A2", team_id=1, is_active=True)
        self.employee_b1 = Employee(id=3, name="Employee B1", team_id=2, is_active=True)
        self.employee_b2 = Employee(id=4, name="Employee B2", team_id=2, is_active=True)
        self.employee_c1 = Employee(id=5, name="Employee C1", team_id=3, is_active=True)
        self.employee_c2 = Employee(id=6, name="Employee C2", team_id=3, is_active=True)

        # Add qualifications to employees
        self.employee_a1.add_qualification("H010")
        self.employee_a2.add_qualification("H080")
        self.employee_b1.add_qualification("H010")
        self.employee_b1.add_qualification("H080")
        self.employee_b2.add_qualification("BW010")
        self.employee_c1.add_qualification("H010")
        self.employee_c2.add_qualification("BW010")

        # Create workstations
        self.ws_a1 = Workstation(id=1, name="H010", line_type="headsub", team_id=1)
        self.ws_a2 = Workstation(id=2, name="H080", line_type="headsub", team_id=1)
        self.ws_b1 = Workstation(id=3, name="H010", line_type="headsub", team_id=2)
        self.ws_b2 = Workstation(id=4, name="BW010", line_type="bodywork", team_id=2)
        self.ws_c1 = Workstation(id=5, name="H010", line_type="headsub", team_id=3)

        # Set up repository returns
        self.team_repository.list_all.return_value = [self.team_a, self.team_b, self.team_c]

        self.team_repository.get.side_effect = lambda id: {
            1: self.team_a,
            2: self.team_b,
            3: self.team_c
        }.get(id)

        self.employee_repository.get_by_team_id.side_effect = lambda id: {
            1: [self.employee_a1, self.employee_a2],
            2: [self.employee_b1, self.employee_b2],
            3: [self.employee_c1, self.employee_c2]
        }.get(id, [])

        self.workstation_repository.get_by_team_id.side_effect = lambda id: {
            1: [self.ws_a1, self.ws_a2],
            2: [self.ws_b1, self.ws_b2],
            3: [self.ws_c1]
        }.get(id, [])

        # Test date
        self.test_date = date(2024, 6, 1)

    def test_build_aro_transfer_graph(self):
        # Mock is_available_for_period to return True for all employees
        with patch.object(Employee, 'is_available_for_period', return_value=True):
            # Call the method
            graph = self.aro_graph_service.build_aro_transfer_graph(self.test_date)

            # Check the graph structure
            self.assertIn(1, graph)  # Team A
            self.assertIn(2, graph)  # Team B
            self.assertIn(3, graph)  # Team C

            # Team C should have an edge to Team A (C has 2 employees, 1 workstation)
            team_c_edges = graph[3]
            self.assertTrue(any(edge['team_id'] == 1 for edge in team_c_edges))

            # Team C should have an edge to Team B
            self.assertTrue(any(edge['team_id'] == 2 for edge in team_c_edges))

            # Team A should not have edges (2 employees, 2 workstations)
            self.assertEqual(len(graph[1]), 0)

            # Team B should not have edges (2 employees, 2 workstations)
            self.assertEqual(len(graph[2]), 0)

    def test_find_optimal_aro_paths(self):
        # Mock build_aro_transfer_graph to return a predefined graph
        mock_graph = {
            1: [],  # Team A has no extra employees
            2: [],  # Team B has no extra employees
            3: [    # Team C has extra employees
                {
                    'team_id': 1,
                    'capacity': 1,
                    'cost': 1.0,
                    'employees': [5]  # Employee C1 can work at Team A
                },
                {
                    'team_id': 2,
                    'capacity': 1,
                    'cost': 1.2,
                    'employees': [6]  # Employee C2 can work at Team B
                }
            ]
        }

        with patch.object(self.aro_graph_service, 'build_aro_transfer_graph', return_value=mock_graph):
            # Find paths to Team A
            paths = self.aro_graph_service.find_optimal_aro_paths(1, self.test_date)

            # Should find one path from Team C to Team A
            self.assertEqual(len(paths), 1)
            self.assertEqual(paths[0]['path'][0]['from_team_id'], 3)
            self.assertEqual(paths[0]['path'][0]['to_team_id'], 1)

            # Find paths to Team B
            paths = self.aro_graph_service.find_optimal_aro_paths(2, self.test_date)

            # Should find one path from Team C to Team B
            self.assertEqual(len(paths), 1)
            self.assertEqual(paths[0]['path'][0]['from_team_id'], 3)
            self.assertEqual(paths[0]['path'][0]['to_team_id'], 2)

    def test_assign_optimal_aros(self):
        # Mock find_optimal_aro_paths to return a predefined path
        mock_paths = [
            {
                'path': [
                    {
                        'from_team_id': 3,
                        'to_team_id': 1,
                        'capacity': 1,
                        'cost': 1.0,
                        'employees': [5]  # Employee C1
                    }
                ],
                'total_cost': 1.0,
                'capacity': 1
            }
        ]

        # Mock aro_service.assign_aro to return success
        self.aro_service.assign_aro.return_value = {'status': 'success', 'message': 'Employee assigned as ARO'}

        # Mock aro_service.find_aro_assignment to return a mock assignment
        mock_assignment = AROAssignment(
            id=1,
            employee_id=5,
            from_team_id=3,
            to_team_id=1,
            assignment_date=self.test_date
        )
        self.aro_service.find_aro_assignment.return_value = mock_assignment

        with patch.object(self.aro_graph_service, 'find_optimal_aro_paths', return_value=mock_paths):
            # Assign AROs to Team A
            assignments = self.aro_graph_service.assign_optimal_aros(1, 1, self.test_date)

            # Should create one assignment
            self.assertEqual(len(assignments), 1)
            self.assertEqual(assignments[0].employee_id, 5)
            self.assertEqual(assignments[0].from_team_id, 3)
            self.assertEqual(assignments[0].to_team_id, 1)

            # Verify aro_service.assign_aro was called
            self.aro_service.assign_aro.assert_called_once_with(
                employee_id=5,
                to_team_id=1,
                assignment_date=self.test_date,
                period=None
            )

    def test_multi_hop_path(self):
        # Mock build_aro_transfer_graph to return a graph with a multi-hop path
        mock_graph = {
            1: [],  # Team A has no extra employees
            2: [    # Team B has extra employees that can go to Team A
                {
                    'team_id': 1,
                    'capacity': 1,
                    'cost': 1.0,
                    'employees': [3]  # Employee B1 can work at Team A
                }
            ],
            3: [    # Team C has extra employees that can go to Team B
                {
                    'team_id': 2,
                    'capacity': 1,
                    'cost': 1.0,
                    'employees': [5]  # Employee C1 can work at Team B
                }
            ]
        }

        # Mock aro_service methods
        self.aro_service.assign_aro.return_value = {'status': 'success', 'message': 'Employee assigned as ARO'}

        # Mock find_aro_assignment to return appropriate assignments
        def mock_find_aro_assignment(employee_id, assignment_date, period):
            if employee_id == 5:  # First hop: C1 -> B
                return AROAssignment(
                    id=1,
                    employee_id=5,
                    from_team_id=3,
                    to_team_id=2,
                    assignment_date=assignment_date,
                    period=period
                )
            elif employee_id == 3:  # Second hop: B1 -> A
                return AROAssignment(
                    id=2,
                    employee_id=3,
                    from_team_id=2,
                    to_team_id=1,
                    assignment_date=assignment_date,
                    period=period
                )
            return None

        self.aro_service.find_aro_assignment.side_effect = mock_find_aro_assignment

        # Mock _find_shortest_paths to return a multi-hop path
        mock_paths = [
            {
                'path': [
                    {
                        'from_team_id': 3,
                        'to_team_id': 2,
                        'capacity': 1,
                        'cost': 1.0,
                        'employees': [5]  # Employee C1
                    },
                    {
                        'from_team_id': 2,
                        'to_team_id': 1,
                        'capacity': 1,
                        'cost': 1.0,
                        'employees': [3]  # Employee B1
                    }
                ],
                'total_cost': 2.0,
                'capacity': 1
            }
        ]

        with patch.object(self.aro_graph_service, 'build_aro_transfer_graph', return_value=mock_graph), \
             patch.object(self.aro_graph_service, 'find_optimal_aro_paths', return_value=mock_paths):

            # Assign AROs to Team A
            assignments = self.aro_graph_service.assign_optimal_aros(1, 1, self.test_date)

            # Should create one assignment (the final hop to Team A)
            self.assertEqual(len(assignments), 1)

            # Verify aro_service.assign_aro was called twice (once for each hop)
            self.assertEqual(self.aro_service.assign_aro.call_count, 2)

            # First call should be for Employee C1 to Team B
            first_call_args = self.aro_service.assign_aro.call_args_list[0][1]
            self.assertEqual(first_call_args['employee_id'], 5)
            self.assertEqual(first_call_args['to_team_id'], 2)

            # Second call should be for an employee from Team B to Team A
            # (we can't assert the exact employee ID because it depends on what employee_repository.get_by_team_id returns)
            second_call_args = self.aro_service.assign_aro.call_args_list[1][1]
            self.assertEqual(second_call_args['to_team_id'], 1)

    def test_caching(self):
        """Test that caching works for edge costs and transfer graphs."""
        # Mock is_available_for_period to return True for all employees
        with patch.object(Employee, 'is_available_for_period', return_value=True):
            # Call the method twice with the same parameters
            graph1 = self.aro_graph_service.build_aro_transfer_graph(self.test_date)
            graph2 = self.aro_graph_service.build_aro_transfer_graph(self.test_date)

            # The second call should return the cached result
            self.assertEqual(id(graph1), id(graph2))

            # Clear the cache
            self.aro_graph_service.clear_caches()

            # Call the method again
            graph3 = self.aro_graph_service.build_aro_transfer_graph(self.test_date)

            # The result should be different from the cached result
            self.assertNotEqual(id(graph1), id(graph3))

    def test_k_shortest_paths(self):
        """Test that Yen's k-shortest paths algorithm works."""
        # Create a more complex graph with multiple paths
        mock_graph = {
            1: [],  # Team A has no extra employees
            2: [    # Team B has extra employees that can go to Team A
                {
                    'team_id': 1,
                    'capacity': 1,
                    'cost': 1.0,
                    'employees': [3]  # Employee B1 can work at Team A
                }
            ],
            3: [    # Team C has extra employees that can go to Team A and Team B
                {
                    'team_id': 1,
                    'capacity': 1,
                    'cost': 2.0,  # Higher cost path directly to A
                    'employees': [5]  # Employee C1 can work at Team A
                },
                {
                    'team_id': 2,
                    'capacity': 1,
                    'cost': 1.0,  # Lower cost path to B
                    'employees': [5]  # Employee C1 can work at Team B
                }
            ]
        }

        # Mock _find_shortest_paths to return paths based on the mock graph
        def mock_find_shortest_paths(graph, source, target, max_hops):
            if source == 3 and target == 1:
                # Direct path from C to A
                return [{
                    'path': [
                        {
                            'from_team_id': 3,
                            'to_team_id': 1,
                            'capacity': 1,
                            'cost': 2.0,
                            'employees': [5]
                        }
                    ],
                    'total_cost': 2.0,
                    'capacity': 1
                }]
            elif source == 3 and target == 2:
                # Path from C to B
                return [{
                    'path': [
                        {
                            'from_team_id': 3,
                            'to_team_id': 2,
                            'capacity': 1,
                            'cost': 1.0,
                            'employees': [5]
                        }
                    ],
                    'total_cost': 1.0,
                    'capacity': 1
                }]
            elif source == 2 and target == 1:
                # Path from B to A
                return [{
                    'path': [
                        {
                            'from_team_id': 2,
                            'to_team_id': 1,
                            'capacity': 1,
                            'cost': 1.0,
                            'employees': [3]
                        }
                    ],
                    'total_cost': 1.0,
                    'capacity': 1
                }]
            return []

        with patch.object(self.aro_graph_service, 'build_aro_transfer_graph', return_value=mock_graph), \
             patch.object(self.aro_graph_service, '_find_shortest_paths', side_effect=mock_find_shortest_paths):

            # Find paths from Team C to Team A with k=2
            paths = self.aro_graph_service.find_k_shortest_paths(mock_graph, 3, 1, max_hops=2, k=2)

            # Should find two paths: direct C->A and indirect C->B->A
            self.assertEqual(len(paths), 2)

            # First path should be direct C->A
            self.assertEqual(len(paths[0]['path']), 1)
            self.assertEqual(paths[0]['path'][0]['from_team_id'], 3)
            self.assertEqual(paths[0]['path'][0]['to_team_id'], 1)

            # Second path should be indirect C->B->A
            # Note: This test might fail if the implementation of Yen's algorithm is different
            # from what we expect. The important thing is that it finds multiple paths.
            if len(paths) > 1:
                self.assertEqual(paths[1]['total_cost'], 2.0)  # 1.0 + 1.0

    def test_enhanced_edge_cost(self):
        """Test that enhanced edge cost calculation works."""
        # Mock repository methods
        self.aro_repository.get_by_employee_id.return_value = [
            AROAssignment(
                id=1,
                employee_id=5,
                from_team_id=3,
                to_team_id=1,
                assignment_date=date.today() - timedelta(days=10)
            )
        ]

        # Call the method
        cost = self.aro_graph_service._calculate_edge_cost(self.team_c, self.team_a, [5])

        # Cost should be affected by familiarity and fairness
        self.assertGreater(cost, 0.1)  # Ensure cost is positive

        # Test with different parameters
        cost2 = self.aro_graph_service._calculate_edge_cost(self.team_c, self.team_b, [6])

        # Cost should be different
        self.assertNotEqual(cost, cost2)

    def test_transaction_retry(self):
        """Test that transaction retry logic works for deadlocks."""
        # Mock session methods
        self.aro_graph_service._session = MagicMock()
        self.aro_graph_service._session.commit.side_effect = [
            OperationalError("deadlock detected", None, None),  # First attempt fails
            None  # Second attempt succeeds
        ]

        # Mock time.sleep to avoid waiting
        with patch('time.sleep'):
            # Use the transaction context manager
            with self.aro_graph_service._transaction():
                pass  # Do nothing inside the transaction

            # Verify that commit was called twice
            self.assertEqual(self.aro_graph_service._session.commit.call_count, 2)

            # Verify that rollback was called once
            self.aro_graph_service._session.rollback.assert_called_once()

    def test_transaction_max_retries(self):
        """Test that transaction retry logic gives up after max retries."""
        # Mock session methods
        self.aro_graph_service._session = MagicMock()
        self.aro_graph_service._session.commit.side_effect = OperationalError("deadlock detected", None, None)

        # Mock time.sleep to avoid waiting
        with patch('time.sleep'):
            # Use the transaction context manager with max_retries=2
            with self.assertRaises(ValueError):
                with self.aro_graph_service._transaction(max_retries=2):
                    pass  # Do nothing inside the transaction

            # Verify that commit was called 3 times (initial + 2 retries)
            self.assertEqual(self.aro_graph_service._session.commit.call_count, 3)

            # Verify that rollback was called 3 times
            self.assertEqual(self.aro_graph_service._session.rollback.call_count, 3)

if __name__ == '__main__':
    unittest.main()
