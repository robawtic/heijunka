from typing import List, Optional, Generator
from datetime import date
from contextlib import contextmanager
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from domain.contexts.assignment.aro_assignment import AROAssignment
from domain.models.AROAssignmentModel import AROAssignmentModel
from domain.repositories.interfaces.aro_assignment_repository import AROAssignmentRepositoryInterface
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger

class SqlAlchemyAROAssignmentRepository(BaseSqlAlchemyRepository[AROAssignment, AROAssignmentModel], AROAssignmentRepositoryInterface):
    """
    SQLAlchemy implementation of the AROAssignmentRepository interface.
    """

    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session: The SQLAlchemy session to use for database operations.
        """
        super().__init__(session, AROAssignmentModel, AROAssignment)
        self.logger = get_logger("heijunka.repositories.aro_assignment")
        self.rate_limited_logger = get_logger("heijunka.repositories.aro_assignment", rate_limit=False)

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
                    "repository": "aro_assignment"
                }
            )
            raise RepositoryError(f"Database error: {error_msg}")
        except Exception as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in ARO assignment repository: {error_msg}",
                extra={
                    "event_type": "unexpected_error",
                    "error_type": type(e).__name__,
                    "repository": "aro_assignment"
                }
            )
            raise RepositoryError(f"Repository error: {error_msg}")

    def get_by_date(self, assignment_date: date) -> List[AROAssignment]:
        """
        Retrieve all ARO assignments for a specific date.

        Args:
            assignment_date: The date to retrieve assignments for.

        Returns:
            A list of ARO assignments for the specified date.
        """
        try:
            self.logger.info(
                f"Retrieving ARO assignments for date: {assignment_date}",
                extra={
                    "event_type": "aro_assignments_lookup",
                    "lookup_type": "date",
                    "assignment_date": assignment_date.isoformat()
                }
            )

            models = self._session.query(AROAssignmentModel).filter(
                AROAssignmentModel.assignment_date == assignment_date
            ).all()

            assignment_count = len(models)
            self.logger.info(
                f"Found {assignment_count} ARO assignments for date: {assignment_date}",
                extra={
                    "event_type": "aro_assignments_lookup_success",
                    "lookup_type": "date",
                    "assignment_date": assignment_date.isoformat(),
                    "assignment_count": assignment_count
                }
            )

            return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving ARO assignments by date: {error_msg}",
                extra={
                    "event_type": "aro_assignments_lookup_error",
                    "lookup_type": "date",
                    "assignment_date": assignment_date.isoformat() if assignment_date else None,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving ARO assignments by date: {error_msg}")

    def get_by_employee_id(self, employee_id: int, assignment_date: Optional[date] = None) -> List[AROAssignment]:
        """
        Retrieve all ARO assignments for a specific employee.

        Args:
            employee_id: The ID of the employee to retrieve assignments for.
            assignment_date: Optional date to filter assignments by.

        Returns:
            A list of ARO assignments for the specified employee.
        """
        try:
            log_context = {
                "event_type": "aro_assignments_lookup",
                "lookup_type": "employee_id",
                "employee_id": employee_id
            }

            if assignment_date:
                log_context["assignment_date"] = assignment_date.isoformat()
                self.logger.info(
                    f"Retrieving ARO assignments for employee ID: {employee_id} on date: {assignment_date}",
                    extra=log_context
                )
            else:
                self.logger.info(
                    f"Retrieving all ARO assignments for employee ID: {employee_id}",
                    extra=log_context
                )

            query = self._session.query(AROAssignmentModel).filter(
                AROAssignmentModel.employee_id == employee_id
            )

            if assignment_date:
                query = query.filter(AROAssignmentModel.assignment_date == assignment_date)

            models = query.all()
            assignment_count = len(models)

            success_context = {
                "event_type": "aro_assignments_lookup_success",
                "lookup_type": "employee_id",
                "employee_id": employee_id,
                "assignment_count": assignment_count
            }

            if assignment_date:
                success_context["assignment_date"] = assignment_date.isoformat()
                self.logger.info(
                    f"Found {assignment_count} ARO assignments for employee ID: {employee_id} on date: {assignment_date}",
                    extra=success_context
                )
            else:
                self.logger.info(
                    f"Found {assignment_count} ARO assignments for employee ID: {employee_id}",
                    extra=success_context
                )

            return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            error_context = {
                "event_type": "aro_assignments_lookup_error",
                "lookup_type": "employee_id",
                "employee_id": employee_id,
                "error_type": type(e).__name__
            }

            if assignment_date:
                error_context["assignment_date"] = assignment_date.isoformat()

            self.logger.error(
                f"Error retrieving ARO assignments by employee ID: {error_msg}",
                extra=error_context
            )
            raise RepositoryError(f"Error retrieving ARO assignments by employee ID: {error_msg}")

    def get_by_from_team_id(self, team_id: int, assignment_date: date) -> List[AROAssignment]:
        """
        Retrieve all ARO assignments where employees are leaving a specific team on a specific date.

        Args:
            team_id: The ID of the team that employees are leaving from.
            assignment_date: The date to retrieve assignments for.

        Returns:
            A list of ARO assignments for employees leaving the specified team.
        """
        try:
            self.logger.info(
                f"Retrieving ARO assignments for employees leaving team ID: {team_id} on date: {assignment_date}",
                extra={
                    "event_type": "aro_assignments_lookup",
                    "lookup_type": "from_team_id",
                    "team_id": team_id,
                    "assignment_date": assignment_date.isoformat()
                }
            )

            models = self._session.query(AROAssignmentModel).filter(
                and_(
                    AROAssignmentModel.from_team_id == team_id,
                    AROAssignmentModel.assignment_date == assignment_date
                )
            ).all()

            assignment_count = len(models)
            self.logger.info(
                f"Found {assignment_count} ARO assignments for employees leaving team ID: {team_id} on date: {assignment_date}",
                extra={
                    "event_type": "aro_assignments_lookup_success",
                    "lookup_type": "from_team_id",
                    "team_id": team_id,
                    "assignment_date": assignment_date.isoformat(),
                    "assignment_count": assignment_count
                }
            )

            return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving ARO assignments by from_team_id: {error_msg}",
                extra={
                    "event_type": "aro_assignments_lookup_error",
                    "lookup_type": "from_team_id",
                    "team_id": team_id,
                    "assignment_date": assignment_date.isoformat() if assignment_date else None,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving ARO assignments by from_team_id: {error_msg}")

    def get_by_to_team_id(self, team_id: int, assignment_date: date) -> List[AROAssignment]:
        """
        Retrieve all ARO assignments where employees are joining a specific team on a specific date.

        Args:
            team_id: The ID of the team that employees are joining to.
            assignment_date: The date to retrieve assignments for.

        Returns:
            A list of ARO assignments for employees joining the specified team.
        """
        try:
            self.logger.info(
                f"Retrieving ARO assignments for employees joining team ID: {team_id} on date: {assignment_date}",
                extra={
                    "event_type": "aro_assignments_lookup",
                    "lookup_type": "to_team_id",
                    "team_id": team_id,
                    "assignment_date": assignment_date.isoformat()
                }
            )

            models = self._session.query(AROAssignmentModel).filter(
                and_(
                    AROAssignmentModel.to_team_id == team_id,
                    AROAssignmentModel.assignment_date == assignment_date
                )
            ).all()

            assignment_count = len(models)
            self.logger.info(
                f"Found {assignment_count} ARO assignments for employees joining team ID: {team_id} on date: {assignment_date}",
                extra={
                    "event_type": "aro_assignments_lookup_success",
                    "lookup_type": "to_team_id",
                    "team_id": team_id,
                    "assignment_date": assignment_date.isoformat(),
                    "assignment_count": assignment_count
                }
            )

            return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving ARO assignments by to_team_id: {error_msg}",
                extra={
                    "event_type": "aro_assignments_lookup_error",
                    "lookup_type": "to_team_id",
                    "team_id": team_id,
                    "assignment_date": assignment_date.isoformat() if assignment_date else None,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving ARO assignments by to_team_id: {error_msg}")

    def get_employees_leaving(self, team_id: int, assignment_date: date, period: Optional[int] = None) -> List[int]:
        """
        Retrieve IDs of employees leaving a specific team on a specific date and optionally during a specific period.

        Args:
            team_id: The ID of the team that employees are leaving from.
            assignment_date: The date to retrieve assignments for.
            period: Optional period to filter assignments by.

        Returns:
            A list of employee IDs that are leaving the specified team.
        """
        try:
            log_context = {
                "event_type": "employees_leaving_lookup",
                "team_id": team_id,
                "assignment_date": assignment_date.isoformat()
            }

            if period is not None:
                log_context["period"] = period
                self.logger.info(
                    f"Retrieving employees leaving team ID: {team_id} on date: {assignment_date} during period: {period}",
                    extra=log_context
                )
            else:
                self.logger.info(
                    f"Retrieving employees leaving team ID: {team_id} on date: {assignment_date}",
                    extra=log_context
                )

            query = self._session.query(AROAssignmentModel.employee_id).filter(
                and_(
                    AROAssignmentModel.from_team_id == team_id,
                    AROAssignmentModel.assignment_date == assignment_date
                )
            )

            if period is not None:
                query = query.filter(
                    or_(
                        AROAssignmentModel.period == period,
                        AROAssignmentModel.period == None  # Full-day assignments
                    )
                )

            result = [employee_id for (employee_id,) in query.all()]
            employee_count = len(result)

            success_context = {
                "event_type": "employees_leaving_lookup_success",
                "team_id": team_id,
                "assignment_date": assignment_date.isoformat(),
                "employee_count": employee_count
            }

            if period is not None:
                success_context["period"] = period
                self.logger.info(
                    f"Found {employee_count} employees leaving team ID: {team_id} on date: {assignment_date} during period: {period}",
                    extra=success_context
                )
            else:
                self.logger.info(
                    f"Found {employee_count} employees leaving team ID: {team_id} on date: {assignment_date}",
                    extra=success_context
                )

            return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            error_context = {
                "event_type": "employees_leaving_lookup_error",
                "team_id": team_id,
                "assignment_date": assignment_date.isoformat() if assignment_date else None,
                "error_type": type(e).__name__
            }

            if period is not None:
                error_context["period"] = period

            self.logger.error(
                f"Error retrieving employees leaving team: {error_msg}",
                extra=error_context
            )
            raise RepositoryError(f"Error retrieving employees leaving team: {error_msg}")

    def get_employees_joining(self, team_id: int, assignment_date: date, period: Optional[int] = None) -> List[int]:
        """
        Retrieve IDs of employees joining a specific team on a specific date and optionally during a specific period.

        Args:
            team_id: The ID of the team that employees are joining to.
            assignment_date: The date to retrieve assignments for.
            period: Optional period to filter assignments by.

        Returns:
            A list of employee IDs that are joining the specified team.
        """
        try:
            log_context = {
                "event_type": "employees_joining_lookup",
                "team_id": team_id,
                "assignment_date": assignment_date.isoformat()
            }

            if period is not None:
                log_context["period"] = period
                self.logger.info(
                    f"Retrieving employees joining team ID: {team_id} on date: {assignment_date} during period: {period}",
                    extra=log_context
                )
            else:
                self.logger.info(
                    f"Retrieving employees joining team ID: {team_id} on date: {assignment_date}",
                    extra=log_context
                )

            query = self._session.query(AROAssignmentModel.employee_id).filter(
                and_(
                    AROAssignmentModel.to_team_id == team_id,
                    AROAssignmentModel.assignment_date == assignment_date
                )
            )

            if period is not None:
                query = query.filter(
                    or_(
                        AROAssignmentModel.period == period,
                        AROAssignmentModel.period == None  # Full-day assignments
                    )
                )

            result = [employee_id for (employee_id,) in query.all()]
            employee_count = len(result)

            success_context = {
                "event_type": "employees_joining_lookup_success",
                "team_id": team_id,
                "assignment_date": assignment_date.isoformat(),
                "employee_count": employee_count
            }

            if period is not None:
                success_context["period"] = period
                self.logger.info(
                    f"Found {employee_count} employees joining team ID: {team_id} on date: {assignment_date} during period: {period}",
                    extra=success_context
                )
            else:
                self.logger.info(
                    f"Found {employee_count} employees joining team ID: {team_id} on date: {assignment_date}",
                    extra=success_context
                )

            return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            error_context = {
                "event_type": "employees_joining_lookup_error",
                "team_id": team_id,
                "assignment_date": assignment_date.isoformat() if assignment_date else None,
                "error_type": type(e).__name__
            }

            if period is not None:
                error_context["period"] = period

            self.logger.error(
                f"Error retrieving employees joining team: {error_msg}",
                extra=error_context
            )
            raise RepositoryError(f"Error retrieving employees joining team: {error_msg}")

    def _to_domain(self, model: AROAssignmentModel) -> AROAssignment:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            self.logger.debug(
                "Converting ARO assignment model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "employee_id": model.employee_id,
                    "from_team_id": model.from_team_id,
                    "to_team_id": model.to_team_id,
                    "assignment_date": model.assignment_date.isoformat() if model.assignment_date else None
                }
            )

            return AROAssignment(
                id=model.id,
                employee_id=model.employee_id,
                from_team_id=model.from_team_id,
                to_team_id=model.to_team_id,
                assignment_date=model.assignment_date,
                period=model.period
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting ARO assignment model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: AROAssignment) -> AROAssignmentModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            self.logger.debug(
                "Converting ARO assignment domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "employee_id": entity.employee_id,
                    "from_team_id": entity.from_team_id,
                    "to_team_id": entity.to_team_id,
                    "assignment_date": entity.assignment_date.isoformat() if entity.assignment_date else None
                }
            )

            model = AROAssignmentModel(
                employee_id=entity.employee_id,
                from_team_id=entity.from_team_id,
                to_team_id=entity.to_team_id,
                assignment_date=entity.assignment_date,
                period=entity.period
            )

            return model
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting ARO assignment domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "employee_id": entity.employee_id if entity and hasattr(entity, 'employee_id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: AROAssignmentModel, entity: AROAssignment) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            self.logger.debug(
                "Updating ARO assignment model from domain entity",
                extra={
                    "event_type": "aro_assignment_model_update",
                    "entity_id": model.id,
                    "employee_id": model.employee_id
                }
            )

            # Check for significant changes and log them
            if model.from_team_id != entity.from_team_id:
                self.logger.info(
                    "Changing ARO assignment from_team_id",
                    extra={
                        "event_type": "aro_assignment_field_change",
                        "entity_id": model.id,
                        "field": "from_team_id",
                        "old_value": model.from_team_id,
                        "new_value": entity.from_team_id
                    }
                )

            if model.to_team_id != entity.to_team_id:
                self.logger.info(
                    "Changing ARO assignment to_team_id",
                    extra={
                        "event_type": "aro_assignment_field_change",
                        "entity_id": model.id,
                        "field": "to_team_id",
                        "old_value": model.to_team_id,
                        "new_value": entity.to_team_id
                    }
                )

            if model.assignment_date != entity.assignment_date:
                self.logger.info(
                    "Changing ARO assignment date",
                    extra={
                        "event_type": "aro_assignment_field_change",
                        "entity_id": model.id,
                        "field": "assignment_date",
                        "old_value": model.assignment_date.isoformat() if model.assignment_date else None,
                        "new_value": entity.assignment_date.isoformat() if entity.assignment_date else None
                    }
                )

            if model.period != entity.period:
                self.logger.info(
                    "Changing ARO assignment period",
                    extra={
                        "event_type": "aro_assignment_field_change",
                        "entity_id": model.id,
                        "field": "period",
                        "old_value": model.period,
                        "new_value": entity.period
                    }
                )

            # Update the model
            model.employee_id = entity.employee_id
            model.from_team_id = entity.from_team_id
            model.to_team_id = entity.to_team_id
            model.assignment_date = entity.assignment_date
            model.period = entity.period

            self.logger.debug(
                "Successfully updated ARO assignment model",
                extra={
                    "event_type": "aro_assignment_model_update_success",
                    "entity_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating ARO assignment model: {error_msg}",
                extra={
                    "event_type": "aro_assignment_model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise
