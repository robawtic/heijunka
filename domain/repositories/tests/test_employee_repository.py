import unittest
from datetime import date

from domain.entities.employee import Employee
from domain.repositories.tests.mock_employee_repository import MockEmployeeRepository


class TestEmployeeRepository(unittest.TestCase):
    def setUp(self):
        """Set up a new mock repository for each test."""
        self.repo = MockEmployeeRepository()

        # Add some test employees
        self.employee1 = Employee(
            id=1, 
            name="John Doe", 
            team_id=1,
            _roles=[],
            _qualifications=[],
            _available_periods=[],
            _work_history=[],
            _assigned_workstations=[],
            _team_memberships=[]
        )
        self.employee2 = Employee(
            id=2, 
            name="Jane Smith", 
            team_id=1,
            _roles=[],
            _qualifications=[],
            _available_periods=[],
            _work_history=[],
            _assigned_workstations=[],
            _team_memberships=[]
        )
        self.employee3 = Employee(
            id=3, 
            name="Bob Johnson", 
            team_id=2,
            _roles=[],
            _qualifications=[],
            _available_periods=[],
            _work_history=[],
            _assigned_workstations=[],
            _team_memberships=[]
        )

        self.repo.add(self.employee1)
        self.repo.add(self.employee2)
        self.repo.add(self.employee3)

    def test_get_by_id(self):
        """Test retrieving an employee by ID."""
        employee = self.repo.get_by_id(1)
        self.assertEqual(employee.name, "John Doe")

        # Test non-existent employee
        self.assertIsNone(self.repo.get_by_id(999))

    def test_list_all(self):
        """Test retrieving all employees."""
        employees = self.repo.list_all()
        self.assertEqual(len(employees), 3)

    def test_add(self):
        """Test adding a new employee."""
        new_employee = Employee(
            id=4, 
            name="Alice Brown", 
            team_id=2,
            _roles=[],
            _qualifications=[],
            _available_periods=[],
            _work_history=[],
            _assigned_workstations=[],
            _team_memberships=[]
        )
        self.repo.add(new_employee)

        # Verify the employee was added
        self.assertEqual(len(self.repo.list_all()), 4)
        self.assertEqual(self.repo.get_by_id(4).name, "Alice Brown")

    def test_update(self):
        """Test updating an existing employee."""
        # Update employee1's name
        self.employee1.name = "John Smith"
        self.repo.update(self.employee1)

        # Verify the update
        self.assertEqual(self.repo.get_by_id(1).name, "John Smith")

    def test_delete(self):
        """Test deleting an employee."""
        self.assertTrue(self.repo.delete(1))
        self.assertIsNone(self.repo.get_by_id(1))
        self.assertEqual(len(self.repo.list_all()), 2)

        # Test deleting non-existent employee
        self.assertFalse(self.repo.delete(999))

    def test_get_by_team_id(self):
        """Test retrieving employees by team ID."""
        team1_employees = self.repo.get_by_team_id(1)
        self.assertEqual(len(team1_employees), 2)

        team2_employees = self.repo.get_by_team_id(2)
        self.assertEqual(len(team2_employees), 1)
        self.assertEqual(team2_employees[0].name, "Bob Johnson")

        # Test non-existent team
        self.assertEqual(len(self.repo.get_by_team_id(999)), 0)

    def test_assign_role(self):
        """Test assigning a role to an employee."""
        result = self.repo.assign_role(1, "Manager", 1)
        self.assertEqual(result["status"], "success")

        # Check if the role was added using the roles property
        roles = self.employee1.roles
        self.assertTrue("Manager" in roles)

        # Test assigning the same role again
        result = self.repo.assign_role(1, "Manager", 1)
        self.assertEqual(result["status"], "exists")

        # Test assigning to non-existent employee
        result = self.repo.assign_role(999, "Manager", 1)
        self.assertEqual(result["status"], "error")

    def test_remove_role(self):
        """Test removing a role from an employee."""
        # First assign a role
        self.repo.assign_role(1, "Manager", 1)

        # Then remove it
        result = self.repo.remove_role(1, "Manager", 1)
        self.assertEqual(result["status"], "success")

        # Check if the role was removed using the roles property
        roles = self.employee1.roles
        self.assertFalse("Manager" in roles)

        # Test removing a non-existent role
        result = self.repo.remove_role(1, "NonExistentRole", 1)
        self.assertEqual(result["status"], "error")

        # Test removing from non-existent employee
        result = self.repo.remove_role(999, "Manager", 1)
        self.assertEqual(result["status"], "error")

    def test_work_history(self):
        """Test adding and retrieving work history."""
        # Add work history
        today = date.today()
        self.assertTrue(self.repo.add_work_history(1, 101, today, 1))
        self.assertTrue(self.repo.add_work_history(1, 101, today, 2))

        # Get work history
        history = self.repo.get_work_history(1, 101)
        self.assertEqual(len(history), 2)

        # Get last worked date
        last_date, last_period = self.repo.get_last_worked_date(1, 101)
        self.assertEqual(last_date, today)
        self.assertEqual(last_period, 2)  # Should be the latest period

        # Test non-existent history
        last_date, last_period = self.repo.get_last_worked_date(999, 999)
        self.assertIsNone(last_date)
        self.assertIsNone(last_period)


if __name__ == '__main__':
    unittest.main()
