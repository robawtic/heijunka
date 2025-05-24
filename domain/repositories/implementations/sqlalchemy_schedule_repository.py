from typing import List, Optional, Dict, Any
from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from domain.entities.schedule import Schedule
from domain.models.ScheduleModel import ScheduleModel
from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel
from domain.models.EmployeeModel import EmployeeModel
from domain.models.WorkstationModel import WorkstationModel
from domain.models.TeamModel import TeamModel
from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment
from domain.repositories.interfaces.schedule_repository_interface import ScheduleRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError


class SqlAlchemyScheduleRepository(BaseSqlAlchemyRepository[Schedule, ScheduleModel], ScheduleRepositoryInterface):
    """
    SQLAlchemy implementation of the ScheduleRepositoryInterface.
    """

    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session: The SQLAlchemy session to use for database operations.
        """
        super().__init__(session, ScheduleModel, Schedule)

    def get_by_task_id(self, task_id: str) -> Optional[Schedule]:
        """
        Get a schedule by its task ID.

        Args:
            task_id: The task ID of the schedule.

        Returns:
            The schedule if found, None otherwise.
        """
        try:
            model = self._session.query(ScheduleModel).filter(ScheduleModel.task_id == task_id).options(
                joinedload(ScheduleModel.team),
                joinedload(ScheduleModel.work_history_entries).joinedload(EmployeeWorkHistoryModel.employee),
                joinedload(ScheduleModel.work_history_entries).joinedload(EmployeeWorkHistoryModel.station)
            ).first()

            if model is None:
                return None

            return self._to_domain(model)
        except SQLAlchemyError as e:
            raise RepositoryError(f"Database error while retrieving schedule by task ID: {str(e)}")

    def get_by_team_id(self, team_id: int, start_date: Optional[date] = None,
                       end_date: Optional[date] = None, status: Optional[str] = None,
                       skip: int = 0, limit: int = 100) -> List[Schedule]:
        """
        Get all schedules for a specific team with filtering and pagination.

        Args:
            team_id: The ID of the team.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            status: Optional status filter.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of schedules for the team.
        """
        try:
            query = self._session.query(ScheduleModel).filter(ScheduleModel.team_id == team_id)

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

            models = query.order_by(ScheduleModel.created_at.desc()).offset(skip).limit(limit).all()

            return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Database error while retrieving schedules by team ID: {str(e)}")

    def create_schedule(self, team_id: int, start_date: date, periods_per_day: int,
                        call_ins: List[str] = None, offline: List[str] = None,
                        force_complete: bool = False) -> Schedule:
        """
        Create a new schedule.

        Args:
            team_id: The ID of the team.
            start_date: The start date of the schedule.
            periods_per_day: Number of periods per day.
            call_ins: List of employee names who called in (unavailable).
            offline: List of strings in format "employee:periods" specifying which employees are offline for which periods.
            force_complete: Whether to force completion of the schedule.

        Returns:
            The created schedule.
        """
        try:
            # Parse offline parameter to convert to the format expected by the Schedule entity
            offline_dict = {}
            if offline:
                for offline_str in offline:
                    parts = offline_str.split(':')
                    if len(parts) == 2:
                        emp_name, periods_str = parts
                        periods = [int(p) for p in periods_str.split(',')]
                        offline_dict[emp_name] = periods

            # Create a new ScheduleModel
            model = ScheduleModel(
                team_id=team_id,
                start_date=start_date,
                periods_per_day=periods_per_day,
                call_ins=call_ins,
                offline=offline_dict,
                force_complete=force_complete,
                status="pending"
            )

            self._session.add(model)
            self._session.commit()
            self._session.refresh(model)

            # Convert to domain entity
            return self._to_domain(model)
        except SQLAlchemyError as e:
            self._session.rollback()
            raise RepositoryError(f"Database error while creating schedule: {str(e)}")

    def update_status(self, schedule_id: int, status: str, error_message: Optional[str] = None) -> Optional[Schedule]:
        """
        Update the status of a schedule.

        Args:
            schedule_id: The ID of the schedule.
            status: The new status.
            error_message: Optional error message.

        Returns:
            The updated schedule if found, None otherwise.
        """
        try:
            model = self._session.query(ScheduleModel).get(schedule_id)
            if model is None:
                return None

            model.status = status
            if error_message is not None:
                model.error_message = error_message

            self._session.commit()
            self._session.refresh(model)

            return self._to_domain(model)
        except SQLAlchemyError as e:
            self._session.rollback()
            raise RepositoryError(f"Database error while updating schedule status: {str(e)}")

    def count(self, team_id: Optional[int] = None, start_date: Optional[date] = None,
              end_date: Optional[date] = None, status: Optional[str] = None) -> int:
        """
        Count schedules with filtering.

        Args:
            team_id: Optional team ID filter.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            status: Optional status filter.

        Returns:
            The number of schedules matching the filters.
        """
        try:
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
        except SQLAlchemyError as e:
            raise RepositoryError(f"Database error while counting schedules: {str(e)}")

    def _to_domain(self, model: ScheduleModel) -> Schedule:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        # Create the Schedule entity
        schedule = Schedule(
            id=model.id,
            team_id=model.team_id,
            start_date=model.start_date,
            periods_per_day=model.periods_per_day,
            status=model.status,
            call_ins=model.call_ins or [],
            offline=model.offline or {},
            force_complete=model.force_complete,
            error_message=model.error_message,
            task_id=model.task_id
        )

        # Add assignments if available
        if model.work_history_entries:
            for entry in model.work_history_entries:
                # Skip entries that are not generated by the scheduler or are temporary
                if not entry.is_generated or entry.is_temporary:
                    continue

                # Get employee and workstation
                employee_model = entry.employee
                workstation_model = entry.station

                if not employee_model or not workstation_model:
                    continue

                # Convert to domain entities
                employee = employee_model.to_domain()
                workstation = workstation_model.to_domain()

                # Create schedule period
                period = SchedulePeriod(date=entry.worked_date, period=entry.work_period)

                # Create work assignment
                assignment = WorkAssignment(
                    employee=employee,
                    workstation=workstation,
                    period=period
                )

                # Add to schedule
                schedule._assignments.append(assignment)

        return schedule

    def _to_model(self, entity: Schedule) -> ScheduleModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        # Create or update the ScheduleModel
        model = ScheduleModel(
            id=entity.id if entity.id > 0 else None,  # Use None for new entities
            team_id=entity.team_id,
            start_date=entity.start_date,
            periods_per_day=entity.periods_per_day,
            call_ins=entity.call_ins,
            offline=entity.offline,
            force_complete=entity.force_complete,
            status=entity.status,
            error_message=entity.error_message,
            task_id=entity.task_id
        )

        return model

    def _update_model(self, model: ScheduleModel, entity: Schedule) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        model.team_id = entity.team_id
        model.start_date = entity.start_date
        model.periods_per_day = entity.periods_per_day
        model.call_ins = entity.call_ins
        model.offline = entity.offline
        model.force_complete = entity.force_complete
        model.status = entity.status
        model.error_message = entity.error_message
        model.task_id = entity.task_id

        # Note: We don't update work_history_entries here as they are managed separately
        # through the AssignmentRepository