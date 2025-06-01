from typing import List, Optional, Generator
from datetime import date
from contextlib import contextmanager
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from domain.entities.schedule import Schedule
from domain.models.ScheduleModel import ScheduleModel
from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel
from domain.repositories.interfaces.schedule_repository_interface import ScheduleRepositoryInterface
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger


class SqlAlchemyScheduleRepository(BaseSqlAlchemyRepository[Schedule, ScheduleModel], ScheduleRepositoryInterface):
    """
    SQLAlchemy implementation of the ScheduleRepositoryInterface.
    """

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.

        Yields:
            The SQLAlchemy session.
        """
        try:
            yield self._session
            self._session.commit()
        except SQLAlchemyError as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Database operation failed: {error_msg}",
                extra={
                    "event_type": "database_error",
                    "error_type": type(e).__name__,
                    "repository": "schedule"
                }
            )
            raise RepositoryError(f"Database error: {error_msg}")
        except Exception as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in schedule repository: {error_msg}",
                extra={
                    "event_type": "unexpected_error",
                    "error_type": type(e).__name__,
                    "repository": "schedule"
                }
            )
            raise RepositoryError(f"Repository error: {error_msg}")

    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session: The SQLAlchemy session to use for database operations.
        """
        super().__init__(session, ScheduleModel, Schedule)
        self.logger = get_logger("heijunka.repositories.schedule")
        self.rate_limited_logger = get_logger("heijunka.repositories.schedule", rate_limit=True)

    def get_by_task_id(self, task_id: str) -> Optional[Schedule]:
        """
        Get a schedule by its task ID.

        Args:
            task_id: The task ID of the schedule.

        Returns:
            The schedule if found, None otherwise.
        """
        try:
            self.logger.info(
                f"Retrieving schedule by task ID: {task_id}",
                extra={
                    "event_type": "schedule_lookup",
                    "lookup_type": "task_id",
                    "task_id": task_id
                }
            )

            model = self._session.query(ScheduleModel).filter(ScheduleModel.task_id == task_id).options(
                joinedload(ScheduleModel.team),
                joinedload(ScheduleModel.work_history_entries).joinedload(EmployeeWorkHistoryModel.employee),
                joinedload(ScheduleModel.work_history_entries).joinedload(EmployeeWorkHistoryModel.station)
            ).first()

            if model is None:
                self.logger.info(
                    f"No schedule found with task ID: {task_id}",
                    extra={
                        "event_type": "schedule_lookup_failed",
                        "lookup_type": "task_id",
                        "task_id": task_id,
                        "reason": "not_found"
                    }
                )
                return None

            self.logger.info(
                f"Found schedule with task ID: {task_id}",
                extra={
                    "event_type": "schedule_lookup_success",
                    "lookup_type": "task_id",
                    "task_id": task_id,
                    "schedule_id": model.id,
                    "team_id": model.team_id
                }
            )

            return self._to_domain(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving schedule by task ID: {error_msg}",
                extra={
                    "event_type": "schedule_lookup_error",
                    "lookup_type": "task_id",
                    "task_id": task_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Database error while retrieving schedule by task ID: {error_msg}")

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
            self.logger.info(
                f"Retrieving schedules for team ID: {team_id}",
                extra={
                    "event_type": "schedules_lookup",
                    "lookup_type": "team_id",
                    "team_id": team_id,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "status": status,
                    "skip": skip,
                    "limit": limit
                }
            )

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

            count = len(models)
            self.logger.info(
                f"Retrieved {count} schedules for team ID: {team_id}",
                extra={
                    "event_type": "schedules_lookup_success",
                    "lookup_type": "team_id",
                    "team_id": team_id,
                    "count": count
                }
            )

            return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving schedules by team ID: {error_msg}",
                extra={
                    "event_type": "schedules_lookup_error",
                    "lookup_type": "team_id",
                    "team_id": team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Database error while retrieving schedules by team ID: {error_msg}")

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
            self.logger.info(
                "Creating new schedule",
                extra={
                    "event_type": "schedule_create",
                    "team_id": team_id,
                    "start_date": start_date.isoformat() if start_date else None,
                    "periods_per_day": periods_per_day,
                    "call_ins_count": len(call_ins) if call_ins else 0,
                    "offline_count": len(offline) if offline else 0,
                    "force_complete": force_complete
                }
            )

            # Parse offline parameter to convert to the format expected by the Schedule entity
            offline_dict = {}
            if offline:
                for offline_str in offline:
                    parts = offline_str.split(':')
                    if len(parts) == 2:
                        emp_name, periods_str = parts
                        periods = [int(p) for p in periods_str.split(',')]
                        offline_dict[emp_name] = periods
                        self.logger.debug(
                            f"Parsed offline entry: {emp_name} for periods {periods}",
                            extra={
                                "event_type": "schedule_create_offline_parse",
                                "employee_name": emp_name,
                                "periods": periods
                            }
                        )

            with self.session_scope() as session:
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

                session.add(model)
                session.flush()

                self.logger.info(
                    "Successfully created schedule",
                    extra={
                        "event_type": "schedule_create_success",
                        "schedule_id": model.id,
                        "team_id": team_id,
                        "start_date": start_date.isoformat() if start_date else None
                    }
                )

                # Convert to domain entity
                return self._to_domain(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error creating schedule: {error_msg}",
                extra={
                    "event_type": "schedule_create_error",
                    "team_id": team_id,
                    "start_date": start_date.isoformat() if start_date else None,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to create schedule: {error_msg}")

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
            self.logger.info(
                f"Updating schedule status for schedule ID: {schedule_id}",
                extra={
                    "event_type": "schedule_status_update",
                    "schedule_id": schedule_id,
                    "new_status": status,
                    "has_error_message": error_message is not None
                }
            )

            with self.session_scope() as session:
                model = session.query(ScheduleModel).get(schedule_id)
                if model is None:
                    self.logger.info(
                        f"No schedule found with ID: {schedule_id} to update status",
                        extra={
                            "event_type": "schedule_status_update_failed",
                            "schedule_id": schedule_id,
                            "reason": "not_found"
                        }
                    )
                    return None

                # Log the change
                old_status = model.status
                self.logger.info(
                    "Changing schedule status",
                    extra={
                        "event_type": "schedule_field_change",
                        "schedule_id": schedule_id,
                        "field": "status",
                        "old_value": old_status,
                        "new_value": status
                    }
                )

                model.status = status
                if error_message is not None:
                    old_error = model.error_message
                    self.logger.info(
                        "Changing schedule error message",
                        extra={
                            "event_type": "schedule_field_change",
                            "schedule_id": schedule_id,
                            "field": "error_message",
                            "old_value": old_error,
                            "new_value": error_message
                        }
                    )
                    model.error_message = error_message

                session.flush()

                self.logger.info(
                    f"Successfully updated schedule status for schedule ID: {schedule_id}",
                    extra={
                        "event_type": "schedule_status_update_success",
                        "schedule_id": schedule_id,
                        "status": status
                    }
                )

                return self._to_domain(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating schedule status: {error_msg}",
                extra={
                    "event_type": "schedule_status_update_error",
                    "schedule_id": schedule_id,
                    "status": status,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to update schedule status: {error_msg}")

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
            self.logger.info(
                "Counting schedules with filters",
                extra={
                    "event_type": "schedules_count",
                    "team_id": team_id,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "status": status
                }
            )

            query = self._session.query(ScheduleModel)

            if team_id is not None:
                query = query.filter(ScheduleModel.team_id == team_id)

            if start_date is not None:
                query = query.filter(ScheduleModel.start_date >= start_date)

            if end_date is not None:
                query = query.filter(ScheduleModel.start_date <= end_date)

            if status is not None:
                query = query.filter(ScheduleModel.status == status)

            count = query.count()

            self.logger.info(
                f"Counted {count} schedules matching filters",
                extra={
                    "event_type": "schedules_count_success",
                    "count": count,
                    "team_id": team_id,
                    "status": status
                }
            )

            return count
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error counting schedules: {error_msg}",
                extra={
                    "event_type": "schedules_count_error",
                    "team_id": team_id,
                    "status": status,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Database error while counting schedules: {error_msg}")

    def _to_domain(self, model: ScheduleModel) -> Schedule:
        """
        Convert a SQLAlchemy model to a domain entity using factory.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            self.logger.debug(
                "Converting schedule model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "team_id": model.team_id,
                    "start_date": model.start_date.isoformat() if model.start_date else None
                }
            )

            from domain.factories.schedule_factory import ScheduleFactory
            schedule = ScheduleFactory.create_from_model(model)

            self.logger.debug(
                "Successfully converted schedule model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion_success",
                    "entity_id": model.id
                }
            )

            return schedule
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting schedule model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: Schedule) -> ScheduleModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            entity_id = entity.id if hasattr(entity, 'id') and entity.id > 0 else "new"
            self.logger.debug(
                "Converting schedule domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "entity_id": entity_id,
                    "team_id": entity.team_id,
                    "start_date": entity.start_date.isoformat() if entity.start_date else None
                }
            )

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

            self.logger.debug(
                "Successfully converted schedule domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion_success",
                    "entity_id": entity_id
                }
            )

            return model
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting schedule domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "entity_id": entity.id if entity and hasattr(entity, 'id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: ScheduleModel, entity: Schedule) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            self.logger.debug(
                "Updating schedule model from domain entity",
                extra={
                    "event_type": "schedule_model_update",
                    "entity_id": model.id,
                    "team_id": model.team_id
                }
            )

            # Check for significant changes and log them
            if model.team_id != entity.team_id:
                self.logger.info(
                    "Changing schedule team",
                    extra={
                        "event_type": "schedule_field_change",
                        "entity_id": model.id,
                        "field": "team_id",
                        "old_value": model.team_id,
                        "new_value": entity.team_id
                    }
                )

            if model.start_date != entity.start_date:
                self.logger.info(
                    "Changing schedule start date",
                    extra={
                        "event_type": "schedule_field_change",
                        "entity_id": model.id,
                        "field": "start_date",
                        "old_value": model.start_date.isoformat() if model.start_date else None,
                        "new_value": entity.start_date.isoformat() if entity.start_date else None
                    }
                )

            if model.status != entity.status:
                self.logger.info(
                    "Changing schedule status",
                    extra={
                        "event_type": "schedule_field_change",
                        "entity_id": model.id,
                        "field": "status",
                        "old_value": model.status,
                        "new_value": entity.status
                    }
                )

            # Update the model
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

            self.logger.debug(
                "Successfully updated schedule model",
                extra={
                    "event_type": "schedule_model_update_success",
                    "entity_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating schedule model: {error_msg}",
                extra={
                    "event_type": "schedule_model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise
