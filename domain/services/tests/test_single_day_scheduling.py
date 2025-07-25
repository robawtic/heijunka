import unittest
from datetime import date
from unittest.mock import MagicMock

from domain.contexts.employee_management.entities.employee import Employee
from domain.contexts.workstation_management.entities.workstation import Workstation
from domain.contexts.employee_management.entities.team import Team
from domain.services.schedule_service import ScheduleService


class TestSingleDayScheduling(unittest.TestCase):
    def setUp(self):
        """Set up the test environment."""
        # Create a schedule service
        self.schedule_service = ScheduleService()

        # Create test data
        self._create_test_data()

    def _create_test_data(self):
        """Create test data for the tests."""
        # Create team
        self.team = Team(id=1, name="headsub", description="Head Sub Team")

        # Create employees
        self.employee1 = Employee(id=1, name="John Doe", team_id=1)
        self.employee2 = Employee(id=2, name="Jane Smith", team_id=1)
        self.employee3 = Employee(id=3, name="Bob Johnson", team_id=1)
        self.employees = [self.employee1, self.employee2, self.employee3]

        # Create workstations
        self.workstation1 = Workstation(id=1, name="Station 1", line_type="Assembly", team_id=1)
        self.workstation2 = Workstation(id=2, name="Station 2", line_type="Assembly", team_id=1)
        self.workstation3 = Workstation(id=3, name="H010", line_type="Assembly", team_id=1)
        self.workstations = [self.workstation1, self.workstation2, self.workstation3]

        # Add qualifications
        self.employee1.add_qualification("Station 1")
        self.employee1.add_qualification("Station 2")
        self.employee1.add_qualification("H010")

        self.employee2.add_qualification("Station 1")
        self.employee2.add_qualification("H010")

        self.employee3.add_qualification("Station 2")
        self.employee3.add_qualification("H010")

    def test_generate_schedule_single_day(self):
        """Test generating a schedule for a single day."""
        # Generate a schedule
        start_date = date.today()
        periods_per_day = 4
        team_name = "headsub"

        # Create a mock session for database access
        mock_session = MagicMock()

        # Create a mock team repository
        mock_team_repository = MagicMock()
        mock_team_repository.get_by_name.return_value = self.team

        # Generate the schedule
        assignments = self.schedule_service.generate_schedule(
            employees=self.employees,
            workstations=self.workstations,
            start_date=start_date,
            periods_per_day=periods_per_day,
            team_name=team_name,
            session=mock_session,
            team_repository=mock_team_repository
        )

        # Verify that assignments were generated
        self.assertIsNotNone(assignments)
        self.assertTrue(len(assignments) > 0)

        # Verify that each assignment has the correct date
        for assignment in assignments:
            self.assertEqual(assignment.period.date, start_date)

        # Verify that each employee is assigned to at most one workstation per period
        for period in range(1, periods_per_day + 1):
            employee_assignments = {}
            for assignment in assignments:
                if assignment.period.period == period:
                    employee_id = assignment.employee.id
                    self.assertNotIn(employee_id, employee_assignments, 
                                    f"Employee {employee_id} assigned to multiple workstations in period {period}")
                    employee_assignments[employee_id] = assignment.workstation.id

        # Verify that each workstation has at most one employee per period
        for period in range(1, periods_per_day + 1):
            workstation_assignments = {}
            for assignment in assignments:
                if assignment.period.period == period:
                    workstation_id = assignment.workstation.id
                    self.assertNotIn(workstation_id, workstation_assignments, 
                                    f"Workstation {workstation_id} assigned to multiple employees in period {period}")
                    workstation_assignments[workstation_id] = assignment.employee.id

        # Verify that employees are only assigned to workstations they are qualified for
        for assignment in assignments:
            employee = assignment.employee
            workstation = assignment.workstation
            self.assertTrue(employee.can_work(workstation), 
                           f"Employee {employee.id} assigned to workstation {workstation.id} but is not qualified")


if __name__ == '__main__':
    unittest.main()
