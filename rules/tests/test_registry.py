import unittest
from unittest.mock import patch, MagicMock

from ortools.sat.python.cp_model import CpModel

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from rules.context import RuleContext, HeadsubRuleContext
from rules.registry import (
    COMMON_HARD_RULES,
    COMMON_SOFT_RULES,
    TEAM_RULES,
    get_rules_for_team,
    create_context_for_team,
    ALL_RULES
)


class TestRegistry(unittest.TestCase):
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
        self.workstations = [self.workstation1, self.workstation2]
        
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
        
        # Create context parameters
        self.context_params = {
            'model': self.model,
            'assign': self.assign,
            'days': self.days,
            'employees': self.employees,
            'workstations': self.workstations,
            'periods': self.periods
        }
    
    def test_common_hard_rules(self):
        """Test that COMMON_HARD_RULES is a list of functions."""
        self.assertIsInstance(COMMON_HARD_RULES, list)
        for rule in COMMON_HARD_RULES:
            self.assertTrue(callable(rule))
    
    def test_common_soft_rules(self):
        """Test that COMMON_SOFT_RULES is a list of functions."""
        self.assertIsInstance(COMMON_SOFT_RULES, list)
        for rule in COMMON_SOFT_RULES:
            self.assertTrue(callable(rule))
    
    def test_team_rules(self):
        """Test that TEAM_RULES is a dictionary of team names to rule lists."""
        self.assertIsInstance(TEAM_RULES, dict)
        for team_name, rules in TEAM_RULES.items():
            self.assertIsInstance(team_name, str)
            self.assertIsInstance(rules, list)
            for rule in rules:
                self.assertTrue(callable(rule))
    
    def test_get_rules_for_team_with_team(self):
        """Test that get_rules_for_team returns the correct rules for a team."""
        # Mock TEAM_RULES to have a known value
        with patch('rules.registry.TEAM_RULES', {'testteam': [lambda ctx: None]}):
            rules = get_rules_for_team('testteam')
            
            # Verify that the rules include common hard rules, team-specific rules, and common soft rules
            self.assertEqual(len(rules), len(COMMON_HARD_RULES) + 1 + len(COMMON_SOFT_RULES))
            
            # Verify that the first rules are the common hard rules
            self.assertEqual(rules[:len(COMMON_HARD_RULES)], COMMON_HARD_RULES)
            
            # Verify that the last rules are the common soft rules
            self.assertEqual(rules[-len(COMMON_SOFT_RULES):], COMMON_SOFT_RULES)
    
    def test_get_rules_for_team_without_team(self):
        """Test that get_rules_for_team returns only common rules for an unknown team."""
        rules = get_rules_for_team('unknown_team')
        
        # Verify that the rules include only common hard rules and common soft rules
        self.assertEqual(len(rules), len(COMMON_HARD_RULES) + len(COMMON_SOFT_RULES))
        
        # Verify that the first rules are the common hard rules
        self.assertEqual(rules[:len(COMMON_HARD_RULES)], COMMON_HARD_RULES)
        
        # Verify that the last rules are the common soft rules
        self.assertEqual(rules[-len(COMMON_SOFT_RULES):], COMMON_SOFT_RULES)
    
    def test_create_context_for_team_headsub(self):
        """Test that create_context_for_team returns a HeadsubRuleContext for the Headsub team."""
        ctx = create_context_for_team('headsub', **self.context_params)
        
        # Verify that the context is a HeadsubRuleContext
        self.assertIsInstance(ctx, HeadsubRuleContext)
        
        # Verify that the team_name is set
        self.assertEqual(ctx.team_name, 'headsub')
        
        # Verify that other parameters are set
        self.assertEqual(ctx.model, self.model)
        self.assertEqual(ctx.assign, self.assign)
        self.assertEqual(ctx.days, self.days)
        self.assertEqual(ctx.employees, self.employees)
        self.assertEqual(ctx.workstations, self.workstations)
        self.assertEqual(ctx.periods, self.periods)
    
    def test_create_context_for_team_other(self):
        """Test that create_context_for_team returns a RuleContext for other teams."""
        ctx = create_context_for_team('otherteam', **self.context_params)
        
        # Verify that the context is a RuleContext but not a HeadsubRuleContext
        self.assertIsInstance(ctx, RuleContext)
        self.assertNotIsInstance(ctx, HeadsubRuleContext)
        
        # Verify that the team_name is set
        self.assertEqual(ctx.team_name, 'otherteam')
        
        # Verify that other parameters are set
        self.assertEqual(ctx.model, self.model)
        self.assertEqual(ctx.assign, self.assign)
        self.assertEqual(ctx.days, self.days)
        self.assertEqual(ctx.employees, self.employees)
        self.assertEqual(ctx.workstations, self.workstations)
        self.assertEqual(ctx.periods, self.periods)
    
    def test_all_rules(self):
        """Test that ALL_RULES includes all rules."""
        # Verify that ALL_RULES is a list
        self.assertIsInstance(ALL_RULES, list)
        
        # Verify that ALL_RULES includes all common hard rules
        for rule in COMMON_HARD_RULES:
            self.assertIn(rule, ALL_RULES)
        
        # Verify that ALL_RULES includes all common soft rules
        for rule in COMMON_SOFT_RULES:
            self.assertIn(rule, ALL_RULES)
        
        # Verify that ALL_RULES includes all team-specific rules
        for rules in TEAM_RULES.values():
            for rule in rules:
                self.assertIn(rule, ALL_RULES)


if __name__ == '__main__':
    unittest.main()