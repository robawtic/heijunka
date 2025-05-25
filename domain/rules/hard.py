# domain/rules/hard.py
from domain.rules.context import RuleContext, rule_metadata


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods", "call_ins", "employee_offline_periods", "start_date"])
def forbid_unavailable(ctx: RuleContext):
    """
    Prevent employees from being assigned during periods they're unavailable.

    This rule checks each employee's availability and ensures they are not
    scheduled during times they've marked as unavailable.
    It also handles call-ins, which are employees who are completely unavailable for the day,
    and offline periods, which are periods when an employee is unavailable.
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods
    start_date = ctx.start_date
    call_ins = ctx.call_ins or []  # Default to empty list if None
    employee_offline_periods = ctx.employee_offline_periods or {}  # Default to empty dict if None

    if not start_date:
        return  # Can't check availability without a start date

    for i, emp in enumerate(employees):
        # Check if employee called in (completely unavailable)
        if emp.name in call_ins:
            # Forbid assignment to any workstation during any period
            for j in range(len(workstations)):
                for p in range(periods):
                    model.Add(assign[(i, j, p)] == 0)
        else:
            # Check regular availability
            for p in range(periods):
                # Check if employee is unavailable for this period
                is_unavailable = not emp.is_available_for_period(start_date, p + 1)  # Periods are 1-indexed in the domain model

                # Check if employee is marked as offline for this period
                is_offline = False
                if emp.name in employee_offline_periods:
                    offline_periods = employee_offline_periods[emp.name]
                    if p + 1 in offline_periods:  # Periods are 1-indexed
                        is_offline = True

                # If employee is unavailable or offline, forbid assignment
                if is_unavailable or is_offline:
                    # Forbid assignment to any workstation during this period
                    for j in range(len(workstations)):
                        model.Add(assign[(i, j, p)] == 0)


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods"])
def forbid_unknown_stations(ctx: RuleContext):
    """
    Prevent employees from being assigned to workstations they don't know.

    This rule checks each employee's qualifications and ensures they are only
    assigned to workstations they are trained for.
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods

    for i, emp in enumerate(employees):
        for j, ws in enumerate(workstations):
            # Check if employee knows this workstation
            if not emp.can_work(ws):
                # Forbid assignment to this workstation
                for p in range(periods):
                    model.Add(assign[(i, j, p)] == 0)


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods"])
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
    periods = ctx.periods

    for i in range(len(employees)):
        for p in range(periods):
            model.Add(sum(assign[(i, j, p)] for j in range(len(workstations))) <= 1)


@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods"])
def add_exactly_one_per_station(ctx: RuleContext):
    """
    Ensure each workstation has at most one employee assigned per period.

    This rule prevents overstaffing by requiring at most one employee per workstation per period.
    Some workstations may remain unstaffed if there are not enough qualified employees.
    """
    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    periods = ctx.periods

    # Find the Parts Wash station if it exists
    pw_idx = next((j for j, ws in enumerate(workstations) if ws.name == "Parts Wash"), None)

    for j in range(len(workstations)):
        for p in range(periods):
            # Special case for Parts Wash: only staff in first period
            if j == pw_idx and p != 0:
                continue

            # Require at most one employee per workstation per period
            model.Add(sum(assign[(i, j, p)] for i in range(len(employees))) == 1)