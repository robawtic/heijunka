# heijunka/domain/services/schedule_generation.py
from typing import List, Dict, Optional, Any, Tuple
import logging

from ortools.sat.python import cp_model

from domain.entities.schedule.model import Schedule
from domain.entities.schedule.validation import validate
from domain.entities.schedule.aro_helpers import check_employee_availability, handle_employee_shortage
from domain.value_objects.schedule_period import SchedulePeriod
from domain.entities.schedule.events import ScheduleValidationFailed
from domain.repositories.interfaces.team_aro_repository import TeamAroRepositoryInterface

# Logger for this module
logger = logging.getLogger(__name__)

def setup_constraint_model(
    schedule: Schedule, 
    employees: List["Employee"], 
    workstations: List["Workstation"],
    rule_context: Optional["RuleContext"] = None, 
    session: Optional[Any] = None, 
    team_repository: Optional["TeamRepositoryInterface"] = None, 
    prefetched_data: Optional[Dict[str, Any]] = None
) -> Tuple[Any, Dict[Tuple[int, int, int], Any], str, "RuleContext"]:
    """
    Set up the constraint model and define decision variables.

    Args:
        schedule: The schedule to generate assignments for
        employees: List of employees available for scheduling
        workstations: List of workstations to be staffed
        rule_context: Optional pre-configured rule context
        session: Database session for accessing work history data
        team_repository: Optional repository for retrieving team information
        prefetched_data: Optional dictionary containing prefetched data to avoid database queries

    Returns:
        Tuple containing:
        - CP model
        - Dictionary of decision variables
        - Team name
        - Rule context
    """
    from domain.rules.registry import create_context_for_team

    # Create CP model
    model = cp_model.CpModel()

    # Define decision variables
    assign = {}
    for e, employee in enumerate(employees):
        for w, workstation in enumerate(workstations):
            for p in range(schedule.periods_per_day):
                assign[(e, w, p)] = model.NewBoolVar(
                    f'assign_e{e}_w{w}_p{p}')

    # Parse offline parameter
    employee_offline_periods = {}
    if schedule.offline:
        for emp_name, periods in schedule.offline.items():
            employee_offline_periods[emp_name] = set(periods)

    # Get team name from team_id
    team_name = "default"  # Default if no repository is provided
    if schedule.team_id:
        # Try to get team from prefetched data first
        team = None
        if prefetched_data and 'teams_by_id' in prefetched_data and schedule.team_id in prefetched_data['teams_by_id']:
            team = prefetched_data['teams_by_id'][schedule.team_id]
        elif team_repository:
            team = team_repository.get(schedule.team_id)

        if team:
            team_name = team.name.lower()

    # Create or use rule context
    if rule_context is None:
        ctx = create_context_for_team(
            team_name=team_name,
            model=model,
            assign=assign,
            employees=employees,
            workstations=workstations,
            periods=schedule.periods_per_day,
            start_date=schedule.start_date,
            lookback=3,  # DEFAULT_LOOKBACK_DAYS
            session=session,
            call_ins=schedule.call_ins,
            employee_offline_periods=employee_offline_periods,
            backup_idx=next((i for i, e in enumerate(employees) if e.has_role("Backup")), None),
            offline_periods={},  # No offline periods for now
            scheduled=[]  # No scheduled assignments for now
        )
    else:
        ctx = rule_context

    return model, assign, team_name, ctx

def apply_rules(
    schedule: Schedule, 
    model: Any, 
    ctx: "RuleContext", 
    team_name: str
) -> Any:
    """
    Apply rules and set up objective function.

    Args:
        schedule: The schedule to generate assignments for
        model: CP model
        ctx: Rule context
        team_name: Team name

    Returns:
        Updated CP model
    """
    from domain.rules.registry import get_rules_for_team

    # Rule weights for different rule types
    RULE_WEIGHTS = {
        # Current soft rules
        "add_same_day_repeat_penalties": 100,
        "add_lookback_any_period_penalties": 1000,
        "add_lookback_same_period_penalties": 500,

        # Backward compatibility
        "add_rotation_penalties": 1000
    }

    # Apply rules
    rules = get_rules_for_team(team_name)
    objective_terms = []

    for rule in rules:
        result = rule(ctx)
        # If the rule returns penalty variables, add them to the objective
        if isinstance(result, list) and result:
            # Get the weight for this rule (default to 10 if not specified)
            weight = RULE_WEIGHTS.get(rule.__name__, 10)
            for penalty in result:
                objective_terms.append(weight * penalty)

    # Set objective function
    if objective_terms:
        model.Minimize(sum(objective_terms))

    return model

def solve_model(schedule: Schedule, model, time_limit: Optional[float] = None) -> Tuple[int, Any]:
    """
    Solve the constraint model.

    Args:
        schedule: The schedule to generate assignments for
        model: CP model
        time_limit: Optional custom time limit (overrides default)

    Returns:
        Tuple containing:
        - Status code
        - Solver
    """
    # Constants
    DEFAULT_SOLVER_TIME_LIMIT = 3.0  # 30/10 seconds
    MAX_SOLVER_TIME_LIMIT = 300.0    # 5 minutes

    # Solve the model
    solver = cp_model.CpSolver()

    # Use provided time_limit, or default to DEFAULT_SOLVER_TIME_LIMIT
    # but never exceed MAX_SOLVER_TIME_LIMIT
    effective_time_limit = min(
        time_limit or DEFAULT_SOLVER_TIME_LIMIT,
        MAX_SOLVER_TIME_LIMIT
    )

    solver.parameters.max_time_in_seconds = effective_time_limit
    logger.debug(f"Setting solver time limit to {effective_time_limit} seconds")

    status = solver.Solve(model)

    return status, solver

def process_solution(
    schedule: Schedule, 
    status: int, 
    solver: Any, 
    assign: Dict[Tuple[int, int, int], Any], 
    employees: List["Employee"], 
    workstations: List["Workstation"]
) -> bool:
    """
    Process the solution and create assignments.

    Args:
        schedule: The schedule to generate assignments for
        status: Status code from solver
        solver: CP solver
        assign: Dictionary of decision variables
        employees: List of employees available for scheduling
        workstations: List of workstations to be staffed

    Returns:
        True if assignments were successfully generated, False otherwise
    """
    from domain.entities.schedule.assignment import create_and_add_assignment

    # Extract results if solution found
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        # Extract assignments
        current_date = schedule.start_date
        for period in range(schedule.periods_per_day):
            for emp_idx, employee in enumerate(employees):
                for ws_idx, workstation in enumerate(workstations):
                    if solver.Value(assign[(emp_idx, ws_idx, period)]) == 1:
                        # Create a SchedulePeriod for this assignment
                        schedule_period = SchedulePeriod(date=current_date, period=period + 1)

                        # Create and add assignment
                        try:
                            create_and_add_assignment(schedule, employee, workstation, schedule_period)
                        except ValueError as e:
                            # Log error but continue with other assignments
                            logger.warning(f"Team {schedule.team_id}: Error creating assignment: {str(e)}")
                            schedule.register_domain_event(ScheduleValidationFailed(
                                schedule_id=schedule.id,
                                validation_errors=[str(e)]
                            ))

        # Update schedule status
        schedule.set_status("generated")
        logger.info(f"Team {schedule.team_id}: Generated {len(schedule._assignments)} assignments")
        return True
    else:
        schedule.set_status("failed")
        # Get more details about why it failed
        status_name = solver.StatusName(status)
        employee_count = len(employees)
        workstation_count = len(workstations)
        call_ins_count = len(schedule.call_ins) if schedule.call_ins else 0

        error_msg = (
            f"No solution found. Status: {status_name}. "
            f"Available employees: {employee_count}, Workstations: {workstation_count}. "
            f"Call-ins: {call_ins_count}. "
            f"Try reducing the number of call-ins or use --force-complete to generate a partial schedule."
        )

        schedule.set_error_message(error_msg)
        logger.warning(f"Team {schedule.team_id}: No solution found. Status: {solver.StatusName(status)}")
        return False

def generate_assignments(
    schedule: Schedule, 
    employees: List["Employee"], 
    workstations: List["Workstation"],
    rule_context: Optional[Any] = None, 
    session=None, 
    team_repository=None,
    aro_service=None, 
    aro_graph_service=None, 
    prefetched_data: Optional[Dict] = None,
    team_aro_repository: Optional[TeamAroRepositoryInterface] = None
) -> bool:
    """
    Generate assignments for this schedule using constraint programming.

    Args:
        schedule: The schedule to generate assignments for
        employees: List of employees available for scheduling
        workstations: List of workstations to be staffed
        rule_context: Optional pre-configured rule context
        session: Database session for accessing work history data
        team_repository: Optional repository for retrieving team information
        aro_service: Optional ARO service for finding and assigning AROs
        aro_graph_service: Optional ARO graph service for optimizing ARO assignments
        prefetched_data: Optional dictionary containing prefetched data to avoid database queries
        team_aro_repository: Optional repository for retrieving TeamAro relationships

    Returns:
        True if assignments were successfully generated, False otherwise
    """
    # Clear existing assignments if any
    schedule._assignments = []

    # Check if we have enough employees to cover all workstations
    available_count, aro_count, non_aro_employees = check_employee_availability(schedule, employees)

    # Handle employee shortage if needed
    if available_count < len(workstations):
        continue_generation, employees = handle_employee_shortage(
            schedule, employees, workstations, available_count, session, team_repository,
            aro_service, aro_graph_service, prefetched_data, team_aro_repository
        )

        if not continue_generation:
            return False

    # Setup the constraint model
    model, assign, team_name, ctx = setup_constraint_model(
        schedule, employees, workstations, rule_context, session, team_repository, prefetched_data
    )

    # Apply rules and set up objective function
    model = apply_rules(schedule, model, ctx, team_name)

    # Solve the model
    status, solver = solve_model(schedule, model)

    # Process the solution
    return process_solution(schedule, status, solver, assign, employees, workstations)
