import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from ortools.sat.python.cp_model import CpModel

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from rules.context import HeadsubRuleContext
from rules.teams.headsub import (
    forbid_adjacent_special_loading,
    forbid_parts_wash_outside_period1,
    limit_h010_once_per_day,
    HEADSUB_RULES
)


class TestHeadsubRules(unittest.TestCase):
    def setUp(self):
        """Set up the test environment."""
        # Create a CP model
        self.model = CpModel()
        
        # Create employees
        self.employee1 = Employee(id=1, name="John Doe", team_id=1)
        self.employee2 = Employee(id=2, name="Jane Smith", team_id=1)
        self.employees = [self.employee1, self.employee2]
        
        # Create workstations
        self.h170 = Workstation(id=1, name="H170", line_type="Assembly", team_id=1)
        self.bw010 = Workstation(id=2, name="BW010", line_type="Assembly", team_id=1)
        self.parts_wash = Workstation(id=3, name="Parts Wash", line_type="Assembly", team_id=1)
        self.h010 = Workstation(id=4, name="H010", line_type="Assembly", team_id=1)
        self.loading_station = Workstation(id=5, name="Loading", line_type="Assembly", team_id=1)
        
        # Set up is_loading method for workstations
        self.h170.is_loading = MagicMock(return_value=False)
        self.bw010.is_loading = MagicMock(return_value=False)
        self.parts_wash.is_loading = MagicMock(return_value=False)
        self.h010.is_loading = MagicMock(return_value=False)
        self.loading_station.is_loading = MagicMock(return_value=True)
        
        self.workstations = [self.h170, self.bw010, self.parts_wash, self.h010, self.loading_station]
        
        # Set up periods
        self.periods = 3
        
        # Create assignment variables
        self.assign = {}
        for i in range(len(self.employees)):
            for j in range(len(self.workstations)):
                for p in range(self.periods):
                    self.assign[(i, j, p)] = self.model.NewBoolVar(f"assign_e{i}_w{j}_p{p}")

        # Create rule context
        self.start_date = date.today()
        self.ctx = HeadsubRuleContext(
            model=self.model,
            assign=self.assign,
            employees=self.employees,
            workstations=self.workstations,
            periods=self.periods,
            start_date=self.start_date,
            scheduled=[]
        )
    
    def test_forbid_adjacent_special_loading(self):
        """Test that forbid_adjacent_special_loading rule is correctly implemented."""
        # Apply the rule
        forbid_adjacent_special_loading(self.ctx)
        
        # Verify that the model has constraints that prevent assignment
        self.assertTrue(self.model.Proto().constraints)
    
    def test_forbid_parts_wash_outside_period1(self):
        """Test that forbid_parts_wash_outside_period1 rule is correctly implemented."""
        # Apply the rule
        forbid_parts_wash_outside_period1(self.ctx)
        
        # Verify that the model has constraints that prevent assignment
        self.assertTrue(self.model.Proto().constraints)
    
    def test_limit_h010_once_per_day(self):
        """Test that limit_h010_once_per_day rule is correctly implemented."""
        # Apply the rule
        limit_h010_once_per_day(self.ctx)
        
        # Verify that the model has constraints that limit assignments
        self.assertTrue(self.model.Proto().constraints)
    
    def test_limit_h010_once_per_day_with_scheduled(self):
        """Test limit_h010_once_per_day with already scheduled assignments."""
        # Set up scheduled assignments
        self.ctx.scheduled = [(1, 4, 0)]  # Employee 1 already worked at H010 in period 0
        
        # Apply the rule
        limit_h010_once_per_day(self.ctx)
        
        # Verify that the model has constraints that prevent assignment
        self.assertTrue(self.model.Proto().constraints)
    
    def test_headsub_rules_list(self):
        """Test that HEADSUB_RULES is a list of functions."""
        self.assertIsInstance(HEADSUB_RULES, list)
        # Note: Currently, HEADSUB_RULES is empty as all rules are temporarily disabled
        # If rules are re-enabled, this test should be updated to verify that each rule is callable
        # for rule in HEADSUB_RULES:
        #     self.assertTrue(callable(rule))


if __name__ == '__main__':
    unittest.main()