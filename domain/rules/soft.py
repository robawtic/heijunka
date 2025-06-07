# domain/rules/soft.py
from domain.rules.context import RuleContext, rule_metadata
from datetime import timedelta
from domain.value_objects.employee_availability import AvailabilityStatus

@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods"])
def add_same_day_repeat_penalties(ctx: RuleContext):
    """
    Penalize any employee who works the same station in two different periods on the same day.

    This rule encourages variety in an employee's daily assignments by penalizing
    having them work the same station multiple times in a day.

    Returns:
        List of penalty variables to be added to the objective function
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods

    # Default weight for same-day repeat penalties
    weight = 1

    penalties = []

    for i in range(len(employees)):
        for j in range(len(workstations)):
            # For every distinct pair of periods (p1 < p2):
            for p1 in range(periods):
                for p2 in range(p1 + 1, periods):
                    # Create a penalty variable that is 1 if the employee is assigned
                    # to the same workstation in both periods
                    pen = model.NewIntVar(0, weight, f"same_day_repeat_e{i}_w{j}_p{p1}_{p2}")

                    # Create a boolean indicator for the condition
                    indicator = model.NewBoolVar(f"same_day_indicator_e{i}_w{j}_p{p1}_{p2}")

                    # indicator is true if employee works same station in both periods
                    model.AddBoolAnd([assign[(i, j, p1)], assign[(i, j, p2)]]).OnlyEnforceIf(indicator)
                    model.AddBoolOr([
                        assign[(i, j, p1)].Not(),
                        assign[(i, j, p2)].Not()
                    ]).OnlyEnforceIf(indicator.Not())

                    # Set penalty value based on indicator
                    model.Add(pen == weight).OnlyEnforceIf(indicator)
                    model.Add(pen == 0).OnlyEnforceIf(indicator.Not())

                    penalties.append(pen)

    return penalties


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods", "start_date", "lookback", "employee_history_repo"])
def add_lookback_any_period_penalties(ctx: RuleContext):
    """
    Penalize employees who are assigned to the same workstation they worked at all in the recent past
    (within a lookback window), regardless of which period they worked it.

    This rule encourages variety in an employee's assignments across days by penalizing
    having them work the same station they worked at any point in the lookback window.

    Returns:
        List of penalty variables to be added to the objective function
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods
    start_date = ctx.start_date
    lookback = max(ctx.lookback or 0, 0)  # Normalize lookback window
    repo = ctx.employee_history_repo

    # Default weight for lookback-any penalties
    weight = 1

    if not start_date or not repo or lookback == 0:
        return []  # Can't check history without start date, repository, or with zero lookback

    penalties = []
    # map station_id -> index j
    ws_idx = {ws.id: j for j, ws in enumerate(workstations)}

    from datetime import timedelta

    # Calculate lookback window
    lookback_start = start_date - timedelta(days=lookback)

    for i, emp in enumerate(employees):
        # Get all distinct stations the employee worked at in the lookback window
        worked_stations = repo.get_distinct_stations(emp.id, lookback_start, start_date)

        for station_id in worked_stations:
            j = ws_idx.get(station_id)
            if j is None:
                continue

            # Penalize assignments to stations the employee worked at in the lookback window
            for p in range(periods):
                pen = model.NewIntVar(0, weight, f"lookback_any_e{i}_w{j}_p{p}")
                indicator = model.NewBoolVar(f"lookback_any_indicator_e{i}_w{j}_p{p}")

                # indicator is true if employee is assigned to this station
                model.Add(assign[(i, j, p)] == 1).OnlyEnforceIf(indicator)
                model.Add(assign[(i, j, p)] == 0).OnlyEnforceIf(indicator.Not())

                # Set penalty value based on indicator
                model.Add(pen == weight).OnlyEnforceIf(indicator)
                model.Add(pen == 0).OnlyEnforceIf(indicator.Not())

                penalties.append(pen)

    return penalties


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods", "start_date", "lookback", "employee_history_repo"])
def add_lookback_same_period_penalties(ctx: RuleContext):
    """
    Penalize employees who are assigned to the same workstation and period they worked in the recent past
    (within a lookback window).

    This rule encourages variety in an employee's assignments across days by penalizing
    having them work the same station at the same period they worked in the lookback window.

    Returns:
        List of penalty variables to be added to the objective function
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods
    start_date = ctx.start_date
    lookback = max(ctx.lookback or 0, 0)  # Normalize lookback window
    repo = ctx.employee_history_repo

    # Default weight for lookback-same penalties
    weight = 2  # Higher weight for same period repeats

    if not start_date or not repo or lookback == 0:
        return []  # Can't check history without start date, repository, or with zero lookback

    penalties = []
    # map station_id -> index j
    ws_idx = {ws.id: j for j, ws in enumerate(workstations)}

    from datetime import timedelta

    # Calculate lookback window
    lookback_start = start_date - timedelta(days=lookback)

    for i, emp in enumerate(employees):
        # Get all distinct (station_id, work_period) pairs the employee worked in the lookback window
        station_period_pairs = repo.get_distinct_station_periods(emp.id, lookback_start, start_date)

        # Penalize assignments to (station, period) pairs the employee worked in the lookback window
        for station_id, p in station_period_pairs:
            j = ws_idx.get(station_id)
            if j is None or p < 0 or p >= periods:
                continue

            pen = model.NewIntVar(0, weight, f"lookback_same_e{i}_w{j}_p{p}")
            indicator = model.NewBoolVar(f"lookback_same_indicator_e{i}_w{j}_p{p}")

            # indicator is true if employee is assigned to this station-period pair
            model.Add(assign[(i, j, p)] == 1).OnlyEnforceIf(indicator)
            model.Add(assign[(i, j, p)] == 0).OnlyEnforceIf(indicator.Not())

            # Set penalty value based on indicator
            model.Add(pen == weight).OnlyEnforceIf(indicator)
            model.Add(pen == 0).OnlyEnforceIf(indicator.Not())

            penalties.append(pen)

    return penalties


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods", "start_date", "aro_data"])
def add_aro_reassignment_penalties(ctx: RuleContext):
    """
    Penalize reassigning employees who are already assigned as AROs.

    This rule discourages (but doesn't forbid) reassigning ARO employees
    by adding a high penalty to their assignments.

    Returns:
        List of penalty variables to be added to the objective function
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods
    start_date = ctx.start_date

    # High weight for ARO reassignment penalties
    weight = 1  # Higher than other soft constraints

    penalties = []

    for i, emp in enumerate(employees):
        # Check if employee is an ARO for this date
        is_aro = any(
            av.status == AvailabilityStatus.ARO 
            for av in emp.available_periods 
            if av.date == start_date
        )

        if is_aro:
            # Add penalties for all possible assignments of this ARO employee
            for j in range(len(workstations)):
                for p in range(periods):
                    pen = model.NewIntVar(0, weight, f"aro_reassign_e{i}_w{j}_p{p}")
                    indicator = model.NewBoolVar(f"aro_reassign_indicator_e{i}_w{j}_p{p}")

                    # indicator is true if ARO employee is assigned
                    model.Add(assign[(i, j, p)] == 1).OnlyEnforceIf(indicator)
                    model.Add(assign[(i, j, p)] == 0).OnlyEnforceIf(indicator.Not())

                    # Set penalty value based on indicator
                    model.Add(pen == weight).OnlyEnforceIf(indicator)
                    model.Add(pen == 0).OnlyEnforceIf(indicator.Not())

                    penalties.append(pen)

    return penalties
