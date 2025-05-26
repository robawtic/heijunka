# tests/domain/services/test_regression_test_service.py
import unittest
from unittest.mock import MagicMock, patch
from datetime import date

from domain.services.regression_test_service import RegressionTestService, RegressionTestResult
from domain.value_objects.regression_test_scenario import RegressionTestScenario
from domain.value_objects.work_assignment import WorkAssignment
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.value_objects.work_period import WorkPeriod

class TestRegressionTestService(unittest.TestCase):
    """Test cases for the RegressionTestService."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock repositories
        self.employee_repository = MagicMock()
        self.workstation_repository = MagicMock()
        self.team_repository = MagicMock()
        self.schedule_repository = MagicMock()
        self.schedule_service = MagicMock()
        self.session = MagicMock()
        
        # Create service
        self.service = RegressionTestService(
            employee_repository=self.employee_repository,
            workstation_repository=self.workstation_repository,
            team_repository=self.team_repository,
            schedule_service=self.schedule_service,
            schedule_repository=self.schedule_repository,
            session=self.session
        )
        
        # Create test data
        self.test_date = date(2024, 8, 19)
        self.team_id = 1
        self.team_name = "Test Team"
        
        # Mock team
        self.team = MagicMock()
        self.team.id = self.team_id
        self.team.name = self.team_name
        self.team_repository.get_by_name.return_value = self.team
        
        # Create test scenario
        self.scenario = RegressionTestScenario(
            name="Test Scenario",
            team_id=self.team_id,
            start_date=self.test_date,
            periods_per_day=4,
            expected_metrics={
                "total_assignments": 10,
                "min_employee_assignments": 2,
                "max_employee_assignments": 3,
                "avg_employee_assignments": 2.5
            },
            tolerance_thresholds={
                "total_assignments": 0,
                "min_employee_assignments": 0,
                "max_employee_assignments": 0,
                "avg_employee_assignments": 0.1
            }
        )
    
    def test_run_regression_tests_all_pass(self):
        """Test running regression tests where all tests pass."""
        # Create mock employees and workstations
        employee1 = Employee(id=1, name="Employee 1", team_id=self.team_id)
        employee2 = Employee(id=2, name="Employee 2", team_id=self.team_id)
        workstation1 = Workstation(id=1, name="Workstation 1", team_id=self.team_id)
        workstation2 = Workstation(id=2, name="Workstation 2", team_id=self.team_id)
        
        # Create mock assignments
        assignments = [
            WorkAssignment(
                employee=employee1,
                workstation=workstation1,
                period=WorkPeriod(date=self.test_date, period=1)
            ),
            WorkAssignment(
                employee=employee1,
                workstation=workstation2,
                period=WorkPeriod(date=self.test_date, period=2)
            ),
            WorkAssignment(
                employee=employee2,
                workstation=workstation1,
                period=WorkPeriod(date=self.test_date, period=3)
            ),
            WorkAssignment(
                employee=employee2,
                workstation=workstation2,
                period=WorkPeriod(date=self.test_date, period=4)
            )
        ]
        
        # Mock simulator run_scenario method
        self.service.simulator.run_scenario = MagicMock()
        self.service.simulator.run_scenario.return_value = {
            'scenario': self.scenario,
            'assignments': assignments,
            'metrics': {
                'total_assignments': 4,
                'min_employee_assignments': 2,
                'max_employee_assignments': 2,
                'avg_employee_assignments': 2.0,
                'assignments_per_employee': {
                    'Employee 1': 2,
                    'Employee 2': 2
                },
                'assignments_per_workstation': {
                    'Workstation 1': 2,
                    'Workstation 2': 2
                }
            }
        }
        
        # Update expected metrics to match mock results
        self.scenario.expected_metrics = {
            'total_assignments': 4,
            'min_employee_assignments': 2,
            'max_employee_assignments': 2,
            'avg_employee_assignments': 2.0
        }
        
        # Run regression tests
        results = self.service.run_regression_tests([self.scenario])
        
        # Verify results
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].passed)
        self.assertEqual(results[0].scenario_name, "Test Scenario")
        
        # Verify metrics results
        for metric in self.scenario.expected_metrics:
            expected = self.scenario.expected_metrics[metric]
            actual = results[0].metrics_results[metric][1]  # actual value
            passed = results[0].metrics_results[metric][2]  # passed flag
            self.assertEqual(expected, actual)
            self.assertTrue(passed)
    
    def test_run_regression_tests_with_failures(self):
        """Test running regression tests where some tests fail."""
        # Create mock employees and workstations
        employee1 = Employee(id=1, name="Employee 1", team_id=self.team_id)
        employee2 = Employee(id=2, name="Employee 2", team_id=self.team_id)
        workstation1 = Workstation(id=1, name="Workstation 1", team_id=self.team_id)
        workstation2 = Workstation(id=2, name="Workstation 2", team_id=self.team_id)
        
        # Create mock assignments
        assignments = [
            WorkAssignment(
                employee=employee1,
                workstation=workstation1,
                period=WorkPeriod(date=self.test_date, period=1)
            ),
            WorkAssignment(
                employee=employee1,
                workstation=workstation2,
                period=WorkPeriod(date=self.test_date, period=2)
            ),
            WorkAssignment(
                employee=employee2,
                workstation=workstation1,
                period=WorkPeriod(date=self.test_date, period=3)
            ),
            WorkAssignment(
                employee=employee2,
                workstation=workstation2,
                period=WorkPeriod(date=self.test_date, period=4)
            ),
            WorkAssignment(
                employee=employee1,
                workstation=workstation1,
                period=WorkPeriod(date=self.test_date, period=5)
            )
        ]
        
        # Mock simulator run_scenario method
        self.service.simulator.run_scenario = MagicMock()
        self.service.simulator.run_scenario.return_value = {
            'scenario': self.scenario,
            'assignments': assignments,
            'metrics': {
                'total_assignments': 5,  # Different from expected
                'min_employee_assignments': 2,
                'max_employee_assignments': 3,  # Different from expected
                'avg_employee_assignments': 2.5,
                'assignments_per_employee': {
                    'Employee 1': 3,
                    'Employee 2': 2
                },
                'assignments_per_workstation': {
                    'Workstation 1': 3,
                    'Workstation 2': 2
                }
            }
        }
        
        # Set expected metrics that will cause failures
        self.scenario.expected_metrics = {
            'total_assignments': 4,  # Expected 4, actual 5
            'min_employee_assignments': 2,
            'max_employee_assignments': 2,  # Expected 2, actual 3
            'avg_employee_assignments': 2.5
        }
        
        # Run regression tests
        results = self.service.run_regression_tests([self.scenario])
        
        # Verify results
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].passed)
        self.assertEqual(results[0].scenario_name, "Test Scenario")
        
        # Verify failed metrics
        failed_metrics = results[0].get_failed_metrics()
        self.assertIn('total_assignments', failed_metrics)
        self.assertIn('max_employee_assignments', failed_metrics)
        self.assertEqual(failed_metrics['total_assignments'], (4, 5))
        self.assertEqual(failed_metrics['max_employee_assignments'], (2, 3))
    
    def test_run_regression_tests_with_error(self):
        """Test running regression tests where an error occurs."""
        # Mock simulator run_scenario method to raise an exception
        self.service.simulator.run_scenario = MagicMock()
        self.service.simulator.run_scenario.side_effect = ValueError("Test error")
        
        # Run regression tests
        results = self.service.run_regression_tests([self.scenario])
        
        # Verify results
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].passed)
        self.assertEqual(results[0].scenario_name, "Test Scenario")
        self.assertEqual(results[0].error_message, "Test error")
    
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data='[{"name": "Test Scenario"}]')
    @patch('json.load')
    def test_load_regression_tests_from_file(self, mock_json_load, mock_open):
        """Test loading regression tests from a file."""
        # Mock json.load to return test data
        mock_json_load.return_value = [
            {
                "name": "Test Scenario",
                "call_ins": [],
                "offline": [],
                "force_complete": False,
                "periods_per_day": 4,
                "expected_metrics": {
                    "total_assignments": 10
                },
                "tolerance_thresholds": {
                    "total_assignments": 0
                }
            }
        ]
        
        # Load regression tests
        scenarios = self.service.load_regression_tests_from_file("test_file.json", self.team_name, self.test_date)
        
        # Verify scenarios
        self.assertEqual(len(scenarios), 1)
        self.assertEqual(scenarios[0].name, "Test Scenario")
        self.assertEqual(scenarios[0].team_id, self.team_id)
        self.assertEqual(scenarios[0].start_date, self.test_date)
        self.assertEqual(scenarios[0].periods_per_day, 4)
        self.assertEqual(scenarios[0].expected_metrics, {"total_assignments": 10})
        self.assertEqual(scenarios[0].tolerance_thresholds, {"total_assignments": 0})

if __name__ == '__main__':
    unittest.main()