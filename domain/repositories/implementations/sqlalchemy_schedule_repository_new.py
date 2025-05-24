# heijunka/domain/repositories/implementations/sqlalchemy_schedule_repository_new.py
from contextlib import contextmanager
from typing import List, Optional, Generator, Dict
from datetime import date
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from domain.entities.schedule import Schedule
from domain.models.ScheduleModel import ScheduleModel
from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel
from domain.models.EmployeeModel import EmployeeModel
from domain.models.WorkstationModel import WorkstationModel
from domain.repositories.interfaces.schedule_repository_interface import ScheduleRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from domain.value_objects.work_assignment import WorkAssignment
from domain.value_objects.schedule_period import SchedulePeriod
from infrastructure.exceptions import RepositoryError


class SqlAlchemyScheduleRepository(BaseSqlAlchemyRepository[Schedule, ScheduleModel], ScheduleRepositoryInterface):
    def __init__(self, session: Session):
        super().__init__(session, ScheduleModel, Schedule)

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        try:
            yield self._session
            self._session.commit()
        except SQLAlchemyError as e:
            self._session.rollback()
            raise RepositoryError(f"Database operation failed: {str(e)}")
        except Exception as e:
            self._session.rollback()
            raise

    def get_by_task_id(self, task_id: str) -> Optional[Schedule]:
        """Get a schedule by task ID."""
        schedule_model = self._session.query(ScheduleModel).filter(
            ScheduleModel.task_id == task_id
        ).options(
            joinedload(ScheduleModel.team),
            joinedload(ScheduleModel.work_history_entries).joinedload(EmployeeWorkHistoryModel.employee),
            joinedload(ScheduleModel.work_history_entries).joinedload(EmployeeWorkHistoryModel.station)
        ).first()
        
        if not schedule_model:
            return None
            
        return self._to_domain(schedule_model)

    def get_by_team_id(self, team_id: int, start_date: Optional[date] = None,
                      end_date: Optional[date] = None, status: Optional[str] = None,
                      skip: int = 0, limit: int = 100) -> List[Schedule]:
        """Get all schedules for a specific team with filtering and pagination."""
        query = self._session.query(ScheduleModel).filter(
            ScheduleModel.team_id == team_id
        )
        
        if start_date is not None:
            query = query.filter(ScheduleModel.start_date >= start_date)
            
        if end_date is not None:
            query = query.filter(ScheduleModel.start_date <= end_date)
            
        if status is not None:
            query = query.filter(ScheduleModel.status == status)
            
        # Use eager loading to avoid N+1 queries
        query = query.options(
            joinedload(ScheduleModel.team),
            joinedload(ScheduleModel.work_history_entries).joinedload(EmployeeWorkHistoryModel.employee),
            joinedload(ScheduleModel.work_history_entries).joinedload(EmployeeWorkHistoryModel.station)
        )
        
        schedule_models = query.order_by(ScheduleModel.created_at.desc()).offset(skip).limit(limit).all()
        return [self._to_domain(model) for model in schedule_models]

    def create_schedule(self, team_id: int, start_date: date, days: int, periods_per_day: int, 
                       call_ins: List[str] = None, offline: List[str] = None, 
                       force_complete: bool = False) -> Schedule:
        """Create a new schedule."""
        # Parse offline parameter to convert to the format expected by the Schedule entity
        offline_dict = {}
        if offline:
            for offline_str in offline:
                parts = offline_str.split(':')
                if len(parts) == 2:
                    emp_name, periods_str = parts
                    periods = [int(p) for p in periods_str.split(',')]
                    offline_dict[emp_name] = periods
        
        # Create a new Schedule entity
        schedule = Schedule(
            id=0,  # Will be set by the database
            team_id=team_id,
            start_date=start_date,
            days=days,
            periods_per_day=periods_per_day,
            call_ins=call_ins,
            offline=offline_dict,
            force_complete=force_complete,
            status="pending"
        )
        
        # Add the schedule to the database
        return self.add(schedule)

    def update_status(self, schedule_id: int, status: str, error_message: Optional[str] = None) -> Optional[Schedule]:
        """Update the status of a schedule."""
        schedule = self.get_by_id(schedule_id)
        if not schedule:
            return None
            
        schedule.set_status(status)
        if error_message is not None:
            schedule.set_error_message(error_message)
            
        return self.update(schedule)

    def count(self, team_id: Optional[int] = None, start_date: Optional[date] = None,
             end_date: Optional[date] = None, status: Optional[str] = None) -> int:
        """Count schedules with filtering."""
        query = self._session.query(ScheduleModel)
        
        if team_id is not None:
            query = query.filter(ScheduleModel.team_id == team_id)
            
        if start_date is not None:
            query = query.filter(ScheduleModel.start_date >= start_date)
            
        if end_date is not None:
            query = query.filter(ScheduleModel.start_date <= end_date)
            
        if status is not None:
            query = query.filter(ScheduleModel.status == status)
            
        return query.count()

    def _to_domain(self, model: ScheduleModel) -> Schedule:
        """Convert a ScheduleModel to a Schedule domain entity."""
        # Parse offline parameter
        offline_dict = {}
        if model.offline:
            for offline_str in model.offline:
                parts = offline_str.split(':')
                if len(parts) == 2:
                    emp_name, periods_str = parts
                    periods = [int(p) for p in periods_str.split(',')]
                    offline_dict[emp_name] = periods
        
        # Create the Schedule entity
        schedule = Schedule(
            id=model.id,
            team_id=model.team_id,
            start_date=model.start_date,
            days=model.days,
            periods_per_day=model.periods_per_day,
            call_ins=model.call_ins,
            offline=offline_dict,
            force_complete=model.force_complete,
            status=model.status,
            error_message=model.error_message,
            task_id=model.task_id
        )
        
        # Add work assignments
        if model.work_history_entries:
            for entry in model.work_history_entries:
                if entry.employee and entry.station:
                    period = SchedulePeriod(date=entry.worked_date, period=entry.work_period)
                    assignment = WorkAssignment(
                        employee=entry.employee.to_domain(),
                        workstation=entry.station.to_domain(),
                        period=period
                    )
                    schedule._assignments.append(assignment)
        
        return schedule

    def _to_model(self, entity: Schedule) -> ScheduleModel:
        """Convert a Schedule domain entity to a ScheduleModel."""
        # Convert offline dictionary to list of strings
        offline_list = []
        if entity.offline:
            for emp_name, periods in entity.offline.items():
                periods_str = ','.join(str(p) for p in periods)
                offline_list.append(f"{emp_name}:{periods_str}")
        
        # Create the ScheduleModel
        model = ScheduleModel(
            id=entity.id,
            team_id=entity.team_id,
            start_date=entity.start_date,
            days=entity.days,
            periods_per_day=entity.periods_per_day,
            call_ins=entity.call_ins,
            offline=offline_list,
            force_complete=entity.force_complete,
            status=entity.status,
            error_message=entity.error_message,
            task_id=entity.task_id
        )
        
        return model

    def _update_model(self, model: ScheduleModel, entity: Schedule) -> None:
        """Update a ScheduleModel with values from a Schedule domain entity."""
        # Convert offline dictionary to list of strings
        offline_list = []
        if entity.offline:
            for emp_name, periods in entity.offline.items():
                periods_str = ','.join(str(p) for p in periods)
                offline_list.append(f"{emp_name}:{periods_str}")
        
        # Update the ScheduleModel
        model.team_id = entity.team_id
        model.start_date = entity.start_date
        model.days = entity.days
        model.periods_per_day = entity.periods_per_day
        model.call_ins = entity.call_ins
        model.offline = offline_list
        model.force_complete = entity.force_complete
        model.status = entity.status
        model.error_message = entity.error_message
        model.task_id = entity.task_id
        
        # Note: We don't update work_history_entries here because that would be handled
        # by a separate repository for work history entries