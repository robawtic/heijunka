import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from ortools.sat.python.cp_model import CpModel

from domain.contexts.employee_management.entities.employee import Employee
from domain.contexts.workstation_management.entities.workstation import Workstation
from domain.contexts.employee_management.value_objects.work_history_entry import WorkHistoryEntry
from domain.rules.context import RuleContext
from domain.rules.soft import (
    add_same_day_repeat_penalties,
    add_lookback_any_period_penalties,
    add_lookback_same_period_penalties,
    add_aro_reassignment_penalties
)


class TestSoftRules(unittest.TestCase):
    def setUp(self):
        """Set up the test environment."""
        # Create a CP model
        self.model = CpModel()

        # Create employees
        self.employee1 = Employee(id=1, name="John Doe", team_id=1)
        self.employee2 = Employee(id=2, name="Jane Smith", team_id=1)
        self.employees = [self.employee1, self.employee2]

        # Create workstations
        self.workstation1 = Workstation(id=1, name="Station 1", line_type="Assembly", team_id=1)
        self.workstation2 = Workstation(id=2, name="Station 2", line_type="Assembly", team_id=1)
        self.aro_station = Workstation(id=3, name="ARO", line_type="Assembly", team_id=1)
        self.workstations = [self.workstation1, self.workstation2, self.aro_station]

        # Set up periods
        self.periods = 2

        # Create assignment variables
        self.assign = {}
        for i in range(len(self.employees)):
            for j in range(len(self.workstations)):
                for p in range(self.periods):
                    self.assign[(i, j, p)] = self.model.NewBoolVar(f"assign_e{i}_w{j}_p{p}")

        # Create rule context
        self.start_date = date.today()
        self.ctx = RuleContext(
            model=self.model,
            assign=self.assign,
            employees=self.employees,
            workstations=self.workstations,
            periods=self.periods,
            start_date=self.start_date,
            lookback=3,
            session=MagicMock()
        )

        # Work history will be added in specific tests as needed

    def test_add_lookback_any_period_penalties(self):
        """Test that add_lookback_any_period_penalties rule is correctly implemented."""
        # Add work history entries
        yesterday = self.start_date - timedelta(days=1)
        self.employee1.add_work_history_entry(
            workstation_id=1,
            worked_date=yesterday,
            work_period=1
        )

        # Configure the mock session to return work history entries
        from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel
        mock_entry = MagicMock(spec=EmployeeWorkHistoryModel)
        mock_entry.employee_id = 1
        mock_entry.station_id = 1
        mock_entry.worked_date = yesterday
        mock_entry.work_period = 1

        # Configure the query method to return our mock entry
        mock_query = MagicMock()
        mock_query.filter_by.return_value.all.return_value = [mock_entry]
        self.ctx.session.query.return_value = mock_query

        # Apply the rule
        penalties = add_lookback_any_period_penalties(self.ctx)

        # Verify that penalties were created
        self.assertTrue(penalties)

    def test_add_lookback_any_period_penalties_no_history(self):
        """Test add_lookback_any_period_penalties with no work history."""
        # Apply the rule with empty work history
        penalties = add_lookback_any_period_penalties(self.ctx)

        # Verify that no penalties were created (empty list)
        self.assertEqual(penalties, [])

    def test_add_lookback_any_period_penalties_no_start_date(self):
        """Test add_lookback_any_period_penalties with no start date."""
        # Set start_date to None
        self.ctx.start_date = None

        # Apply the rule
        penalties = add_lookback_any_period_penalties(self.ctx)

        # Verify that no penalties were created (empty list)
        self.assertEqual(penalties, [])

    def test_add_same_day_repeat_penalties(self):
        """Test that add_same_day_repeat_penalties rule is correctly implemented."""
        # Apply the rule
        penalties = add_same_day_repeat_penalties(self.ctx)

        # Verify that penalties were created
        self.assertTrue(penalties)

        # Calculate expected number of penalties
        # For each employee, workstation, we create penalties for each pair of periods
        expected_count = len(self.employees) * len(self.workstations) * (self.periods * (self.periods - 1) // 2)
        self.assertEqual(len(penalties), expected_count)

    def test_add_aro_reassignment_penalties(self):
        """Test that add_aro_reassignment_penalties rule is correctly implemented."""
        # Apply the rule
        penalties = add_aro_reassignment_penalties(self.ctx)

        # Verify that penalties were created
        self.assertTrue(penalties)


if __name__ == '__main__':
    unittest.main()
