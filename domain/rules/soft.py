# domain/rules/soft.py
from domain.rules.context import RuleContext, rule_metadata
from datetime import timedelta
from domain.value_objects.employee_availability import AvailabilityStatus

@rule_metadata(uses=["model", "assign", "employees", "workstations", "current_period", "start_date", "employee_history_repo"])
def add_same_day_repeat_penalties(ctx: RuleContext):
    """
    Penalize any employee who works the same station in two different periods on the same day.

    This rule encourages variety in an employee's daily assignments by penalizing
    having them work the same station multiple times in a day.

    Returns:
        List of penalty variables to be added to the objective function
    """
    import logging
    logger = logging.getLogger(__name__)

    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    current_period = ctx.current_period or 1  # Default to period 1 if not specified
    start_date = ctx.start_date
    repo = ctx.employee_history_repo

    # Convert to 0-indexed for internal use
    p = current_period - 1

    # Default weight for same-day repeat penalties
    weight = 10000  # Higher weight to strongly discourage same-day repeats

    if not start_date:
        logger.warning("Cannot apply same-day repeat penalties: start_date is missing")
        return []

    if not repo:
        logger.warning("Cannot apply same-day repeat penalties: employee_history_repo is missing")
        return []

    if current_period <= 1:
        logger.info("Skipping same-day repeat penalties for period 1 (no previous periods)")
        return []

    penalties = []
    # map station_id -> index j
    ws_idx = {ws.id: j for j, ws in enumerate(workstations)}

    try:
        for i, emp in enumerate(employees):
            # Get all work history entries for this employee on the current day up to the current period
            entries, _ = repo.get_filtered(
                employee_id=emp.id,
                start_date=start_date,
                end_date=start_date,  # Same day
                period=None  # All periods
            )

            # Extract workstation IDs from previous periods on the same day
            previous_stations = set()
            for entry in entries:
                # Only consider periods before the current one
                if entry.work_period < current_period:
                    previous_stations.add(entry.workstation_id)

            # Penalize assignments to stations the employee already worked at earlier today
            for station_id in previous_stations:
                j = ws_idx.get(station_id)
                if j is None:
                    continue

                # Penalize assignments to stations the employee already worked at earlier today
                pen = model.NewIntVar(0, weight, f"same_day_repeat_e{i}_w{j}_p{current_period}")
                indicator = model.NewBoolVar(f"same_day_repeat_indicator_e{i}_w{j}_p{current_period}")

                # indicator is true if employee is assigned to this station
                model.Add(assign[(i, j, p)] == 1).OnlyEnforceIf(indicator)
                model.Add(assign[(i, j, p)] == 0).OnlyEnforceIf(indicator.Not())

                # Set penalty value based on indicator
                model.Add(pen == weight).OnlyEnforceIf(indicator)
                model.Add(pen == 0).OnlyEnforceIf(indicator.Not())

                penalties.append(pen)

        logger.info(f"Added {len(penalties)} same-day repeat penalties for period {current_period}")
        return penalties
    except Exception as e:
        logger.error(f"Error applying same-day repeat penalties: {str(e)}")
        # Re-raise the exception to make failures visible
        raise


@rule_metadata(uses=["model", "assign", "employees", "workstations", "current_period", "start_date", "lookback", "employee_history_repo"])
def add_lookback_any_period_penalties(ctx: RuleContext):
    """
    Penalize employees who are assigned to the same workstation they worked at all in the recent past
    (within a lookback window), regardless of which period they worked it.

    This rule encourages variety in an employee's assignments across days by penalizing
    having them work the same station they worked at any point in the lookback window.

    Returns:
        List of penalty variables to be added to the objective function
    """
    import logging
    logger = logging.getLogger(__name__)

    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    current_period = ctx.current_period or 1  # Default to period 1 if not specified
    start_date = ctx.start_date
    lookback = max(ctx.lookback or 0, 0)  # Normalize lookback window
    repo = ctx.employee_history_repo

    # Convert to 0-indexed for internal use
    p = current_period - 1

    # Default weight for lookback-any penalties
    weight = 10000

    if not start_date:
        logger.warning("Cannot apply lookback-any penalties: start_date is missing")
        return []

    if not repo:
        logger.warning("Cannot apply lookback-any penalties: employee_history_repo is missing")
        return []

    if lookback == 0:
        logger.info("Skipping lookback-any penalties: lookback window is zero")
        return []

    penalties = []
    # map station_id -> index j
    ws_idx = {ws.id: j for j, ws in enumerate(workstations)}

    from datetime import timedelta

    # Calculate lookback window
    lookback_start = start_date - timedelta(days=lookback)
    logger.info(f"Applying lookback-any penalties with {lookback} day window ({lookback_start} to {start_date})")

    try:
        for i, emp in enumerate(employees):
            # Get all distinct stations the employee worked at in the lookback window
            worked_stations = repo.get_distinct_stations(emp.id, lookback_start, start_date)

            for station_id in worked_stations:
                j = ws_idx.get(station_id)
                if j is None:
                    continue

                # Penalize assignments to stations the employee worked at in the lookback window
                pen = model.NewIntVar(0, weight, f"lookback_any_e{i}_w{j}_p{current_period}")
                indicator = model.NewBoolVar(f"lookback_any_indicator_e{i}_w{j}_p{current_period}")

                # indicator is true if employee is assigned to this station
                model.Add(assign[(i, j, p)] == 1).OnlyEnforceIf(indicator)
                model.Add(assign[(i, j, p)] == 0).OnlyEnforceIf(indicator.Not())

                # Set penalty value based on indicator
                model.Add(pen == weight).OnlyEnforceIf(indicator)
                model.Add(pen == 0).OnlyEnforceIf(indicator.Not())

                penalties.append(pen)

        logger.info(f"Added {len(penalties)} lookback-any penalties for period {current_period}")
        return penalties
    except Exception as e:
        logger.error(f"Error applying lookback-any penalties: {str(e)}")
        # Re-raise the exception to make failures visible
        raise


@rule_metadata(uses=["model", "assign", "employees", "workstations", "current_period", "start_date", "lookback", "employee_history_repo"])
def add_lookback_same_period_penalties(ctx: RuleContext):
    """
    Penalize employees who are assigned to the same workstation and period they worked in the recent past
    (within a lookback window).

    This rule encourages variety in an employee's assignments across days by penalizing
    having them work the same station at the same period they worked in the lookback window.

    Returns:
        List of penalty variables to be added to the objective function
    """
    import logging
    logger = logging.getLogger(__name__)

    model = ctx.model
    assign = ctx.assign
    employees = ctx.employees
    workstations = ctx.workstations
    current_period = ctx.current_period or 1  # Default to period 1 if not specified
    start_date = ctx.start_date
    lookback = max(ctx.lookback or 0, 0)  # Normalize lookback window
    repo = ctx.employee_history_repo

    # Convert to 0-indexed for internal use
    p = current_period - 1

    # Default weight for lookback-same penalties
    weight = 10000  # Higher weight for same period repeats

    if not start_date:
        logger.warning("Cannot apply lookback-same-period penalties: start_date is missing")
        return []

    if not repo:
        logger.warning("Cannot apply lookback-same-period penalties: employee_history_repo is missing")
        return []

    if lookback == 0:
        logger.info("Skipping lookback-same-period penalties: lookback window is zero")
        return []

    penalties = []
    # map station_id -> index j
    ws_idx = {ws.id: j for j, ws in enumerate(workstations)}

    from datetime import timedelta

    # Calculate lookback window
    lookback_start = start_date - timedelta(days=lookback)
    logger.info(f"Applying lookback-same-period penalties with {lookback} day window ({lookback_start} to {start_date})")

    try:
        for i, emp in enumerate(employees):
            # Get all distinct (station_id, work_period) pairs the employee worked in the lookback window
            station_period_pairs = repo.get_distinct_station_periods(emp.id, lookback_start, start_date)

            # Penalize assignments to (station, period) pairs the employee worked in the lookback window
            for station_id, period_num in station_period_pairs:
                j = ws_idx.get(station_id)
                # Only consider if the period matches the current period we're processing
                # period_num is 0-indexed, so compare with p (0-indexed current_period)
                if j is None or period_num != p:
                    continue

                pen = model.NewIntVar(0, weight, f"lookback_same_e{i}_w{j}_p{current_period}")
                indicator = model.NewBoolVar(f"lookback_same_indicator_e{i}_w{j}_p{current_period}")

                # indicator is true if employee is assigned to this station-period pair
                model.Add(assign[(i, j, p)] == 1).OnlyEnforceIf(indicator)
                model.Add(assign[(i, j, p)] == 0).OnlyEnforceIf(indicator.Not())

                # Set penalty value based on indicator
                model.Add(pen == weight).OnlyEnforceIf(indicator)
                model.Add(pen == 0).OnlyEnforceIf(indicator.Not())

                penalties.append(pen)

        logger.info(f"Added {len(penalties)} lookback-same-period penalties for period {current_period}")
        return penalties
    except Exception as e:
        logger.error(f"Error applying lookback-same-period penalties: {str(e)}")
        # Re-raise the exception to make failures visible
        raise


@rule_metadata(uses=["model", "assign", "employees", "workstations", "current_period", "start_date", "aro_data"])
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
    current_period = ctx.current_period or 1  # Default to period 1 if not specified
    start_date = ctx.start_date

    # Convert to 0-indexed for internal use
    p = current_period - 1

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
                pen = model.NewIntVar(0, weight, f"aro_reassign_e{i}_w{j}_p{current_period}")
                indicator = model.NewBoolVar(f"aro_reassign_indicator_e{i}_w{j}_p{current_period}")

                # indicator is true if ARO employee is assigned
                model.Add(assign[(i, j, p)] == 1).OnlyEnforceIf(indicator)
                model.Add(assign[(i, j, p)] == 0).OnlyEnforceIf(indicator.Not())

                # Set penalty value based on indicator
                model.Add(pen == weight).OnlyEnforceIf(indicator)
                model.Add(pen == 0).OnlyEnforceIf(indicator.Not())

                penalties.append(pen)

    return penalties
