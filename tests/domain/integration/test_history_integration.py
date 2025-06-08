import unittest
from unittest.mock import MagicMock, patch
from datetime import date, timedelta

from domain.entities.schedule.model import Schedule
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.repositories.interfaces import TeamRepositoryInterface
from domain.value_objects.work_history_entry import WorkHistoryEntry
from domain.services.cp_model_builder import CPModelBuilder
from domain.repositories.interfaces.employee_work_history_repository import EmployeeWorkHistoryRepositoryInterface


class TestHistoryIntegration(unittest.TestCase):
    """Integration test for historical data usage in scheduling."""

    def setUp(self):
        # Create test employees and workstations
        self.employees = [
            Employee(id=1, name="Employee1", team_id=1),
            Employee(id=2, name="Employee2", team_id=1)
        ]
        self.workstations = [
            Workstation(id=101, name="Station1", line_type="Main Line", team_id=1),
            Workstation(id=102, name="Station2", line_type="Main Line", team_id=1)
        ]

        # Set up dates
        self.today = date(2025, 6, 7)
        self.yesterday = self.today - timedelta(days=1)

        # Create mock repository
        self.mock_repo = MagicMock(spec=EmployeeWorkHistoryRepositoryInterface)
        self.mock_team_repo = MagicMock(spec=TeamRepositoryInterface)

        # Configure mock team repository to return a team with a name
        mock_team = MagicMock()
        mock_team.name = "TestTeam"
        self.mock_team_repo.get.return_value = mock_team

        # Set up CP model builder
        self.cp_model_builder = CPModelBuilder()

    def test_end_to_end_history_workflow(self):
        """Test the end-to-end workflow of using historical data in scheduling."""
        # 1. Set up historical data in the repository

        # Yesterday's work history
        yesterday_entries = [
            WorkHistoryEntry(employee_id=1, workstation_id=101, worked_date=self.yesterday, work_period=1),
            WorkHistoryEntry(employee_id=1, workstation_id=102, worked_date=self.yesterday, work_period=2),
            WorkHistoryEntry(employee_id=2, workstation_id=102, worked_date=self.yesterday, work_period=1),
            WorkHistoryEntry(employee_id=2, workstation_id=101, worked_date=self.yesterday, work_period=2)
        ]

        # Today's work history for period 1
        today_entries = [
            WorkHistoryEntry(employee_id=1, workstation_id=101, worked_date=self.today, work_period=1),
            WorkHistoryEntry(employee_id=2, workstation_id=102, worked_date=self.today, work_period=1)
        ]

        # Configure mock repository responses

        # For same-day repeat penalties (period 2)
        self.mock_repo.get_filtered.return_value = (today_entries, len(today_entries))

        # For lookback any period penalties
        self.mock_repo.get_distinct_stations.side_effect = lambda emp_id, start, end: {
            1: {101, 102},
            2: {101, 102}
        }.get(emp_id, set())

        # For lookback same period penalties
        self.mock_repo.get_distinct_station_periods.side_effect = lambda emp_id, start, end: {
            1: {(101, 0), (102, 1)},  # 0-indexed periods
            2: {(102, 0), (101, 1)}
        }.get(emp_id, set())

        # 2. Create a schedule
        schedule = Schedule(
            id=1,
            team_id=1,
            start_date=self.today,
            periods_per_day=2,
            status="active"  # Required parameter
        )

        # 3. Generate assignments with history repository
        with patch('domain.value_objects.work_history_entry.WorkHistoryEntry') as mock_entry_class:
            # Track calls to the repository's add method
            add_calls = []
            self.mock_repo.add.side_effect = lambda entry: add_calls.append(entry)

            # Generate assignments
            success = schedule.generate_assignments(
                employees=self.employees,
                workstations=self.workstations,
                employee_history_repo=self.mock_repo,
                team_repository=self.mock_team_repo
            )

            # 4. Verify success and repository interactions
            self.assertTrue(success, "Schedule generation should succeed")

            # Verify that get_filtered was called for same-day repeat penalties
            self.mock_repo.get_filtered.assert_called()

            # Verify that get_distinct_stations was called for lookback any period penalties
            self.mock_repo.get_distinct_stations.assert_called()

            # Verify that get_distinct_station_periods was called for lookback same period penalties
            self.mock_repo.get_distinct_station_periods.assert_called()

            # Verify that new assignments were recorded in the repository
            self.assertTrue(len(add_calls) > 0, "New assignments should be recorded in the repository")

            # Verify that the assignments follow the penalty rules
            # (This is a simplified check - in a real test, we would verify more specific constraints)
            assignments = schedule.assignments
            self.assertTrue(len(assignments) > 0, "Schedule should have assignments")

            # Print the generated schedule for inspection
            print("\nGenerated Schedule:")
            for assignment in assignments:
                print(f"Period {assignment.period.period}: {assignment.employee.name} -> {assignment.workstation.name}")

    def test_repository_error_handling(self):
        """Test that repository errors are properly handled during scheduling."""
        # Make repository raise an exception
        self.mock_repo.get_filtered.side_effect = Exception("Database connection failed")

        # Create a schedule
        schedule = Schedule(
            id=1,
            team_id=1,
            start_date=self.today,
            periods_per_day=2,
            status="active"  # Required parameter
        )

        # Generate assignments with the failing repository
        # This should not crash but should log the error and return False
        success = schedule.generate_assignments(
            employees=self.employees,
            workstations=self.workstations,
            employee_history_repo=self.mock_repo,
            team_repository=self.mock_team_repo
        )

        # Verify that schedule generation failed
        self.assertFalse(success, "Schedule generation should fail when repository fails")
        self.assertTrue("failed" in schedule.status, "Schedule status should be 'failed'")
        self.assertIsNotNone(schedule.error_message, "Schedule should have an error message")


if __name__ == '__main__':
    unittest.main()
