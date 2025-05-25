# heijunka/domain/services/schedule_service.py
from typing import List, Dict, Set, Optional, Tuple, Any
from datetime import date, timedelta

from ortools.sat.python import cp_model

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment
from domain.value_objects.schedule_constraint import ScheduleConstraint, ConstraintType
from domain.events import AssignmentCreated
from domain.rules.context import RuleContext


class ScheduleService:
    def __init__(self, constraints: List[ScheduleConstraint] = None):
        self.constraints = constraints or []

    def assign_employee(self, employee: Employee, workstation: Workstation,
                        period: SchedulePeriod, schedule_id: int = None) -> WorkAssignment:
        """
        Assign an employee to a workstation for a specific period

        This method delegates to the Schedule entity's create_assignment method.
        If no schedule_id is provided, a temporary schedule is created.

        Args:
            employee: The employee to assign
            workstation: The workstation to assign the employee to
            period: The period for the assignment
            schedule_id: Optional ID of an existing schedule

        Returns:
            The created work assignment

        Raises:
            ValueError: If the assignment is invalid
        """
        # If a schedule_id is provided, load the schedule from the repository
        # In a real implementation, this would be done via a repository
        if schedule_id:
            # This is a placeholder, would be retrieved from a repository
            from domain.entities.schedule import Schedule
            schedule = Schedule(
                id=schedule_id,
                team_id=1,  # Placeholder
                start_date=period.date,
                periods_per_day=4,
                status="active"
            )
        else:
            # Create a temporary schedule
            from domain.entities.schedule import Schedule
            schedule = Schedule(
                id=1,  # Using a valid ID for now, would be set by the repository in a real implementation
                team_id=1,  # Placeholder
                start_date=period.date,
                periods_per_day=4,
                status="temporary"
            )

        # Use the Schedule entity's create_assignment method
        return schedule.create_assignment(employee, workstation, period)

    def generate_schedule(self, employees: List[Employee], workstations: List[Workstation],
                          start_date: date, periods_per_day: int,
                          team_name: str, call_ins: List[str] = None, offline: List[str] = None, 
                          force_complete: bool = False, session=None) -> List[WorkAssignment]:
        """
        Generate a schedule for the given employees, workstations, and time period

        This method orchestrates the schedule generation process by:
        1. Creating a Schedule entity
        2. Setting up the necessary parameters
        3. Delegating the actual generation to the Schedule entity
        4. Returning the generated assignments

        Args:
            employees: List of employees to schedule
            workstations: List of workstations to assign employees to
            start_date: The start date of the schedule
            periods_per_day: Number of periods per day
            team_name: Name of the team to generate the schedule for
            call_ins: List of employee names who called in (unavailable)
            offline: List of strings in format "employee:periods" specifying which employees are offline for which periods
            force_complete: Whether to force completion of the schedule
            session: Database session for accessing work history data

        Returns:
            List of work assignments
        """
        # Parse offline parameter to convert to the format expected by the Schedule entity
        offline_dict = {}
        if offline:
            for offline_str in offline:
                parts = offline_str.split(':')
                if len(parts) == 2:
                    emp_name, periods_str = parts
                    periods = [int(p) for p in periods_str.split(',')]
                    offline_dict[emp_name] = periods

        # Get team_id from team_name (in a real implementation, this would be done via a repository)
        team_id = 1  # Placeholder, would be retrieved from a repository

        # Create a Schedule entity
        from domain.entities.schedule import Schedule
        schedule = Schedule(
            id=1,  # Using a valid ID for now, would be set by the repository in a real implementation
            team_id=team_id,
            start_date=start_date,
            periods_per_day=periods_per_day,
            status="pending",
            call_ins=call_ins or [],
            offline=offline_dict,
            force_complete=force_complete
        )

        # Create a rule context (optional, could be done inside the Schedule entity)
        from domain.rules.registry import create_context_for_team

        # Generate assignments using the Schedule entity
        success = schedule.generate_assignments(employees, workstations)

        if success:
            print(f"Generated {len(schedule.assignments)} assignments")
            return schedule.assignments
        else:
            print(f"No solution found. Error: {schedule.error_message}")
            return []

    def add_constraint(self, constraint: ScheduleConstraint):
        """Add a constraint to the schedule service"""
        self.constraints.append(constraint)
