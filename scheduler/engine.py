# scheduler/engine.py

from domain.rules.registry import get_rules_for_team, create_context_for_team
from models import load_models

def run_schedule(teams, call_ins, overrides, config):
    """
    Run the scheduling algorithm for the given teams.

    Args:
        teams: Team name or list of team names
        call_ins: List of employee names who called in (unavailable)
        overrides: Dictionary of scheduling overrides
        config: Configuration dictionary

    Returns:
        Dictionary with status and schedule
    """
    # Load data (employees, stations, etc.) from DB or config
    employees, workstations, team_objs = load_models(teams, config)

    # Debug output
    print(f"Loaded {len(employees)} employees and {len(workstations)} workstations for team(s) {teams}")
    for i, emp in enumerate(employees):
        print(f"  Employee {i}: {emp.name}, qualifications: {emp.qualifications}")
    for j, ws in enumerate(workstations):
        print(f"  Workstation {j}: {ws.name}, is_loading: {ws.is_loading()}")

    # Build CP model, assign variables, etc.
    from ortools.sat.python import cp_model
    model = cp_model.CpModel()

    # Create decision variables
    # (day, employee_idx, workstation_idx, period) -> BoolVar
    assign = {}
    for i in range(len(employees)):
        for j in range(len(workstations)):
            for p in range(config["periods"]):
                assign[(i, j, p)] = model.NewBoolVar(f"assign_e{i}_w{j}_p{p}")

    # Create the appropriate context for the team
    ctx = create_context_for_team(
        team_name=teams,
        model=model,
        assign=assign,
        employees=employees,
        workstations=workstations,
        periods=config["periods"],
        start_date=config.get("start_date"),
        lookback=config.get("lookback", 3),
        session=config.get("session"),
        backup_idx=next((i for i, e in enumerate(employees) if e.has_role("Backup")), None),
        offline_periods=config.get("offline_periods", {}),
        scheduled=config.get("scheduled", [])
    )

    # Apply all rules via registry
    rules = get_rules_for_team(teams)
    objective_terms = []

    # Define weights for different rule types
    rule_weights = {
        "add_rotation_penalties": 500,  # Increased from 50 to 500 to make rotation more effective
        "add_repeat_station_penalties": 100,
        "add_workload_deviation": 200,
        "add_compound_fatigue_penalty_daylevel": 300,
        "add_compound_fatigue_repetition_penalty": 1000,
        "add_cross_day_repeat_penalties": 5000,
        "add_consecutive_day_combo_penalties": 100,
        "add_historical_station_fairness": 200
    }

    for rule in rules:
        result = rule(ctx)
        # If the rule returns penalty variables, add them to the objective
        if isinstance(result, list) and result:
            # Get the weight for this rule (default to 10 if not specified)
            weight = rule_weights.get(rule.__name__, 10)
            print(f"Rule {rule.__name__} returned {len(result)} penalty terms with weight {weight}")
            # This is a soft constraint that returned penalty variables
            for penalty in result:
                objective_terms.append(weight * penalty)

    # If we have objective terms, set up the objective function
    if objective_terms:
        print(f"Adding {len(objective_terms)} penalty terms to objective function")
        model.Minimize(sum(objective_terms))

    # Solve the model
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.get("max_solve_time", 60)
    print(f"Solving model with {len(employees)} employees and {len(workstations)} workstations...")
    status = solver.Solve(model)
    print(f"Solver status: {solver.StatusName(status)}")

    # Process results
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        # Extract assignments
        schedule = []
        for i, emp in enumerate(employees):
            for j, ws in enumerate(workstations):
                for p in range(config["periods"]):
                    if solver.Value(assign[(i, j, p)]) == 1:
                        schedule.append({
                            "employee_id": emp.id,
                            "employee_name": emp.name,
                            "workstation_id": ws.id,
                            "workstation_name": ws.name,
                            "period": p
                        })
        print(f"Generated {len(schedule)} assignments")
        return {
            "status": "success",
            "schedule": schedule,
            "is_optimal": status == cp_model.OPTIMAL
        }
    else:
        print(f"No solution found. Status: {solver.StatusName(status)}")
        return {
            "status": "error",
            "message": f"No solution found. Status: {solver.StatusName(status)}"
        }
