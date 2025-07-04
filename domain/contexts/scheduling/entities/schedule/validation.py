# heijunka/domain/contexts/scheduling/entities/schedule/validation.py
from typing import List
import logging

from .model import Schedule
from .events import ScheduleValidationFailed

# Logger for this module
logger = logging.getLogger(__name__)

def validate_basic_properties(schedule: Schedule) -> List[str]:
    """
    Validate basic schedule properties.

    Args:
        schedule: The schedule to validate.

    Returns:
        List of validation error messages
    """
    errors = []

    try:
        if not isinstance(schedule.team_id, int) or schedule.team_id <= 0:
            errors.append("Team ID must be a positive integer")
        if not isinstance(schedule.start_date, type(schedule.start_date)) or schedule.start_date is None:
            errors.append("Start date must be a date object")
        if not isinstance(schedule.periods_per_day, int) or schedule.periods_per_day <= 0:
            errors.append("Periods per day must be a positive integer")
        if not isinstance(schedule.status, str) or not schedule.status:
            errors.append("Status must be a non-empty string")
    except Exception as e:
        errors.append(f"Error validating basic properties: {str(e)}")

    return errors

def validate_assignment_overlaps(schedule: Schedule) -> List[str]:
    """
    Check for assignment overlaps (same employee assigned to multiple workstations in the same period).

    Args:
        schedule: The schedule to validate.

    Returns:
        List of validation error messages
    """
    errors = []

    try:
        # Dictionary to track employee assignments by date and period
        employee_assignments = {}

        for assignment in schedule._assignments:
            key = (assignment.employee.id, assignment.period.date, assignment.period.period)
            if key in employee_assignments:
                existing = employee_assignments[key]
                errors.append(
                    f"Employee {assignment.employee.name} (ID: {assignment.employee.id}) is assigned to multiple workstations "
                    f"({existing.workstation.name} and {assignment.workstation.name}) "
                    f"on {assignment.period.date} during period {assignment.period.period}"
                )
            else:
                employee_assignments[key] = assignment
    except Exception as e:
        errors.append(f"Error checking assignment overlaps: {str(e)}")

    return errors

def validate_employee_eligibility(schedule: Schedule) -> List[str]:
    """
    Validate employee eligibility/qualification for assigned workstations.

    Args:
        schedule: The schedule to validate.

    Returns:
        List of validation error messages
    """
    errors = []

    try:
        for assignment in schedule._assignments:
            # Check if employee is qualified for the workstation
            if not assignment.employee.can_work(assignment.workstation):
                errors.append(
                    f"Employee {assignment.employee.name} (ID: {assignment.employee.id}) is not qualified to work at "
                    f"workstation {assignment.workstation.name} (ID: {assignment.workstation.id})"
                )

            # Check if employee can handle workstation type (heavy, key skill, etc.)
            if not assignment.employee.can_handle_workstation_type(assignment.workstation):
                errors.append(
                    f"Employee {assignment.employee.name} (ID: {assignment.employee.id}) cannot handle workstation type "
                    f"for {assignment.workstation.name} (ID: {assignment.workstation.id})"
                )

            # Check if employee is qualified for the line type
            if not assignment.employee.is_qualified_for_line(assignment.workstation.line_type):
                errors.append(
                    f"Employee {assignment.employee.name} (ID: {assignment.employee.id}) is not qualified for line type "
                    f"{assignment.workstation.line_type} at workstation {assignment.workstation.name}"
                )

            # Check if employee is available for the assigned period
            if not assignment.employee.is_available_for_period(
                assignment.period.date, assignment.period.period
            ):
                errors.append(
                    f"Employee {assignment.employee.name} (ID: {assignment.employee.id}) is not available on "
                    f"{assignment.period.date} during period {assignment.period.period}"
                )
    except Exception as e:
        errors.append(f"Error checking employee eligibility: {str(e)}")

    return errors

def validate_date_ranges(schedule: Schedule) -> List[str]:
    """
    Validate date ranges and periods for assignments.

    Args:
        schedule: The schedule to validate.

    Returns:
        List of validation error messages
    """
    errors = []

    try:
        for assignment in schedule._assignments:
            # Check if assignment date is within schedule range
            if assignment.period.date < schedule.start_date or assignment.period.date > schedule.end_date:
                errors.append(
                    f"Assignment for employee {assignment.employee.name} at workstation {assignment.workstation.name} "
                    f"on {assignment.period.date} is outside the schedule date range "
                    f"({schedule.start_date} to {schedule.end_date})"
                )

            # Check if period is valid for this schedule
            if assignment.period.period < 1 or assignment.period.period > schedule.periods_per_day:
                errors.append(
                    f"Assignment for employee {assignment.employee.name} at workstation {assignment.workstation.name} "
                    f"has invalid period {assignment.period.period} (valid range: 1-{schedule.periods_per_day})"
                )
    except Exception as e:
        errors.append(f"Error checking date ranges and periods: {str(e)}")

    return errors

def validate(schedule: Schedule) -> bool:
    """
    Validates the schedule entity and its assignments.

    Checks:
    1. Basic schedule properties
    2. Assignment overlaps (same employee assigned to multiple workstations in the same period)
    3. Employee eligibility/qualification for assigned workstations
    4. Valid date ranges and periods for assignments

    Args:
        schedule: The schedule to validate.

    Returns:
        True if validation passes, False otherwise

    Raises:
        ValueError: If validation fails and force_complete is False
    """
    # Validate basic properties
    validation_errors = validate_basic_properties(schedule)

    # Skip assignment validations if there are no assignments
    if not schedule._assignments:
        if validation_errors:
            # Log validation errors
            for error in validation_errors:
                logger.warning(f"Team {schedule.team_id}: Validation error: {error}")

            # Register validation failure event
            schedule.register_domain_event(ScheduleValidationFailed(
                schedule_id=schedule.id,
                validation_errors=validation_errors
            ))

            # If force_complete is False, raise an error with all validation failures
            if not schedule.force_complete:
                raise ValueError(f"Schedule validation failed: {', '.join(validation_errors)}")
            return False
        return True

    # Validate assignments
    validation_errors.extend(validate_assignment_overlaps(schedule))
    validation_errors.extend(validate_employee_eligibility(schedule))
    validation_errors.extend(validate_date_ranges(schedule))

    if validation_errors:
        # Log validation errors
        for error in validation_errors:
            logger.warning(f"Team {schedule.team_id}: Validation error: {error}")

        # Register validation failure event
        schedule.register_domain_event(ScheduleValidationFailed(
            schedule_id=schedule.id,
            validation_errors=validation_errors
        ))

        # If force_complete is False, raise an error with all validation failures
        if not schedule.force_complete:
            raise ValueError(f"Schedule validation failed: {', '.join(validation_errors)}")
        return False

    return True