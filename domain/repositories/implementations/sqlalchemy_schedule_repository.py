from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import date

from domain.models.ScheduleModel import ScheduleModel
from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel
from domain.models.EmployeeModel import EmployeeModel
from domain.models.WorkstationModel import WorkstationModel
from domain.repositories.interfaces.schedule_repository import ScheduleRepository

class SqlAlchemyScheduleRepository(ScheduleRepository):
    def __init__(self, session: Session):
        self.session = session

    def create(self, team_id: int, start_date: date, days: int, periods_per_day: int, 
               call_ins: List[str] = None, offline: List[str] = None, 
               force_complete: bool = False) -> ScheduleModel:
        """Create a new schedule."""
        schedule = ScheduleModel(
            team_id=team_id,
            start_date=start_date,
            days=days,
            periods_per_day=periods_per_day,
            call_ins=call_ins,
            offline=offline,
            force_complete=force_complete,
            status="pending"
        )
        self.session.add(schedule)
        self.session.commit()
        self.session.refresh(schedule)
        return schedule

    def get_by_id(self, schedule_id: int) -> Optional[ScheduleModel]:
        """Get a schedule by ID."""
        return self.session.query(ScheduleModel).filter(ScheduleModel.id == schedule_id).options(
            joinedload(ScheduleModel.team),
            joinedload(ScheduleModel.work_history_entries).joinedload(EmployeeWorkHistoryModel.employee),
            joinedload(ScheduleModel.work_history_entries).joinedload(EmployeeWorkHistoryModel.station)
        ).first()

    def get_by_task_id(self, task_id: str) -> Optional[ScheduleModel]:
        """Get a schedule by task ID."""
        return self.session.query(ScheduleModel).filter(ScheduleModel.task_id == task_id).options(
            joinedload(ScheduleModel.team),
            joinedload(ScheduleModel.work_history_entries).joinedload(EmployeeWorkHistoryModel.employee),
            joinedload(ScheduleModel.work_history_entries).joinedload(EmployeeWorkHistoryModel.station)
        ).first()

    def update(self, schedule_id: int, **kwargs) -> Optional[ScheduleModel]:
        """Update a schedule."""
        schedule = self.get_by_id(schedule_id)
        if not schedule:
            return None

        for key, value in kwargs.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)

        self.session.commit()
        self.session.refresh(schedule)
        return schedule

    def get_all(self, team_id: Optional[int] = None, start_date: Optional[date] = None,
                end_date: Optional[date] = None, status: Optional[str] = None,
                skip: int = 0, limit: int = 100) -> List[ScheduleModel]:
        """Get all schedules with filtering and pagination."""
        query = self.session.query(ScheduleModel)

        # Apply filters at the database level
        if team_id is not None:
            query = query.filter(ScheduleModel.team_id == team_id)

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

        return query.order_by(ScheduleModel.created_at.desc()).offset(skip).limit(limit).all()

    def count(self, team_id: Optional[int] = None, start_date: Optional[date] = None,
              end_date: Optional[date] = None, status: Optional[str] = None) -> int:
        """Count schedules with filtering."""
        query = self.session.query(ScheduleModel)

        if team_id is not None:
            query = query.filter(ScheduleModel.team_id == team_id)

        if start_date is not None:
            query = query.filter(ScheduleModel.start_date >= start_date)

        if end_date is not None:
            query = query.filter(ScheduleModel.start_date <= end_date)

        if status is not None:
            query = query.filter(ScheduleModel.status == status)

        return query.count()
