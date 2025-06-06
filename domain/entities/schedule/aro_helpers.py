# heijunka/domain/entities/schedule/aro_helpers.py
from typing import List, Optional, Dict, Any, Tuple
import logging

from domain.value_objects.employee_availability import AvailabilityStatus
from domain.repositories.interfaces.team_aro_repository import TeamAroRepositoryInterface
from .model import Schedule

# Logger for this module
logger = logging.getLogger(__name__)

def request_aros_from_service(
    schedule: Schedule, 
    needed_count: int, 
    aro_service: "AROService", 
    aro_graph_service: "AROGraphService"
) -> Optional[List["Employee"]]:
    """
    Request AROs through the ARO service.

    Args:
        schedule: The schedule that needs AROs
        needed_count: Number of AROs needed
        aro_service: ARO service for finding and assigning AROs
        aro_graph_service: ARO graph service for optimizing ARO assignments

    Returns:
        List of employees including AROs if successful, empty list if no AROs found, None if service failed
    """
    if not aro_service or not aro_graph_service:
        logger.warning(f"Team {schedule.team_id}: No ARO service or graph service available")
        return []

    logger.info(f"Team {schedule.team_id}: Requesting {needed_count} AROs through ARO service")

    try:
        # Request AROs through the ARO service
        aro_assignments = aro_graph_service.assign_optimal_aros(
            understaffed_team_id=schedule.team_id,
            needed_aros=needed_count,
            assignment_date=schedule.start_date,
            period=None  # Full day assignment
        )

        if not aro_assignments:
            logger.warning(f"Team {schedule.team_id}: No ARO assignments returned from ARO service")
            return []

        logger.info(f"Team {schedule.team_id}: ARO service returned {len(aro_assignments)} ARO assignments")

        # Get updated employee list including AROs
        updated_employees = aro_service.get_employees_for_team_and_period(
            team_id=schedule.team_id,
            assignment_date=schedule.start_date,
            period=None
        )

        logger.info(f"Team {schedule.team_id}: Updated employee list has {len(updated_employees)} employees")
        return updated_employees

    except Exception as e:
        logger.error(f"Team {schedule.team_id}: Error using ARO service: {str(e)}")
        return None

def find_additional_employees_direct(
    schedule: Schedule, 
    needed_count: int, 
    workstations: List["Workstation"], 
    session: Any, 
    team_repository: "TeamRepositoryInterface", 
    prefetched_data: Optional[Dict[str, Any]] = None,
    team_aro_repository: Optional[TeamAroRepositoryInterface] = None
) -> List["Employee"]:
    """
    Find additional employees from other teams using the direct method.

    Args:
        schedule: The schedule that needs additional employees
        needed_count: Number of additional employees needed
        workstations: List of workstations that need to be staffed
        session: Database session for accessing employee data
        team_repository: Repository for retrieving team information
        prefetched_data: Optional dictionary containing prefetched data to avoid database queries
        team_aro_repository: Repository for retrieving TeamAro relationships

    Returns:
        List of additional employees found
    """
    if not team_repository or not session:
        logger.warning(f"Team {schedule.team_id}: No team_repository or session available for direct method")
        return []

    # First try to use TeamAro repository if available
    if team_aro_repository:
        logger.info(f"Team {schedule.team_id}: Using TeamAro repository to find additional employees")
        additional_employees = _find_employees_using_team_aro(
            schedule.team_id, needed_count, team_aro_repository, team_repository, prefetched_data
        )

        if additional_employees:
            logger.info(f"Team {schedule.team_id}: Found {len(additional_employees)} additional employees using TeamAro")
            return additional_employees
        else:
            logger.warning(f"Team {schedule.team_id}: No additional employees found using TeamAro, falling back to direct method")

    # Get the current team (use prefetched data if available)
    team = None
    if prefetched_data and 'teams_by_id' in prefetched_data and schedule.team_id in prefetched_data['teams_by_id']:
        team = prefetched_data['teams_by_id'][schedule.team_id]
    else:
        team = team_repository.get(schedule.team_id)

    if not team:
        logger.warning(f"Team {schedule.team_id}: Team not found for direct method")
        return []

    # Find employees from other teams who can work on this team's workstations
    additional_employees = _find_employees_from_other_teams(
        team, workstations, needed_count, session, team_repository, prefetched_data
    )

    if additional_employees:
        logger.info(f"Team {schedule.team_id}: Found {len(additional_employees)} additional employees using direct method")
    else:
        logger.warning(f"Team {schedule.team_id}: No additional employees found using direct method")

    return additional_employees

def check_employee_availability(
    schedule: Schedule, 
    employees: List["Employee"]
) -> Tuple[int, int, List["Employee"]]:
    """
    Check if there are enough employees to cover all workstations.

    Args:
        schedule: The schedule to check
        employees: List of employees available for scheduling

    Returns:
        Tuple containing:
        - Number of available non-ARO employees
        - Number of ARO employees
        - List of non-ARO employees
    """
    # Filter out AROs, called-in employees, and team leaders from the count
    aro_employees = [e for e in employees if any(
        av.status == AvailabilityStatus.ARO 
        for av in e.available_periods 
        if av.date == schedule.start_date
    )]

    # Filter out employees who are unavailable (called in) or team leaders
    non_aro_employees = [e for e in employees if 
        e.is_available_for_period(schedule.start_date, None) and  # Filter out called-in employees
        not e.has_role("Team Lead") and  # Filter out team leaders
        e.name not in (schedule.call_ins or []) and  # Filter out explicitly called-in employees
        not any(av.status == AvailabilityStatus.ARO for av in e.available_periods if av.date == schedule.start_date)  # Filter out AROs
    ]

    available_count = len(non_aro_employees)
    aro_count = len(aro_employees)

    logger.debug(
        f"Team {schedule.team_id}: {available_count} available employees, {aro_count} ARO employees, "
        f"{len(employees) - available_count - aro_count} unavailable employees"
    )

    return available_count, aro_count, non_aro_employees

def handle_force_complete(
    schedule: Schedule, 
    available_count: int, 
    needed_count: int
) -> bool:
    """
    Handle the case when force_complete is set but not enough employees are available.

    Args:
        schedule: The schedule to check
        available_count: Number of available employees
        needed_count: Number of workstations that need to be staffed

    Returns:
        True if we should continue with schedule generation, False if we should fail
    """
    if schedule.force_complete:
        # If force_complete is set, continue with the available employees
        logger.info(
            f"Team {schedule.team_id}: Not enough employees ({available_count}/{needed_count}), "
            f"but force_complete is set. Continuing with available employees."
        )
        schedule.set_status("partial")
        schedule.set_error_message(
            f"Not enough employees to cover all workstations. "
            f"Available: {available_count}, Needed: {needed_count}. "
            f"Generating partial schedule with force_complete=True."
        )
        return True
    else:
        # If force_complete is not set, fail
        logger.warning(
            f"Team {schedule.team_id}: Not enough employees ({available_count}/{needed_count}) "
            f"and force_complete is not set. Failing."
        )
        schedule.set_status("failed")
        schedule.set_error_message(
            f"Not enough employees to cover all workstations. "
            f"Available: {available_count}, Needed: {needed_count}. "
            f"Call-ins: {', '.join(schedule.call_ins) if schedule.call_ins else 'None'}. "
            f"Try reducing the number of call-ins or use --force-complete to generate a partial schedule."
        )
        return False

def handle_employee_shortage(
    schedule: Schedule, 
    employees: List["Employee"], 
    workstations: List["Workstation"],
    available_count: int, 
    session: Optional[Any] = None, 
    team_repository: Optional["TeamRepositoryInterface"] = None,
    aro_service: Optional["AROService"] = None, 
    aro_graph_service: Optional["AROGraphService"] = None, 
    prefetched_data: Optional[Dict[str, Any]] = None,
    team_aro_repository: Optional[TeamAroRepositoryInterface] = None
) -> Tuple[bool, List["Employee"]]:
    """
    Handle the case when there aren't enough employees to cover all workstations.

    Args:
        schedule: The schedule that needs additional employees
        employees: List of employees available for scheduling
        workstations: List of workstations to be staffed
        available_count: Number of available employees
        session: Database session for accessing work history data
        team_repository: Optional repository for retrieving team information
        aro_service: Optional ARO service for finding and assigning AROs
        aro_graph_service: Optional ARO graph service for optimizing ARO assignments
        prefetched_data: Optional dictionary containing prefetched data to avoid database queries
        team_aro_repository: Optional repository for retrieving TeamAro relationships

    Returns:
        Tuple containing:
        - Boolean indicating whether to continue with schedule generation
        - Updated list of employees (may include additional employees)
    """
    needed_count = len(workstations) - available_count

    # Set initial status
    schedule.set_status("pending_aro")
    schedule.set_error_message(f"Not enough employees to cover all workstations. "
                      f"Available: {available_count}, Needed: {len(workstations)}")

    logger.info(f"Team {schedule.team_id}: Not enough employees ({available_count}/{len(workstations)}), "
               f"need {needed_count} more")

    # Try to get additional employees
    updated_employees = employees.copy()

    # First try ARO service if available
    if aro_service and aro_graph_service:
        aro_employees = request_aros_from_service(schedule, needed_count, aro_service, aro_graph_service)
        if aro_employees is None:
            logger.warning(f"Team {schedule.team_id}: ARO service failed, falling back to direct method")
        elif aro_employees:  # Non-empty list means AROs were found
            logger.info(f"Team {schedule.team_id}: Using {len(aro_employees)} employees from ARO service")
            return True, aro_employees
        else:
            logger.info(f"Team {schedule.team_id}: No AROs found from ARO service, falling back to direct method")

    # If ARO service failed or isn't available, try direct method
    additional_employees = find_additional_employees_direct(
        schedule, needed_count, workstations, session, team_repository, prefetched_data, team_aro_repository
    )

    if additional_employees:
        # Add the additional employees to our list
        updated_employees.extend(additional_employees)
        return True, updated_employees

    # If we still don't have enough employees, check force_complete
    return handle_force_complete(schedule, available_count, len(workstations)), updated_employees

def _find_employees_using_team_aro(
    team_id: int,
    needed_count: int,
    team_aro_repository: TeamAroRepositoryInterface,
    team_repository: "TeamRepositoryInterface",
    prefetched_data: Optional[Dict[str, Any]] = None
) -> List["Employee"]:
    """
    Find employees who are designated as AROs for this team using the TeamAro repository.

    Args:
        team_id: The ID of the team that needs additional employees
        needed_count: The number of additional employees needed
        team_aro_repository: Repository for retrieving TeamAro relationships
        team_repository: Repository for retrieving team information
        prefetched_data: Optional dictionary containing prefetched data to avoid database queries

    Returns:
        List of employees who are designated as AROs for this team
    """
    additional_employees = []

    try:
        # Get all active TeamAro relationships for this team
        team_aros = team_aro_repository.get_by_team_id(team_id)
        active_team_aros = [aro for aro in team_aros if aro.is_active()]

        logger.info(f"Team {team_id}: Found {len(active_team_aros)} active TeamAro relationships")

        # Get the employees for each TeamAro relationship
        for team_aro in active_team_aros:
            if len(additional_employees) >= needed_count:
                break

            # Get the employee (use prefetched data if available)
            employee = None
            if prefetched_data and 'employees_by_id' in prefetched_data and team_aro.employee_id in prefetched_data['employees_by_id']:
                employee = prefetched_data['employees_by_id'][team_aro.employee_id]
            else:
                # Try to get the employee from the team repository
                employee = team_repository.get_employee(team_aro.employee_id)

            if employee:
                additional_employees.append(employee)
            else:
                logger.warning(f"Team {team_id}: Could not find employee with ID {team_aro.employee_id} for TeamAro relationship")

        return additional_employees
    except Exception as e:
        logger.error(f"Team {team_id}: Error finding employees using TeamAro: {str(e)}")
        return []

def _find_employees_from_other_teams(
    team: "Team", 
    workstations: List["Workstation"], 
    needed_count: int, 
    session: Any, 
    team_repository: "TeamRepositoryInterface", 
    prefetched_data: Optional[Dict[str, Any]] = None
) -> List["Employee"]:
    """
    Find employees from other teams who can work on this team's workstations.

    Args:
        team: The team that needs additional employees
        workstations: The workstations that need to be staffed
        needed_count: The number of additional employees needed
        session: Database session for accessing employee data
        team_repository: Repository for retrieving team information
        prefetched_data: Optional dictionary containing prefetched data to avoid database queries

    Returns:
        List of employees from other teams who can work on this team's workstations
    """
    additional_employees = []

    # Get all teams in the same department
    # Since Team doesn't have a direct department_id attribute, we need to get it through the team's group
    # Get the team's group first (use prefetched data if available)
    group = None
    if prefetched_data and 'groups_by_team' in prefetched_data and team.id in prefetched_data['groups_by_team']:
        group = prefetched_data['groups_by_team'][team.id]
    else:
        group = team_repository.get_group(team.id)

    if group and hasattr(group, 'department_id'):
        # Get all teams in the same department (use prefetched data if available)
        department_teams = []
        if prefetched_data and 'teams_by_department' in prefetched_data and group.department_id in prefetched_data['teams_by_department']:
            department_teams = prefetched_data['teams_by_department'][group.department_id]
        else:
            department_teams = team_repository.get_by_department_id(group.department_id)

        # Exclude the current team
        other_teams = [t for t in department_teams if t.id != team.id]
    else:
        # If we can't determine the department, just return an empty list
        other_teams = []

    # For each team, find employees who know the workstations we need
    for other_team in other_teams:
        # Skip if we already have enough employees
        if len(additional_employees) >= needed_count:
            break

        # Get employees from this team (use prefetched data if available)
        team_employees = []
        if prefetched_data and 'employees_by_team' in prefetched_data and other_team.id in prefetched_data['employees_by_team']:
            team_employees = prefetched_data['employees_by_team'][other_team.id]
        else:
            team_employees = team_repository.get_members(other_team.id)

        for employee in team_employees:
            # Skip if we already have enough employees
            if len(additional_employees) >= needed_count:
                break

            # Check if this employee knows any of our workstations
            for workstation in workstations:
                if employee.can_work(workstation):
                    # This employee can work on one of our workstations
                    additional_employees.append(employee)
                    break

    return additional_employees
