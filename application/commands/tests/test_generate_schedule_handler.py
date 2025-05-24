import unittest
from datetime import date

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.entities.team import Team
from domain.repositories.tests.mock_employee_repository import MockEmployeeRepository
from domain.repositories.tests.mock_workstation_repository import MockWorkstationRepository
from domain.repositories.tests.mock_team_repository import MockTeamRepository
from domain.repositories.tests.mock_assignment_repository import MockAssignmentRepository
from domain.services.schedule_service import ScheduleService
from application.commands.generate_schedule_command import GenerateScheduleCommand
from application.commands.generate_schedule_handler import GenerateScheduleHandler


class TestGenerateScheduleHandler(unittest.TestCase):
    def setUp(self):
        """Set up the test environment."""
        # Create mock repositories
        self.employee_repo = MockEmployeeRepository()
        self.workstation_repo = MockWorkstationRepository()
        self.team_repo = MockTeamRepository()
        self.assignment_repo = MockAssignmentRepository()

        # Create a schedule service
        self.schedule_service = ScheduleService()

        # Create the handler
        self.handler = GenerateScheduleHandler(
            employee_repository=self.employee_repo,
            workstation_repository=self.workstation_repo,
            team_repository=self.team_repo,
            assignment_repository=self.assignment_repo,
            schedule_service=self.schedule_service
        )

        # Add test data
        self._add_test_data()

    def _add_test_data(self):
        """Add test data to the repositories."""
        # Add team
        self.team = Team(id=1, name="headsub", description="Head Sub Team")
        self.team_repo.add(self.team)

        # Add employees
        self.employee1 = Employee(id=1, name="John Doe", team_id=1)
        self.employee2 = Employee(id=2, name="Jane Smith", team_id=1)

        self.employee_repo.add(self.employee1)
        self.employee_repo.add(self.employee2)

        # Add workstations
        self.workstation1 = Workstation(id=1, name="Station 1", line_type="Assembly", team_id=1)
        self.workstation2 = Workstation(id=2, name="Station 2", line_type="Assembly", team_id=1)

        self.workstation_repo.add(self.workstation1)
        self.workstation_repo.add(self.workstation2)

        # Add qualifications
        self.employee1.add_qualification("Station 1")
        self.employee1.add_qualification("Station 2")
        self.employee2.add_qualification("Station 1")

    def test_handle_command(self):
        """Test handling a generate schedule command."""
        # Create a command
        command = GenerateScheduleCommand(
            team_id=1,
            start_date=date.today(),
            days=1,
            periods_per_day=2,
            call_ins=None,
            force_complete=False
        )

        # Handle the command
        assignments = self.handler.handle(command)

        # Verify the results
        self.assertIsNotNone(assignments)

        # Verify that the assignments were saved to the repository
        self.assertTrue(len(self.assignment_repo.list_all()) > 0)
        self.assertEqual(len(assignments), len(self.assignment_repo.list_all()))

        # Note: The actual assignments will depend on the implementation of the schedule service,
        # which might be complex. For a real test, you might want to mock the schedule service
        # or verify specific properties of the assignments.


if __name__ == '__main__':
    unittest.main()
