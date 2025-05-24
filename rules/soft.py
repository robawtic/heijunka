# rules/soft.py
from rules.context import RuleContext, rule_metadata
from datetime import timedelta

@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods", "start_date", "lookback", "session"])
def add_rotation_penalties(ctx: RuleContext):
    """
    Add penalties for assigning employees to the same workstation they worked recently.

    This rule encourages rotation by penalizing assignments that would have an employee
    work the same station they worked in the recent past (within the lookback window).

    Returns:
        List of penalty variables to be added to the objective function
    """
    print("Applying add_rotation_penalties rule...")
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods
    start_date = ctx.start_date
    lookback = ctx.lookback or 5  # Default lookback of 3 days
    session = ctx.session

    penalties = []

    # Create a mapping from employee/workstation IDs to their indices in the lists
    emp_idx = {e.id: i for i, e in enumerate(employees)}
    ws_idx = {w.id: j for j, w in enumerate(workstations)}

    if not start_date or not session:
        print(f"  Cannot apply rotation penalties: start_date={start_date}, session={session}")
        return penalties  # Can't check history without start date or session

    from datetime import timedelta
    from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel

    today = start_date
    # For each lookback offset, check history
    for k in range(1, lookback + 1):
        hist_date = today - timedelta(days=k)

        # Query work history for the historical date from the database
        for i, emp in enumerate(employees):
            past_entries = (
                session.query(EmployeeWorkHistoryModel)
                       .filter_by(employee_id=emp.id, worked_date=hist_date)
                       .all()
            )

            for entry in past_entries:
                j = ws_idx.get(entry.station_id)
                if j is None:
                    continue

                # Create a stronger penalty by penalizing all periods
                for p in range(periods):
                    # Create a penalty variable that is 1 if the employee is assigned
                    # to the same workstation they worked on the historical date
                    pen = model.NewBoolVar(f"rot_k{k}_e{i}_w{j}_p{p}")
                    model.Add(assign[(i, j, p)] == 1).OnlyEnforceIf(pen)
                    penalties.append(pen)

    return penalties


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods"])
def add_repeat_station_penalties(ctx: RuleContext):
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

    penalties = []

    for i in range(len(employees)):
        for j in range(len(workstations)):
            # For every distinct pair of periods (p1 < p2):
            for p1 in range(periods):
                for p2 in range(p1 + 1, periods):
                    # Create a penalty variable that is 1 if the employee is assigned
                    # to the same workstation in both periods
                    pen = model.NewBoolVar(f"repeat_e{i}_w{j}_p{p1}_{p2}")

                    # pen → (assigned at p1 AND assigned at p2)
                    model.AddBoolAnd([assign[(i, j, p1)], assign[(i, j, p2)]]).OnlyEnforceIf(pen)

                    # if either slot is unassigned, no penalty
                    model.AddBoolOr([
                        assign[(i, j, p1)].Not(),
                        assign[(i, j, p2)].Not(),
                        pen
                    ]).OnlyEnforceIf(pen.Not())

                    penalties.append(pen)

    return penalties


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods"])
def add_workload_deviation(ctx: RuleContext):
    """
    Minimize per-day workload deviation across employees.

    This rule tries to ensure that the workload is distributed fairly among employees
    by penalizing deviations from the average number of assignments per employee.

    Returns:
        List of deviation variables to be added to the objective function
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods

    # Identify core workstations (excluding special stations like ARO)
    core_idxs = [j for j, ws in enumerate(workstations) if ws.name not in ("ARO",)]

    # Calculate target assignments per employee
    target = (periods * len(core_idxs)) // len(employees)
    deviations = []

    for i in range(len(employees)):
        # Count total assignments for this employee on this day
        total = sum(assign[(i, j, p)] for j in core_idxs for p in range(periods))

        # Create a deviation variable that measures how far from target
        dev = model.NewIntVar(0, periods * len(core_idxs), f"dev_e{i}")

        # Set the deviation to be the absolute difference from target
        model.Add(dev >= total - target)
        model.Add(dev >= target - total)

        deviations.append(dev)

    return deviations


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods"])
def add_compound_fatigue_penalty_daylevel(ctx: RuleContext):
    """
    Penalize employees who are assigned to all three types of demanding stations on the same day:
    - H010
    - Heavy loading stations (BW010, H170)
    - Head loading stations (M050, M090)

    This rule encourages variety in an employee's daily assignments by penalizing
    having them work all three types of demanding stations on the same day.

    Returns:
        List of penalty variables to be added to the objective function
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods

    penalties = []

    # Find station indices
    name_to_idx = {ws.name: j for j, ws in enumerate(workstations)}

    setA = [name_to_idx.get("H010")]
    setB = [name_to_idx.get(n) for n in ["BW010", "H170"] if n in name_to_idx]
    setC = [name_to_idx.get(n) for n in ["M050", "M090"] if n in name_to_idx]

    # Skip if any set is empty (station not found)
    if not setA or not setB or not setC:
        return penalties

    for i in range(len(employees)):
        # Create boolean variables for each set
        hasA = model.NewBoolVar(f"cf_a_e{i}")
        hasB = model.NewBoolVar(f"cf_b_e{i}")
        hasC = model.NewBoolVar(f"cf_c_e{i}")
        pen = model.NewBoolVar(f"cf_penalty_e{i}")

        # hasA is true if employee works at any station in setA
        model.AddBoolOr([assign[(i, j, p)] for j in setA for p in range(periods)]).OnlyEnforceIf(hasA)
        model.AddBoolAnd([assign[(i, j, p)].Not() for j in setA for p in range(periods)]).OnlyEnforceIf(hasA.Not())

        # hasB is true if employee works at any station in setB
        model.AddBoolOr([assign[(i, j, p)] for j in setB for p in range(periods)]).OnlyEnforceIf(hasB)
        model.AddBoolAnd([assign[(i, j, p)].Not() for j in setB for p in range(periods)]).OnlyEnforceIf(hasB.Not())

        # hasC is true if employee works at any station in setC
        model.AddBoolOr([assign[(i, j, p)] for j in setC for p in range(periods)]).OnlyEnforceIf(hasC)
        model.AddBoolAnd([assign[(i, j, p)].Not() for j in setC for p in range(periods)]).OnlyEnforceIf(hasC.Not())

        # Penalty is true if employee works at all three types
        model.AddBoolAnd([hasA, hasB, hasC]).OnlyEnforceIf(pen)
        model.AddBoolOr([hasA.Not(), hasB.Not(), hasC.Not()]).OnlyEnforceIf(pen.Not())

        penalties.append(pen)

    return penalties


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods", "start_date", "lookback", "session", "scheduled"])
def add_compound_fatigue_repetition_penalty(ctx: RuleContext):
    """
    Penalize employees who are assigned to all three types of demanding stations after
    having worked all three in the recent past (within the lookback window).

    This rule encourages variety across days by penalizing employees who have already
    worked all three types of demanding stations in the recent past.

    Returns:
        List of penalty variables to be added to the objective function
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods
    start_date = ctx.start_date
    lookback = ctx.lookback or 3
    session = ctx.session
    scheduled = ctx.scheduled or []

    if not start_date or not session:
        return []  # Can't check history without start date or session

    penalties = []
    emp_idx = {e.id: i for i, e in enumerate(employees)}
    ws_by_id = {ws.id: ws for ws in workstations}

    from datetime import timedelta
    from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel

    today = start_date
    for i, emp in enumerate(employees):
        # Check if employee worked all three types in history
        did_A = did_B = did_C = False

        for k in range(1, lookback + 1):
            past_date = today - timedelta(days=k)
            entries = session.query(EmployeeWorkHistoryModel).filter_by(
                employee_id=emp.id, 
                worked_date=past_date
            ).all()

            for entry in entries:
                ws = ws_by_id.get(entry.station_id)
                if not ws:
                    continue

                if ws.name == "H010":
                    did_A = True
                elif ws.name in ["BW010", "H170"]:
                    did_B = True
                elif ws.name in ["M050", "M090"]:
                    did_C = True

        # If employee worked all three types in history, penalize doing it again
        if did_A and did_B and did_C:
            # Find station indices for today
            setA = [j for j, ws in enumerate(workstations) if ws.name == "H010"]
            setB = [j for j, ws in enumerate(workstations) if ws.name in ["BW010", "H170"]]
            setC = [j for j, ws in enumerate(workstations) if ws.name in ["M050", "M090"]]

            # Skip if any set is empty (station not found)
            if not setA or not setB or not setC:
                continue

            # Create boolean variables for each set
            hasA = model.NewBoolVar(f"cf_hist_a_e{i}")
            hasB = model.NewBoolVar(f"cf_hist_b_e{i}")
            hasC = model.NewBoolVar(f"cf_hist_c_e{i}")
            pen = model.NewBoolVar(f"cf_hist_penalty_e{i}")

            # hasA is true if employee works at any station in setA
            model.AddBoolOr([assign[(i, j, p)] for j in setA for p in range(periods)]).OnlyEnforceIf(hasA)
            model.AddBoolAnd([assign[(i, j, p)].Not() for j in setA for p in range(periods)]).OnlyEnforceIf(hasA.Not())

            # hasB is true if employee works at any station in setB
            model.AddBoolOr([assign[(i, j, p)] for j in setB for p in range(periods)]).OnlyEnforceIf(hasB)
            model.AddBoolAnd([assign[(i, j, p)].Not() for j in setB for p in range(periods)]).OnlyEnforceIf(hasB.Not())

            # hasC is true if employee works at any station in setC
            model.AddBoolOr([assign[(i, j, p)] for j in setC for p in range(periods)]).OnlyEnforceIf(hasC)
            model.AddBoolAnd([assign[(i, j, p)].Not() for j in setC for p in range(periods)]).OnlyEnforceIf(hasC.Not())

            # Penalty is true if employee works at all three types
            model.AddBoolAnd([hasA, hasB, hasC]).OnlyEnforceIf(pen)
            model.AddBoolOr([hasA.Not(), hasB.Not(), hasC.Not()]).OnlyEnforceIf(pen.Not())

            penalties.append(pen)

    return penalties


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods", "lookback", "start_date", "session"])
def add_consecutive_day_combo_penalties(ctx: RuleContext):
    """
    Penalize employees who are assigned to all three types of demanding stations after
    having worked all three in the recent past (within the lookback window).

    This rule encourages variety across days by penalizing employees who have already
    worked all three types of demanding stations in the recent past.

    Returns:
        List of penalty variables to be added to the objective function
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods
    lookback = ctx.lookback or 3
    start_date = ctx.start_date
    session = ctx.session

    if not start_date or not session:
        return []  # Can't check history without start date or session

    # Find station indices
    name_to_idx = {ws.name: j for j, ws in enumerate(workstations)}

    setA = [name_to_idx.get("H010")]
    setB = [name_to_idx.get(n) for n in ["BW010", "H170"] if n in name_to_idx]
    setC = [name_to_idx.get(n) for n in ["M050", "M090"] if n in name_to_idx]

    # Skip if any set is empty (station not found)
    if not setA or not setB or not setC:
        return []

    from datetime import timedelta
    from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel

    penalties = []
    for i, emp in enumerate(employees):
        # First, check if the employee worked all three types in the past
        past_combo = False

        # Check historical data for each day in the lookback window
        for k in range(1, lookback + 1):
            past_date = start_date - timedelta(days=k)
            entries = session.query(EmployeeWorkHistoryModel).filter_by(
                employee_id=emp.id,
                worked_date=past_date
            ).all()

            # Check if employee worked all three types on this past day
            did_A = did_B = did_C = False
            for entry in entries:
                ws_name = next((ws.name for ws in workstations if ws.id == entry.station_id), None)
                if not ws_name:
                    continue

                if ws_name == "H010":
                    did_A = True
                elif ws_name in ["BW010", "H170"]:
                    did_B = True
                elif ws_name in ["M050", "M090"]:
                    did_C = True

            # If they worked all three types on this day, set past_combo to True
            if did_A and did_B and did_C:
                past_combo = True
                break

        # If they worked all three types in the past, penalize them working all three types today
        if past_combo:
            # Create boolean variables for each set
            hasA = model.NewBoolVar(f"consec_A_e{i}")
            hasB = model.NewBoolVar(f"consec_B_e{i}")
            hasC = model.NewBoolVar(f"consec_C_e{i}")
            pen = model.NewBoolVar(f"consec_combo_e{i}")

            # hasA is true if employee works at any station in setA
            model.AddBoolOr([assign[(i, j, p)] for j in setA for p in range(periods)]).OnlyEnforceIf(hasA)
            model.AddBoolAnd([assign[(i, j, p)].Not() for j in setA for p in range(periods)]).OnlyEnforceIf(hasA.Not())

            # hasB is true if employee works at any station in setB
            model.AddBoolOr([assign[(i, j, p)] for j in setB for p in range(periods)]).OnlyEnforceIf(hasB)
            model.AddBoolAnd([assign[(i, j, p)].Not() for j in setB for p in range(periods)]).OnlyEnforceIf(hasB.Not())

            # hasC is true if employee works at any station in setC
            model.AddBoolOr([assign[(i, j, p)] for j in setC for p in range(periods)]).OnlyEnforceIf(hasC)
            model.AddBoolAnd([assign[(i, j, p)].Not() for j in setC for p in range(periods)]).OnlyEnforceIf(hasC.Not())

            # Penalty is true if employee works at all three types today
            model.AddBoolAnd([hasA, hasB, hasC]).OnlyEnforceIf(pen)
            model.AddBoolOr([hasA.Not(), hasB.Not(), hasC.Not()]).OnlyEnforceIf(pen.Not())

            penalties.append(pen)

    return penalties


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods", "start_date", "lookback", "session"])
def add_cross_day_repeat_penalties(ctx: RuleContext):
    """
    Look back up to `lookback` days in EmployeeWorkHistory and penalize assigning an employee to
    the same (station, period) they worked on in that window.

    This rule encourages variety in an employee's assignments across days by
    penalizing having them work the same station at the same period on different days.

    Returns:
        List of penalty variables to be added to the objective function
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods
    start_date = ctx.start_date
    lookback = ctx.lookback or 3
    session = ctx.session

    if not start_date or not session:
        return []  # Can't check history without start date or session

    penalties = []
    # map station_id -> index j
    ws_idx = {ws.id: j for j, ws in enumerate(workstations)}

    from datetime import timedelta
    from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel

    for i, emp in enumerate(employees):
        # gather all (j,p) pairs they did in the last `lookback` days
        prev_pairs = set()
        for k in range(1, lookback + 1):
            prev_date = start_date - timedelta(days=k)
            past = (
                session.query(EmployeeWorkHistoryModel)
                       .filter_by(employee_id=emp.id,
                                  worked_date=prev_date)
                       .all()
            )
            for ent in past:
                j = ws_idx.get(ent.station_id)
                # assume ent.work_period is 1-based; convert to 0-based
                p = ent.work_period - 1
                if j is not None and 0 <= p < periods:
                    prev_pairs.add((j, p))

        # now penalize any match today
        for j, p in prev_pairs:
            pen = model.NewBoolVar(f"crosshist_e{i}_j{j}_p{p}")
            # enforce: pen == assign[i,j,p]
            model.Add(assign[(i, j, p)] == pen)
            penalties.append(pen)

    return penalties


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods", "session", "start_date"])
def add_historical_station_fairness(ctx: RuleContext):
    """
    Minimize deviation from fair distribution of stations based on historical assignments.

    This rule looks at the last 30 days of actual work history and tries to ensure
    that the new schedule maintains a fair distribution of stations among qualified employees.

    Returns:
        List of deviation variables to be added to the objective function
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods
    session = ctx.session
    start_date = ctx.start_date
    history_lookback_days = 30  # Look back 30 days for historical fairness

    if not session or not start_date:
        return []  # Can't check history without session or start date

    penalties = []

    from sqlalchemy import func
    from datetime import timedelta
    from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel

    # 1) Load last-30-day true history
    cutoff = start_date - timedelta(days=history_lookback_days)
    rows = (
        session.query(
            EmployeeWorkHistoryModel.employee_id,
            EmployeeWorkHistoryModel.station_id,
            func.count().label("cnt")
        )
        .filter(
            EmployeeWorkHistoryModel.worked_date >= cutoff,
            EmployeeWorkHistoryModel.is_generated == False
        )
        .group_by(
            EmployeeWorkHistoryModel.employee_id,
            EmployeeWorkHistoryModel.station_id
        )
        .all()
    )
    hist_counts = {
        (r.employee_id, r.station_id): r.cnt
        for r in rows
    }

    # 2) Fairness per station among qualified employees
    for j, ws in enumerate(workstations):
        # Find employees who actually know this station
        qualified = []
        for i, emp in enumerate(employees):
            if emp.can_work(ws):
                qualified.append((i, emp))
        if not qualified:
            continue

        # Compute total historical + future slots
        total_hist = sum(
            hist_counts.get((emp.id, ws.id), 0)
            for _, emp in qualified
        )
        total_future = periods  # Just one day
        avg = (total_hist + total_future) / len(qualified)

        for i, emp in qualified:
            # Historical count
            h = hist_counts.get((emp.id, ws.id), 0)

            # New slots variable
            new_var = model.NewIntVar(0, periods, f"new_j{j}_e{i}")
            model.Add(new_var == sum(
                assign[(i, j, p)]
                for p in range(periods)
            ))

            # Combined total
            comb = model.NewIntVar(
                0,
                periods + history_lookback_days * periods,
                f"comb_j{j}_e{i}"
            )
            model.Add(comb == new_var + h)

            # Absolute deviation
            diff = model.NewIntVar(
                0,
                periods + history_lookback_days * periods,
                f"fair_j{j}_e{i}"
            )
            model.Add(diff >= comb - int(avg))
            model.Add(diff >= int(avg) - comb)
            penalties.append(diff)

    return penalties
