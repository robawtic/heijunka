# domain/factories/schedule_factory.py
from typing import List, Dict, Optional, Any
from datetime import date
from domain.contexts.scheduling.entities.model import Schedule
from domain.contexts.scheduling.value_objects.schedule_period import SchedulePeriod
from domain.contexts.assignment.value_objects.work_assignment import WorkAssignment

class ScheduleFactory:
    @staticmethod
    def create_schedule(
        id: Optional[int] = None,
        team_id: int = 0,
        start_date: Optional[date] = None,
        periods_per_day: int = 4,
        status: str = "pending",
        call_ins: Optional[List[str]] = None,
        offline: Optional[Dict[str, List[int]]] = None,
        force_complete: bool = False,
        error_message: Optional[str] = None,
        task_id: Optional[str] = None,
        assignments: Optional[List[WorkAssignment]] = None
    ) -> Schedule:
        """
        Create a new Schedule entity with basic properties.

        Args:
            id: Optional schedule ID (None for new schedules)
            team_id: Team ID the schedule belongs to
            start_date: Start date of the schedule (defaults to today)
            periods_per_day: Number of periods per day
            status: Schedule status (e.g., "pending", "generated")
            call_ins: Optional list of employee names who called in (unavailable)
            offline: Optional dictionary mapping employee names to periods they're offline
            force_complete: Whether to force completion even if validation fails
            error_message: Optional error message
            task_id: Optional task ID for tracking
            assignments: Optional list of work assignments

        Returns:
            A new Schedule entity

        Raises:
            ValueError: If validation fails and force_complete is False
        """
        # Validate inputs before creating the schedule
        if team_id <= 0:
            raise ValueError("Team ID must be a positive integer")

        if periods_per_day <= 0:
            raise ValueError("Periods per day must be a positive integer")

        if not status:
            raise ValueError("Status must be a non-empty string")

        if start_date is None:
            start_date = date.today()

        # Create a basic schedule without assignments
        schedule = Schedule(
            id=id or 0,
            team_id=team_id,
            start_date=start_date,
            periods_per_day=periods_per_day,
            status=status,
            call_ins=call_ins or [],
            offline=offline or {},
            force_complete=force_complete,
            error_message=error_message,
            task_id=task_id,
            _assignments=[]  # Start with empty assignments
        )

        # Add assignments if provided
        if assignments:
            for assignment in assignments:
                schedule.add_assignment(assignment)

        # Validate the schedule
        try:
            schedule.validate()
        except ValueError as e:
            # If validation fails and force_complete is True, log the error but don't raise
            if force_complete:
                schedule.error_message = str(e)
            else:
                raise

        return schedule

    @staticmethod
    def create_daily_schedule(
        id: Optional[int] = None,
        team_id: int = 0,
        start_date: Optional[date] = None,
        periods_per_day: int = 4,
        status: str = "pending",
        call_ins: Optional[List[str]] = None,
        offline: Optional[Dict[str, List[int]]] = None
    ) -> Schedule:
        """
        Create a Schedule for a single day.

        Args:
            id: Optional schedule ID
            team_id: Team ID
            start_date: Date for the schedule (defaults to today)
            periods_per_day: Number of periods per day
            status: Schedule status
            call_ins: Optional list of employee names who called in
            offline: Optional dictionary of offline periods by employee

        Returns:
            A new Schedule entity for a single day

        Raises:
            ValueError: If validation fails
        """
        return ScheduleFactory.create_schedule(
            id=id,
            team_id=team_id,
            start_date=start_date,
            periods_per_day=periods_per_day,
            status=status,
            call_ins=call_ins,
            offline=offline
        )

    @staticmethod
    def create_schedule_with_assignments(
        id: Optional[int] = None,
        team_id: int = 0,
        start_date: Optional[date] = None,
        periods_per_day: int = 4,
        status: str = "generated",
        assignments: Optional[List[WorkAssignment]] = None
    ) -> Schedule:
        """
        Create a Schedule with pre-defined assignments.

        Args:
            id: Optional schedule ID
            team_id: Team ID
            start_date: Date for the schedule (defaults to today)
            periods_per_day: Number of periods per day
            status: Schedule status (default: "generated")
            assignments: Optional list of work assignments

        Returns:
            A new Schedule entity with the specified assignments

        Raises:
            ValueError: If validation fails
        """
        return ScheduleFactory.create_schedule(
            id=id,
            team_id=team_id,
            start_date=start_date,
            periods_per_day=periods_per_day,
            status=status,
            assignments=assignments
        )

    @staticmethod
    def create_from_model(model: Any, include_assignments: bool = True) -> Schedule:
        """
        Create a Schedule entity from a database model.

        Args:
            model: The database model to convert
            include_assignments: Whether to include assignments from work history entries

        Returns:
            A new Schedule entity populated with data from the model

        Raises:
            ValueError: If validation fails
        """
        # Parse JSON fields
        call_ins = model.call_ins if hasattr(model, 'call_ins') and model.call_ins else []
        offline = model.offline if hasattr(model, 'offline') and model.offline else {}

        # Create the schedule without assignments first
        schedule = ScheduleFactory.create_schedule(
            id=model.id,
            team_id=model.team_id,
            start_date=model.start_date,
            periods_per_day=model.periods_per_day,
            status=model.status,
            call_ins=call_ins,
            offline=offline,
            force_complete=model.force_complete if hasattr(model, 'force_complete') else False,
            error_message=model.error_message,
            task_id=model.task_id
        )

        # Add assignments if requested and available
        if include_assignments and hasattr(model, 'work_history_entries') and model.work_history_entries:
            from domain.factories.employee_factory import EmployeeFactory
            from domain.factories.workstation_factory import WorkstationFactory
            from domain.factories.assignment_factory import AssignmentFactory

            for entry in model.work_history_entries:
                if hasattr(entry, 'employee') and entry.employee and hasattr(entry, 'station') and entry.station:
                    # Convert models to domain entities
                    employee = EmployeeFactory.create_from_model(entry.employee)
                    workstation = WorkstationFactory.create_from_model(entry.station)

                    # Create period
                    period = SchedulePeriod(date=entry.worked_date, period=entry.work_period)

                    # Create and add assignment
                    assignment = AssignmentFactory.create_assignment(
                        employee=employee,
                        workstation=workstation,
                        period=period
                    )

                    # Use add_assignment method instead of directly manipulating _assignments
                    schedule.add_assignment(assignment)

        return schedule
