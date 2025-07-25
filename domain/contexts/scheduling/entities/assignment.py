# heijunka/domain/entities/schedule/assignment.py
from typing import List, TYPE_CHECKING

from domain.contexts.scheduling.value_objects.schedule_period import SchedulePeriod
from domain.contexts.assignment.value_objects.work_assignment import WorkAssignment
from .events import AssignmentAdded, AssignmentRemoved

if TYPE_CHECKING:
    from .model import Schedule

def add_assignment(schedule: "Schedule", assignment: WorkAssignment) -> bool:
    """
    Add an assignment to the schedule.

    Args:
        schedule: The schedule to add the assignment to.
        assignment: The assignment to add.

    Returns:
        True if the assignment was added, False if it was already in the schedule.

    Raises:
        ValueError: If the assignment is invalid.
    """
    if not isinstance(assignment, WorkAssignment):
        raise ValueError("assignment must be a WorkAssignment instance")

    # Check if this assignment already exists
    for existing in schedule._assignments:
        if (existing.employee.id == assignment.employee.id and
            existing.workstation.id == assignment.workstation.id and
            existing.period.date == assignment.period.date and
            existing.period.period == assignment.period.period):
            return False

    # Add the assignment to the schedule
    schedule._assignments.append(assignment)

    # Register the domain event
    schedule.register_domain_event(AssignmentAdded(
        schedule_id=schedule.id,
        employee_id=assignment.employee.id,
        workstation_id=assignment.workstation.id,
        period=assignment.period
    ))

    return True

def remove_assignment(schedule: "Schedule", employee_id: int, workstation_id: int, period: SchedulePeriod) -> bool:
    """
    Remove an assignment from the schedule.

    Args:
        schedule: The schedule to remove the assignment from.
        employee_id: The ID of the employee.
        workstation_id: The ID of the workstation.
        period: The period of the assignment.

    Returns:
        True if the assignment was removed, False if it wasn't in the schedule.
    """
    # Find the assignment in the schedule
    for i, assignment in enumerate(schedule._assignments):
        if (assignment.employee.id == employee_id and
            assignment.workstation.id == workstation_id and
            assignment.period.date == period.date and
            assignment.period.period == period.period):
            # Remove the assignment from the schedule
            schedule._assignments.pop(i)

            # Register the domain event
            schedule.register_domain_event(AssignmentRemoved(
                schedule_id=schedule.id,
                employee_id=employee_id,
                workstation_id=workstation_id,
                period=period
            ))

            return True

    return False

def create_and_add_assignment(schedule: "Schedule", employee: "Employee", workstation: "Workstation", 
                             period: SchedulePeriod) -> WorkAssignment:
    """
    Create and add a new assignment to the schedule.

    Args:
        schedule: The schedule to add the assignment to.
        employee: The employee to assign
        workstation: The workstation to assign the employee to
        period: The period for the assignment

    Returns:
        The created work assignment

    Raises:
        ValueError: If the assignment is invalid
    """
    # Validate employee can work at this workstation
    if not employee.can_work(workstation):
        raise ValueError(f"{employee.name} cannot work at {workstation.name}")

    # Validate employee is available for this period
    if not employee.is_available_for_period(period.date, period.period):
        raise ValueError(f"{employee.name} is not available on {period}")

    # Validate period is within schedule range
    if period.date < schedule.start_date or period.date > schedule.end_date:
        raise ValueError(f"Period {period} is outside schedule date range ({schedule.start_date} to {schedule.end_date})")

    # Validate period number is valid
    if period.period < 1 or period.period > schedule.periods_per_day:
        raise ValueError(f"Period {period.period} is outside valid range (1-{schedule.periods_per_day})")

    # Create the assignment
    assignment = WorkAssignment(
        employee=employee,
        workstation=workstation,
        period=period
    )

    # Add to schedule
    add_assignment(schedule, assignment)

    return assignment

def get_assignments_for_date(schedule: "Schedule", date_obj: "date") -> List[WorkAssignment]:
    """
    Get all assignments for a specific date.

    Args:
        schedule: The schedule to get assignments from.
        date_obj: The date to get assignments for.

    Returns:
        A list of assignments for the date.
    """
    return [a for a in schedule._assignments if a.period.date == date_obj]

def get_assignments_for_employee(schedule: "Schedule", employee_id: int) -> List[WorkAssignment]:
    """
    Get all assignments for a specific employee.

    Args:
        schedule: The schedule to get assignments from.
        employee_id: The ID of the employee.

    Returns:
        A list of assignments for the employee.
    """
    return [a for a in schedule._assignments if a.employee.id == employee_id]

def get_assignments_for_workstation(schedule: "Schedule", workstation_id: int) -> List[WorkAssignment]:
    """
    Get all assignments for a specific workstation.

    Args:
        schedule: The schedule to get assignments from.
        workstation_id: The ID of the workstation.

    Returns:
        A list of assignments for the workstation.
    """
    return [a for a in schedule._assignments if a.workstation.id == workstation_id]
