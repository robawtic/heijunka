import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from ortools.sat.python.cp_model import CpModel

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from rules.context import RuleContext
from rules.hard import (
    forbid_consecutive_special,
    forbid_unavailable,
    forbid_unknown_stations,
    add_one_station_per_employee,
    add_exactly_one_per_station
)


class TestHardRules(unittest.TestCase):
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
        self.special_station = Workstation(id=3, name="H170", line_type="Assembly", team_id=1)
        self.parts_wash = Workstation(id=4, name="Parts Wash", line_type="Assembly", team_id=1)
        self.workstations = [self.workstation1, self.workstation2, self.special_station, self.parts_wash]

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
        self.ctx = RuleContext(
            model=self.model,
            assign=self.assign,
            days=self.days,
            employees=self.employees,
            workstations=self.workstations,
            periods=self.periods,
            start_date=date.today()
        )

        # Set up employee qualifications
        self.employee1.add_qualification("Station 1")
        self.employee1.add_qualification("Station 2")
        self.employee2.add_qualification("Station 1")
        self.employee2.add_qualification("H170")

    def test_forbid_consecutive_special(self):
        """Test that forbid_consecutive_special rule is correctly implemented."""
        # This rule is currently disabled, so we'll just verify it returns without error
        result = forbid_consecutive_special(self.ctx)
        self.assertIsNone(result)

    def test_forbid_unavailable(self):
        """Test that forbid_unavailable rule is correctly implemented."""
        # Mock the is_available_for_period method to return False for employee1 on day 0, period 1
        self.employee1.is_available_for_period = MagicMock(return_value=True)
        self.employee1.is_available_for_period.side_effect = lambda day, period: False if period == 1 else True

        # Apply the rule
        forbid_unavailable(self.ctx)

        # Verify that the model has constraints that prevent assignment
        # This is a simplified check - in a real test, you might want to verify the actual constraints
        # by checking the model's proto or using other methods
        self.assertTrue(self.model.Proto().constraints)

    def test_forbid_unknown_stations(self):
        """Test that forbid_unknown_stations rule is correctly implemented."""
        # Set up the can_work method to return appropriate values
        self.employee1.can_work = MagicMock(side_effect=lambda ws: ws.name in self.employee1.qualifications)
        self.employee2.can_work = MagicMock(side_effect=lambda ws: ws.name in self.employee2.qualifications)

        # Apply the rule
        forbid_unknown_stations(self.ctx)

        # Verify that the model has constraints that prevent assignment
        self.assertTrue(self.model.Proto().constraints)

    def test_add_one_station_per_employee(self):
        """Test that add_one_station_per_employee rule is correctly implemented."""
        # Apply the rule
        add_one_station_per_employee(self.ctx)

        # Verify that the model has constraints that limit assignments
        self.assertTrue(self.model.Proto().constraints)

    def test_add_exactly_one_per_station(self):
        """Test that add_exactly_one_per_station rule is correctly implemented."""
        # Apply the rule
        add_exactly_one_per_station(self.ctx)

        # Verify that the model has constraints that limit assignments
        self.assertTrue(self.model.Proto().constraints)


if __name__ == '__main__':
    unittest.main()
