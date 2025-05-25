# domain/factories/schedule_factory.py
from typing import List, Dict, Optional, Any
from datetime import date
from domain.entities.schedule import Schedule
from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment

class ScheduleFactory:
    @staticmethod
    def create_schedule(
        id: Optional[int] = None,
        team_id: int = 0,
        start_date: date = None,
        periods_per_day: int = 4,
        status: str = "pending",
        call_ins: List[str] = None,
        offline: Dict[str, List[int]] = None,
        force_complete: bool = False,
        error_message: Optional[str] = None,
        task_id: Optional[str] = None,
        assignments: List[WorkAssignment] = None
    ) -> Schedule:
        """Create a new Schedule entity with basic properties."""
        if start_date is None:
            start_date = date.today()
            
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
            _assignments=assignments or []
        )
        
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
        start_date: date = None,
        periods_per_day: int = 4,
        status: str = "pending",
        call_ins: List[str] = None,
        offline: Dict[str, List[int]] = None
    ) -> Schedule:
        """Create a Schedule for a single day."""
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
        start_date: date = None,
        periods_per_day: int = 4,
        status: str = "generated",
        assignments: List[WorkAssignment] = None
    ) -> Schedule:
        """Create a Schedule with pre-defined assignments."""
        schedule = ScheduleFactory.create_schedule(
            id=id,
            team_id=team_id,
            start_date=start_date,
            periods_per_day=periods_per_day,
            status=status,
            assignments=assignments
        )
        
        return schedule
    
    @staticmethod
    def create_from_model(model, include_assignments: bool = True) -> Schedule:
        """Create a Schedule entity from a database model."""
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
                    
                    schedule._assignments.append(assignment)
        
        return schedule