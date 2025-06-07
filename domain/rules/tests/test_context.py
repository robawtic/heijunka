import unittest
from datetime import date
from unittest.mock import MagicMock

from ortools.sat.python.cp_model import CpModel

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.rules.context import RuleContext, HeadsubRuleContext, rule_metadata, adapt_rule


class TestRuleContext(unittest.TestCase):
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

        # Set up periods
        self.periods = 2

        # Create assignment variables
        self.assign = {}
        for i in range(len(self.employees)):
            for j in range(len(self.workstations)):
                for p in range(self.periods):
                    self.assign[(i, j, p)] = self.model.NewBoolVar(f"assign_e{i}_w{j}_p{p}")

    def test_rule_context_initialization(self):
        """Test that RuleContext initializes correctly."""
        # Create a context
        ctx = RuleContext(
            model=self.model,
            assign=self.assign,
            employees=self.employees,
            workstations=self.workstations,
            periods=self.periods
        )

        # Verify that the context has the expected attributes
        self.assertEqual(ctx.model, self.model)
        self.assertEqual(ctx.assign, self.assign)
        self.assertEqual(ctx.employees, self.employees)
        self.assertEqual(ctx.workstations, self.workstations)
        self.assertEqual(ctx.periods, self.periods)

        # Verify that optional attributes are initialized to None
        self.assertIsNone(ctx.start_date)
        self.assertIsNone(ctx.lookback)
        self.assertIsNone(ctx.session)
        self.assertIsNone(ctx.backup_idx)
        self.assertIsNone(ctx.team_name)

        # Verify that collections are initialized to empty
        self.assertEqual(ctx.offline_periods, {})
        self.assertEqual(ctx.scheduled, [])
        self.assertEqual(ctx.employee_offline_periods, {})
        self.assertEqual(ctx.aro_data, {})

    def test_headsub_rule_context(self):
        """Test that HeadsubRuleContext initializes correctly."""
        # Create a Headsub context
        ctx = HeadsubRuleContext(
            model=self.model,
            assign=self.assign,
            employees=self.employees,
            workstations=self.workstations,
            periods=self.periods
        )

        # Verify that the context has the expected attributes
        self.assertEqual(ctx.model, self.model)
        self.assertEqual(ctx.assign, self.assign)
        self.assertEqual(ctx.employees, self.employees)
        self.assertEqual(ctx.workstations, self.workstations)
        self.assertEqual(ctx.periods, self.periods)

        # Verify that Headsub-specific attributes are initialized
        self.assertEqual(ctx.special_stations, ["H170", "BW010", "M050", "M090"])

        # Test the is_special_station method
        self.assertTrue(ctx.is_special_station("H170"))
        self.assertTrue(ctx.is_special_station("BW010"))
        self.assertFalse(ctx.is_special_station("Station 1"))

    def test_rule_metadata_decorator(self):
        """Test that rule_metadata decorator works correctly."""
        # Define a rule with metadata
        @rule_metadata(uses=["model", "assign"])
        def test_rule(ctx):
            return ctx.model, ctx.assign

        # Verify that the metadata is attached to the function
        self.assertEqual(test_rule.__rule_uses__, ["model", "assign"])

        # Verify that the function still works
        ctx = RuleContext(
            model=self.model,
            assign=self.assign,
            employees=self.employees,
            workstations=self.workstations,
            periods=self.periods
        )
        model, assign = test_rule(ctx)
        self.assertEqual(model, self.model)
        self.assertEqual(assign, self.assign)

    def test_adapt_rule(self):
        """Test that adapt_rule function works correctly."""
        # Define a prototype rule with explicit parameters
        def prototype_rule(model, A, E, W, P):
            return model, A, E, W, P

        # Adapt the rule
        adapted_rule = adapt_rule(prototype_rule)

        # Verify that the adapted rule has the same name and docstring
        self.assertEqual(adapted_rule.__name__, prototype_rule.__name__)
        self.assertEqual(adapted_rule.__doc__, prototype_rule.__doc__)

        # Create a context
        ctx = RuleContext(
            model=self.model,
            assign=self.assign,
            employees=self.employees,
            workstations=self.workstations,
            periods=self.periods
        )

        # Call the adapted rule
        model, A, E, W, P = adapted_rule(ctx)

        # Verify that the parameters were correctly extracted from the context
        self.assertEqual(model, self.model)
        self.assertEqual(A, self.assign)
        self.assertEqual(E, self.employees)
        self.assertEqual(W, self.workstations)
        self.assertEqual(P, self.periods)


if __name__ == '__main__':
    unittest.main()
