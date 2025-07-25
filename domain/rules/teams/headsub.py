# domain/rules/teams/headsub.py
from domain.rules.context import RuleContext, HeadsubRuleContext, rule_metadata


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods"])
def forbid_adjacent_special_loading(ctx: HeadsubRuleContext):
    """
    Prevent employees from working at special loading stations in adjacent periods.

    This rule is specific to the Headsub team and ensures that employees don't
    get assigned to physically demanding loading stations in adjacent periods.
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods

    # Find loading stations and special stations
    special_stations = {"H170", "BW010"}
    loading_indices = [j for j, ws in enumerate(workstations) if ws.is_loading]
    special_indices = [j for j, ws in enumerate(workstations) if ws.name in special_stations]

    for i in range(len(employees)):
        for p in range(periods):
            # For each special station
            for s in special_indices:
                v = assign[(i, s, p)]
                # Prevent assignment to loading stations in adjacent periods
                if p > 0:
                    for l in loading_indices:
                        model.AddImplication(v, assign[(i, l, p-1)].Not())
                if p < periods - 1:
                    for l in loading_indices:
                        model.AddImplication(v, assign[(i, l, p+1)].Not())

            # For each loading station
            for l in loading_indices:
                v = assign[(i, l, p)]
                # Prevent assignment to special stations in adjacent periods
                if p > 0:
                    for s in special_indices:
                        model.AddImplication(v, assign[(i, s, p-1)].Not())
                if p < periods - 1:
                    for s in special_indices:
                        model.AddImplication(v, assign[(i, s, p+1)].Not())


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods"])
def forbid_parts_wash_outside_period1(ctx: RuleContext):
    """
    Prevent employees from being assigned to Parts Wash outside the first period.

    This rule is specific to the Headsub team and ensures that Parts Wash
    is only staffed during the first period of the day.
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods

    # Find the Parts Wash station if it exists
    try:
        pw_idx = next(j for j, ws in enumerate(workstations) if ws.name == "Parts Wash")
    except StopIteration:
        return  # No Parts Wash station found

    for i in range(len(employees)):
        for p in range(1, periods):  # Skip period 0 (first period)
            model.Add(assign[(i, pw_idx, p)] == 0)


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods", "start_date", "scheduled"])
def limit_h010_once_per_day(ctx: RuleContext):
    """
    Limit employees to working at H010 at most once per day.

    This rule is specific to the Headsub team and ensures that employees
    don't work at the H010 station more than once per day.
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods
    start_date = ctx.start_date
    scheduled = ctx.scheduled or []

    # Find the H010 station if it exists
    try:
        h010_idx = next(j for j, ws in enumerate(workstations) if ws.name == "H010")
    except StopIteration:
        return  # No H010 station found

    h010_id = workstations[h010_idx].id

    for i, emp in enumerate(employees):
        # Check if employee already worked H010 today in scheduled assignments
        already_worked = sum(
            1 for (eid, sid, _) in scheduled
            if eid == emp.id and sid == h010_id
        )

        if already_worked >= 1:
            # Prevent any additional assignments to H010 today
            for p in range(periods):
                model.Add(assign[(i, h010_idx, p)] == 0)
        else:
            # Limit to at most one assignment to H010 today
            model.Add(sum(assign[(i, h010_idx, p)] for p in range(periods)) <= 1)


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods"])
def require_full_staff_for_parts_wash(ctx: HeadsubRuleContext):
    """
    Only allow any assignment to "Parts Wash" if there are enough employees to cover all other stations first.
    Otherwise, forbid Parts Wash entirely.
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods

    total_employees = len(employees)
    # Count every workstation except "Parts Wash"
    total_other_stations = sum(1 for ws in workstations if ws.name != "Parts Wash")

    if total_employees < total_other_stations:
        # Not enough staff → block Parts Wash everywhere
        try:
            pw_idx = next(j for j, ws in enumerate(workstations) if ws.name == "Parts Wash")
        except StopIteration:
            return  # No Parts Wash station found

        for i in range(total_employees):
            for p in range(periods):
                model.Add(assign[(i, pw_idx, p)] == 0)


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods", "start_date", "scheduled"])
def limit_heavy_loading_jobs(ctx: HeadsubRuleContext):
    """
    Limit employees to working at heavy loading stations (H170, BW010) at most once per day.
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods
    scheduled = ctx.scheduled or []

    # Find heavy loading stations
    heavy_stations = {"H170", "BW010"}
    heavy_indices = [j for j, ws in enumerate(workstations) if ws.name in heavy_stations]
    heavy_ids = [workstations[j].id for j in heavy_indices]

    for i, emp in enumerate(employees):
        # Check if employee already worked a heavy loading station today
        already_worked = sum(
            1 for (eid, sid, _) in scheduled
            if eid == emp.id and sid in heavy_ids
        )

        if already_worked >= 1:
            # Prevent any additional assignments to heavy loading stations today
            for j in heavy_indices:
                for p in range(periods):
                    model.Add(assign[(i, j, p)] == 0)
        else:
            # Limit to at most one assignment to heavy loading stations today
            model.Add(sum(assign[(i, j, p)] for j in heavy_indices for p in range(periods)) <= 1)


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods", "start_date", "scheduled"])
def limit_head_loading_jobs(ctx: HeadsubRuleContext):
    """
    Limit employees to working at head loading stations (M050, M090) at most once per day.
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods
    scheduled = ctx.scheduled or []

    # Find head loading stations
    head_stations = {"M050", "M090"}
    head_indices = [j for j, ws in enumerate(workstations) if ws.name in head_stations]
    head_ids = [workstations[j].id for j in head_indices]

    for i, emp in enumerate(employees):
        # Check if employee already worked a head loading station today
        already_worked = sum(
            1 for (eid, sid, _) in scheduled
            if eid == emp.id and sid in head_ids
        )

        if already_worked >= 1:
            # Prevent any additional assignments to head loading stations today
            for j in head_indices:
                for p in range(periods):
                    model.Add(assign[(i, j, p)] == 0)
        else:
            # Limit to at most one assignment to head loading stations today
            model.Add(sum(assign[(i, j, p)] for j in head_indices for p in range(periods)) <= 1)


# forbid_consecutive_special is a headsub specific rule.
@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods"])
def forbid_consecutive_special(ctx: RuleContext):
    """
    Prevent employees from working at special stations in consecutive periods.

    This rule ensures that employees don't get assigned to physically demanding
    or skill-intensive stations in back-to-back periods, reducing fatigue and errors.
    """

    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods

    # Define which stations are considered "special"
    special_stations = ["H170", "BW010", "M050", "M090"]
    special_indices = [j for j, ws in enumerate(workstations)
                      if ws.name in special_stations]

    # For each employee
    for i in range(len(employees)):
        # For each consecutive pair of periods
        for p in range(periods - 1):
            # For each pair of special stations
            for s1 in special_indices:
                for s2 in special_indices:
                    # Forbid assignment to special stations in consecutive periods
                    model.Add(assign[(i, s1, p)] + assign[(i, s2, p + 1)] <= 1)
# List of all Headsub team rules

HEADSUB_RULES = [
    forbid_adjacent_special_loading,
    forbid_parts_wash_outside_period1,
    limit_h010_once_per_day,
    limit_heavy_loading_jobs,
    limit_head_loading_jobs,
    forbid_consecutive_special,
    require_full_staff_for_parts_wash
]
