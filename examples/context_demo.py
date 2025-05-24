# examples/context_demo.py
"""
Demonstration of the Context design pattern for scheduling rules.

This script shows how to use the RuleContext class and its subclasses,
how to apply rules using the context, and how to adapt prototype rules
to use the context.
"""

from datetime import date, timedelta
from ortools.sat.python import cp_model

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from rules.context import RuleContext, HeadsubRuleContext, rule_metadata, adapt_rule
from rules.registry import get_rules_for_team, create_context_for_team


def create_demo_data():
    """Create some demo data for the example."""
    # Create employees
    employees = [
        Employee(id=1, name="Alice", team_id=1, is_active=True),
        Employee(id=2, name="Bob", team_id=1, is_active=True),
        Employee(id=3, name="Charlie", team_id=1, is_active=True),
    ]
    
    # Add qualifications
    employees[0].add_qualification("H010")
    employees[0].add_qualification("H080/H090")
    employees[1].add_qualification("H010")
    employees[1].add_qualification("Parts Wash")
    employees[2].add_qualification("H080/H090")
    employees[2].add_qualification("Parts Wash")
    
    # Create workstations
    workstations = [
        Workstation(id=1, name="H010", line_type="Sub-Assembly", is_loading_job=True),
        Workstation(id=2, name="H080/H090", line_type="Sub-Assembly"),
        Workstation(id=3, name="Parts Wash", line_type="Sub-Assembly"),
    ]
    
    return employees, workstations


def demo_context_usage():
    """Demonstrate how to use the Context design pattern."""
    print("Demonstrating Context design pattern for scheduling rules")
    print("-" * 70)
    
    # Create demo data
    employees, workstations = create_demo_data()
    
    # Create a CP model
    model = cp_model.CpModel()
    
    # Create decision variables
    periods = 3
    assign = {}
    for i in range(len(employees)):
        for j in range(len(workstations)):
            for p in range(periods):
                assign[(i, j, p)] = model.NewBoolVar(f"assign_e{i}_w{j}_p{p}")

    # Create a context
    ctx = RuleContext(
        model=model,
        assign=assign,
        employees=employees,
        workstations=workstations,
        periods=periods,
        start_date=date.today()
    )
    
    # Define a simple rule using the context
    @rule_metadata(uses=["model", "assign", "employees", "workstations"])
    def example_rule(ctx: RuleContext):
        """A simple rule that ensures employees are only assigned to workstations they know."""
        print("Applying example_rule...")
        model = ctx.model
        assign = ctx.assign
        employees = ctx.employees
        workstations = ctx.workstations

        for i, emp in enumerate(employees):
            for j, ws in enumerate(workstations):
                if not emp.can_work(ws):
                    for p in range(ctx.periods):
                        model.Add(assign[(i, j, p)] == 0)
                        print(f"  Forbidding {emp.name} from working at {ws.name}")

    # Apply the rule
    example_rule(ctx)
    print()
    
    # Define a prototype rule with explicit parameters
    def prototype_rule(model, A, E, W, P):
        """A prototype rule with explicit parameters."""
        print("Applying prototype_rule...")
        for i in range(len(E)):
            for p in range(P):
                # Ensure each employee works at most one station per period
                model.Add(sum(A[(i, j, p)] for j in range(len(W))) <= 1)
                print(f"  Ensuring {E[i].name} works at most one station in period {p+1}")
    
    # Adapt the prototype rule to use the context
    adapted_rule = adapt_rule(prototype_rule)
    
    # Apply the adapted rule
    adapted_rule(ctx)
    print()
    
    # Create a team-specific context
    headsub_ctx = HeadsubRuleContext(
        model=model,
        assign=assign,
        employees=employees,
        workstations=workstations,
        periods=periods,
        start_date=date.today(),
        special_stations=["H010"]  # Override the default special stations
    )
    
    # Define a rule that uses the team-specific context
    @rule_metadata(uses=["model", "assign", "special_stations"])
    def team_specific_rule(ctx: HeadsubRuleContext):
        """A rule that uses the team-specific context."""
        print("Applying team_specific_rule...")
        model = ctx.model
        assign = ctx.assign
        
        for j, ws in enumerate(ctx.workstations):
            if ctx.is_special_station(ws.name):
                print(f"  {ws.name} is a special station for this team")
    
    # Apply the team-specific rule
    team_specific_rule(headsub_ctx)
    print()
    
    # Demonstrate using the registry
    print("Demonstrating rule registry...")
    team_name = "headsub"
    
    # Create a context for the team
    registry_ctx = create_context_for_team(
        team_name=team_name,
        model=model,
        assign=assign,
        employees=employees,
        workstations=workstations,
        periods=periods,
        start_date=date.today()
    )
    
    # Get rules for the team
    rules = get_rules_for_team(team_name)
    print(f"Found {len(rules)} rules for team '{team_name}'")
    
    # Apply the first rule as an example
    if rules:
        rule = rules[0]
        print(f"Applying rule: {rule.__name__}")
        rule(registry_ctx)
    
    print("\nContext design pattern demonstration complete!")


if __name__ == "__main__":
    demo_context_usage()