import unittest
from unittest.mock import MagicMock, patch
from datetime import date, timedelta

from domain.rules.soft import (
    add_same_day_repeat_penalties,
    add_lookback_any_period_penalties,
    add_lookback_same_period_penalties
)
from domain.rules.context import RuleContext
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.value_objects.work_history_entry import WorkHistoryEntry
from domain.repositories.interfaces.employee_work_history_repository import EmployeeWorkHistoryRepositoryInterface
from ortools.sat.python.cp_model import CpModel


class TestHistoryPenalties(unittest.TestCase):
    def setUp(self):
        # Create mock model and assign dictionary
        self.model = CpModel()
        self.assign = {}

        # Create test employees and workstations
        self.employees = [
            Employee(id=1, name="Employee1", team_id=1),
            Employee(id=2, name="Employee2", team_id=1)
        ]
        self.workstations = [
            Workstation(id=101, name="Station1", line_type="Main Line", team_id=1),
            Workstation(id=102, name="Station2", line_type="Main Line", team_id=1)
        ]

        # Set up assign variables for the model
        for i, _ in enumerate(self.employees):
            for j, _ in enumerate(self.workstations):
                # Create variables for period 0 and period 1 (for tests that use period 2)
                self.assign[(i, j, 0)] = self.model.NewBoolVar(f'assign_e{i}_w{j}_p0')
                self.assign[(i, j, 1)] = self.model.NewBoolVar(f'assign_e{i}_w{j}_p1')

        # Create mock repository
        self.mock_repo = MagicMock(spec=EmployeeWorkHistoryRepositoryInterface)

        # Set up base context
        self.start_date = date(2025, 6, 7)
        self.ctx = RuleContext(
            model=self.model,
            assign=self.assign,
            employees=self.employees,
            workstations=self.workstations,
            periods=1,
            start_date=self.start_date,
            lookback=3,
            employee_history_repo=self.mock_repo,
            current_period=1
        )

    def test_same_day_repeat_penalties_repo_queried(self):
        """Test that the repository is queried during same-day repeat penalty evaluation."""
        # Set up mock repository to return some work history entries
        self.mock_repo.get_filtered.return_value = (
            [WorkHistoryEntry(employee_id=1, workstation_id=101, worked_date=self.start_date, work_period=1)],
            1
        )

        # Call the function with period 2 (so it looks at period 1 history)
        self.ctx.current_period = 2
        penalties = add_same_day_repeat_penalties(self.ctx)

        # Verify repository was queried (called for each employee)
        self.mock_repo.get_filtered.assert_called()
        self.assertTrue(len(penalties) > 0, "Expected penalties to be generated")

    def test_same_day_repeat_penalties_missing_repo(self):
        """Test that no penalties are applied if repository is missing."""
        # Set context with no repository
        ctx_no_repo = RuleContext(
            model=self.model,
            assign=self.assign,
            employees=self.employees,
            workstations=self.workstations,
            periods=1,
            start_date=self.start_date,
            current_period=2,
            employee_history_repo=None
        )

        penalties = add_same_day_repeat_penalties(ctx_no_repo)
        self.assertEqual(penalties, [], "Expected empty penalties list when repository is missing")

    def test_lookback_any_period_penalties_repo_queried(self):
        """Test that the repository is queried during lookback any period penalty evaluation."""
        # Set up mock repository to return some stations
        self.mock_repo.get_distinct_stations.return_value = {101}

        penalties = add_lookback_any_period_penalties(self.ctx)

        # Verify repository was queried (called for each employee)
        self.mock_repo.get_distinct_stations.assert_called()
        self.assertTrue(len(penalties) > 0, "Expected penalties to be generated")

    def test_lookback_any_period_penalties_zero_lookback(self):
        """Test that no penalties are applied if lookback is zero."""
        # Set context with zero lookback
        ctx_zero_lookback = RuleContext(
            model=self.model,
            assign=self.assign,
            employees=self.employees,
            workstations=self.workstations,
            periods=1,
            start_date=self.start_date,
            lookback=0,
            employee_history_repo=self.mock_repo,
            current_period=1
        )

        penalties = add_lookback_any_period_penalties(ctx_zero_lookback)
        self.assertEqual(penalties, [], "Expected empty penalties list when lookback is zero")

    def test_lookback_same_period_penalties_repo_queried(self):
        """Test that the repository is queried during lookback same period penalty evaluation."""
        # Set up mock repository to return some station-period pairs
        # Note: The period must match the current_period (1) for penalties to be generated
        # The current_period is 1, so we need to return a pair with period 1 (0-indexed)
        self.mock_repo.get_distinct_station_periods.return_value = {(101, 0), (102, 1)}

        penalties = add_lookback_same_period_penalties(self.ctx)

        # Verify repository was queried (called for each employee)
        self.mock_repo.get_distinct_station_periods.assert_called()
        self.assertTrue(len(penalties) > 0, "Expected penalties to be generated")

    def test_repository_error_handling(self):
        """Test that repository errors are not silently swallowed."""
        # Make repository raise an exception
        self.mock_repo.get_filtered.side_effect = Exception("Database connection failed")

        # Call the function with period 2 (so it looks at period 1 history)
        self.ctx.current_period = 2

        # The exception should propagate up
        with self.assertRaises(Exception):
            add_same_day_repeat_penalties(self.ctx)

    def test_assignment_recording(self):
        """Test that new assignments are correctly recorded in the repository."""
        from domain.entities.schedule.model import Schedule
        from domain.value_objects.schedule_period import SchedulePeriod
        from domain.value_objects.work_assignment import WorkAssignment
        from domain.services.cp_model_builder import CPModelBuilder

        # Create a schedule
        schedule = Schedule(
            id=1,
            team_id=1,
            start_date=self.start_date,
            periods_per_day=2,
            status="active"  # Required parameter
        )

        # Create a mock CPModelBuilder that returns a non-empty list of assignments
        mock_cp_builder = MagicMock(spec=CPModelBuilder)

        # Create a sample assignment to return
        schedule_period = SchedulePeriod(date=self.start_date, period=1)
        assignment = WorkAssignment(
            employee=self.employees[0],
            workstation=self.workstations[0],
            period=schedule_period
        )

        # Configure the mock to return our sample assignment
        mock_cp_builder.solve_one_period.return_value = [assignment]

        # Mock the can_work and can_handle_workstation_type methods to return True
        with patch('domain.entities.employee.Employee.can_work', return_value=True), \
             patch('domain.entities.employee.Employee.can_handle_workstation_type', return_value=True):

            # Call generate_assignments with our mock repository and mock CP builder
            schedule.generate_assignments(
                employees=self.employees,
                workstations=self.workstations,
                employee_history_repo=self.mock_repo,
                cp_model_builder=mock_cp_builder
            )

            # Verify that the repository's add method was called at least once
            self.assertTrue(self.mock_repo.add.called, "Repository add method should be called")
            self.assertTrue(len(schedule.assignments) > 0, "Schedule should have assignments")


if __name__ == '__main__':
    unittest.main()
