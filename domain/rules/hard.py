# domain/rules/hard.py
from domain.rules.context import RuleContext, rule_metadata


@rule_metadata(uses=["model", "assign", "employees", "workstations", "current_period", "call_ins", "employee_offline_periods", "start_date"])
def forbid_unavailable(ctx: RuleContext):
    """
    Prevent employees from being assigned during periods they're unavailable.

    DEBUG MODE: Prints details about constraints being added.
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    current_period = ctx.current_period or 1  # Default to period 1 if not specified
    start_date = ctx.start_date
    call_ins = ctx.call_ins or []  # Default to empty list if None
    employee_offline_periods = ctx.employee_offline_periods or {}  # Default to empty dict if None

    # Convert to 0-indexed for internal use
    p = current_period - 1

    if not start_date:
        print("DEBUG: No start_date provided to forbid_unavailable")
        return  # Can't check availability without a start date

    for i, emp in enumerate(employees):
        # Check if employee called in (completely unavailable)
        if emp.name in call_ins:
            print(f"DEBUG: Employee {emp.name} called in. Forbidding period {current_period} for all workstations.")
            for j in range(len(workstations)):
                print(f"DEBUG: Forbid {emp.name} (employee {i}) from workstation {workstations[j].name} (station {j}) period {current_period}")
                model.Add(assign[(i, j, p)] == 0)
        else:
            # Check regular availability
            # Check if employee is unavailable for this period
            is_unavailable = not emp.is_available_for_period(start_date, current_period)  # Periods are 1-indexed in the domain model

            # Check if employee is marked as offline for this period
            is_offline = False
            if emp.name in employee_offline_periods:
                offline_periods = employee_offline_periods[emp.name]
                if current_period in offline_periods:  # Periods are 1-indexed
                    is_offline = True

            if is_unavailable or is_offline:
                reason = []
                if is_unavailable:
                    reason.append('not available')
                if is_offline:
                    reason.append('offline')
                print(f"DEBUG: Forbidding {emp.name} (employee {i}) from all workstations in period {current_period} due to: {', '.join(reason)}")
                for j in range(len(workstations)):
                    print(f"DEBUG: Forbid {emp.name} (employee {i}) from workstation {workstations[j].name} (station {j}) period {current_period}")
                    model.Add(assign[(i, j, p)] == 0)


@rule_metadata(uses=["model", "assign", "employees", "workstations", "current_period"])
def forbid_unknown_stations(ctx: RuleContext):
    """
    Prevent employees from being assigned to workstations they don't know.

    DEBUG MODE: Prints details about constraints being added.
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    current_period = ctx.current_period or 1  # Default to period 1 if not specified

    # Convert to 0-indexed for internal use
    p = current_period - 1

    for i, emp in enumerate(employees):
        for j, ws in enumerate(workstations):
            # Check if employee knows this workstation
            if not emp.can_work(ws):
                model.Add(assign[(i, j, p)] == 0)

@rule_metadata(uses=["model", "assign", "employees", "workstations", "current_period"])
def add_one_station_per_employee(ctx: RuleContext):
    """
    Ensure each employee is assigned to at most one workstation per period.

    This rule prevents double-booking employees by ensuring they can only
    be at one workstation at a time.
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    current_period = ctx.current_period or 1  # Default to period 1 if not specified

    # Convert to 0-indexed for internal use
    p = current_period - 1

    for i in range(len(employees)):
        model.Add(sum(assign[(i, j, p)] for j in range(len(workstations))) <= 1)


@rule_metadata(uses=["model", "assign", "employees", "workstations", "current_period"])
def add_at_most_one_per_station(ctx: RuleContext):
    """
    Ensure each workstation has at most one employee assigned per period.

    This rule prevents overstaffing by requiring at most one employee per workstation per period.
    Some workstations may remain unstaffed if there are not enough qualified employees.
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    current_period = ctx.current_period or 1  # Default to period 1 if not specified

    # Convert to 0-indexed for internal use
    p = current_period - 1

    # Find the Parts Wash station if it exists
    pw_idx = next((j for j, ws in enumerate(workstations) if ws.name == "Parts Wash"), None)

    for j in range(len(workstations)):
        # Special case for Parts Wash: only staff in first period
        if j == pw_idx and current_period != 1:
            continue

        # Require at most one employee per workstation per period
        model.Add(sum(assign[(i, j, p)] for i in range(len(employees))) == 1)
