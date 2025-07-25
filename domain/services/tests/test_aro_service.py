import unittest
from datetime import date
from unittest.mock import MagicMock

from domain.contexts.employee_management.entities.employee import Employee
from domain.contexts.employee_management.entities.team import Team
from domain.services.aro_service import AROService
from domain.contexts.assignment.aro_assignment import AROAssignment

class TestAROService(unittest.TestCase):
    def setUp(self):
        # Create mock repositories
        self.aro_repository = MagicMock()
        self.employee_repository = MagicMock()
        self.team_repository = MagicMock()

        # Create the service
        self.aro_service = AROService(
            self.aro_repository,
            self.employee_repository,
            self.team_repository
        )

        # Create test data
        self.team1 = Team(id=1, name="Team1")
        self.team2 = Team(id=2, name="Team2")
        self.employee1 = Employee(id=1, name="Employee1", team_id=1, is_active=True)
        self.employee2 = Employee(id=2, name="Employee2", team_id=1, is_active=True)
        self.employee3 = Employee(id=3, name="Employee3", team_id=2, is_active=True)

        # Set up repository returns
        self.employee_repository.get.side_effect = lambda id: {
            1: self.employee1,
            2: self.employee2,
            3: self.employee3
        }.get(id)

        self.team_repository.get.side_effect = lambda id: {
            1: self.team1,
            2: self.team2
        }.get(id)

        self.employee_repository.get_by_team_id.side_effect = lambda id: {
            1: [self.employee1, self.employee2],
            2: [self.employee3]
        }.get(id, [])

        # Test date
        self.test_date = date(2024, 6, 1)

    def test_assign_aro(self):
        # Set up repository to return no existing assignments
        self.aro_repository.get_by_employee_id.return_value = []

        # Call the service
        result = self.aro_service.assign_aro(1, 2, self.test_date, 3)

        # Check result
        self.assertEqual(result["status"], "success")

        # Verify repository calls
        self.aro_repository.get_by_employee_id.assert_called_once_with(1, self.test_date)
        self.aro_repository.add.assert_called_once()
        self.employee_repository.update.assert_called_once_with(self.employee1)

    def test_assign_aro_already_assigned(self):
        # Set up repository to return existing assignment
        existing_assignment = AROAssignment(
            id=1,
            employee_id=1,
            from_team_id=1,
            to_team_id=2,
            assignment_date=self.test_date,
            period=3
        )
        self.aro_repository.get_by_employee_id.return_value = [existing_assignment]

        # Call the service
        result = self.aro_service.assign_aro(1, 2, self.test_date, 3)

        # Check result
        self.assertEqual(result["status"], "error")

        # Verify repository calls
        self.aro_repository.get_by_employee_id.assert_called_once_with(1, self.test_date)
        self.aro_repository.add.assert_not_called()
        self.employee_repository.update.assert_not_called()

    def test_get_employees_for_team_and_period(self):
        # Set up repository returns
        self.aro_repository.get_employees_leaving.return_value = [2]  # Employee2 is leaving
        self.aro_repository.get_employees_joining.return_value = [3]  # Employee3 is joining

        # Call the service
        employees = self.aro_service.get_employees_for_team_and_period(1, self.test_date, 3)

        # Check result
        self.assertEqual(len(employees), 2)
        self.assertIn(self.employee1, employees)
        self.assertIn(self.employee3, employees)
        self.assertNotIn(self.employee2, employees)

        # Verify repository calls
        self.employee_repository.get_by_team_id.assert_called_once_with(1)
        self.aro_repository.get_employees_leaving.assert_called_once_with(1, self.test_date, 3)
        self.aro_repository.get_employees_joining.assert_called_once_with(1, self.test_date, 3)
