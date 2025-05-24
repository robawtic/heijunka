import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from ortools.sat.python.cp_model import CpModel

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.value_objects.work_history_entry import WorkHistoryEntry
from rules.context import RuleContext
from rules.soft import (
    add_rotation_penalties,
    add_repeat_station_penalties,
    add_workload_deviation
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

        # Set up days and periods
        self.days = 1
        self.periods = 2

        # Create assignment variables
        self.assign = {}
        for d in range(self.days):
            for i in range(len(self.employees)):
                for j in range(len(self.workstations)):
                    for p in range(self.periods):
                        self.assign[(d, i, j, p)] = self.model.NewBoolVar(f"assign_d{d}_e{i}_w{j}_p{p}")

        # Create rule context
        self.start_date = date.today()
        self.ctx = RuleContext(
            model=self.model,
            assign=self.assign,
            days=self.days,
            employees=self.employees,
            workstations=self.workstations,
            periods=self.periods,
            start_date=self.start_date,
            lookback=3,
            session=MagicMock()
        )

        # Set up work history
        self.employee1.work_history = []
        self.employee2.work_history = []

    def test_add_rotation_penalties(self):
        """Test that add_rotation_penalties rule is correctly implemented."""
        # Add work history entries
        yesterday = self.start_date - timedelta(days=1)
        self.employee1.work_history.append(
            WorkHistoryEntry(employee_id=1, workstation_id=1, worked_date=yesterday)
        )

        # Apply the rule
        penalties = add_rotation_penalties(self.ctx)

        # Verify that penalties were created
        self.assertTrue(penalties)

    def test_add_rotation_penalties_no_history(self):
        """Test add_rotation_penalties with no work history."""
        # Apply the rule with empty work history
        penalties = add_rotation_penalties(self.ctx)

        # Verify that no penalties were created (empty list)
        self.assertEqual(penalties, [])

    def test_add_rotation_penalties_no_start_date(self):
        """Test add_rotation_penalties with no start date."""
        # Set start_date to None
        self.ctx.start_date = None

        # Apply the rule
        penalties = add_rotation_penalties(self.ctx)

        # Verify that no penalties were created (empty list)
        self.assertEqual(penalties, [])

    def test_add_repeat_station_penalties(self):
        """Test that add_repeat_station_penalties rule is correctly implemented."""
        # Apply the rule
        penalties = add_repeat_station_penalties(self.ctx)

        # Verify that penalties were created
        self.assertTrue(penalties)

        # Calculate expected number of penalties
        # For each day, employee, workstation, we create penalties for each pair of periods
        expected_count = self.days * len(self.employees) * len(self.workstations) * (self.periods * (self.periods - 1) // 2)
        self.assertEqual(len(penalties), expected_count)

    def test_add_workload_deviation(self):
        """Test that add_workload_deviation rule is correctly implemented."""
        # Apply the rule
        deviations = add_workload_deviation(self.ctx)

        # Verify that deviation variables were created
        self.assertTrue(deviations)

        # Calculate expected number of deviations
        # For each day and employee, we create one deviation variable
        expected_count = self.days * len(self.employees)
        self.assertEqual(len(deviations), expected_count)


if __name__ == '__main__':
    unittest.main()
