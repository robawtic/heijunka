from typing import List, Optional, Generator
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from domain.contexts.assignment.entities.team_aro import TeamAro
from domain.models.TeamAroModel import TeamAroModel, AroTeamStatus
from domain.repositories.interfaces.team_aro_repository import TeamAroRepositoryInterface
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger

class SqlAlchemyTeamAroRepository(BaseSqlAlchemyRepository[TeamAro, TeamAroModel], TeamAroRepositoryInterface):
    """
    SQLAlchemy implementation of the TeamAroRepository interface.
    """

    def __init__(self, session_factory):
        """
        Initialize the repository with a SQLAlchemy session factory.

        Args:
            session_factory: The SQLAlchemy session factory to use for database operations.
        """
        super().__init__(session_factory, TeamAroModel, TeamAro)
        self.logger = get_logger("heijunka.repositories.team_aro")
        self.rate_limited_logger = get_logger("heijunka.repositories.team_aro", rate_limit=True)


    def get(self, team_aro_id: int) -> Optional[TeamAro]:
        """
        Retrieve a TeamAro relationship by its ID.

        Args:
            team_aro_id: The ID of the TeamAro relationship to retrieve.

        Returns:
            A TeamAro object if found, None otherwise.
        """
        return self.get_by_id(team_aro_id)

    def get_by_employee_id(self, employee_id: int) -> List[TeamAro]:
        """
        Retrieve all TeamAro relationships for a specific employee.

        Args:
            employee_id: The ID of the employee.

        Returns:
            A list of TeamAro relationships for the employee.
        """
        try:
            self.logger.info(
                f"Retrieving TeamAro relationships for employee ID: {employee_id}",
                extra={
                    "event_type": "team_aro_lookup",
                    "lookup_type": "employee_id",
                    "employee_id": employee_id
                }
            )

            with self.session_scope() as session:
                models = session.query(TeamAroModel).filter(
                    TeamAroModel.employee_id == employee_id
                ).all()

                relationship_count = len(models)
                self.logger.info(
                    f"Found {relationship_count} TeamAro relationships for employee ID: {employee_id}",
                    extra={
                        "event_type": "team_aro_lookup_success",
                        "lookup_type": "employee_id",
                        "employee_id": employee_id,
                        "relationship_count": relationship_count
                    }
                )

                return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving TeamAro relationships by employee ID: {error_msg}",
                extra={
                    "event_type": "team_aro_lookup_error",
                    "lookup_type": "employee_id",
                    "employee_id": employee_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving TeamAro relationships by employee ID: {error_msg}")

    def get_by_team_id(self, team_id: int) -> List[TeamAro]:
        """
        Retrieve all TeamAro relationships for a specific team.

        Args:
            team_id: The ID of the team.

        Returns:
            A list of TeamAro relationships for the team.
        """
        try:
            self.logger.info(
                f"Retrieving TeamAro relationships for team ID: {team_id}",
                extra={
                    "event_type": "team_aro_lookup",
                    "lookup_type": "team_id",
                    "team_id": team_id
                }
            )

            with self.session_scope() as session:
                models = session.query(TeamAroModel).filter(
                    TeamAroModel.team_id == team_id
                ).all()

                relationship_count = len(models)
                self.logger.info(
                    f"Found {relationship_count} TeamAro relationships for team ID: {team_id}",
                    extra={
                        "event_type": "team_aro_lookup_success",
                        "lookup_type": "team_id",
                        "team_id": team_id,
                        "relationship_count": relationship_count
                    }
                )

                return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving TeamAro relationships by team ID: {error_msg}",
                extra={
                    "event_type": "team_aro_lookup_error",
                    "lookup_type": "team_id",
                    "team_id": team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving TeamAro relationships by team ID: {error_msg}")

    def get_by_status(self, status: str) -> List[TeamAro]:
        """
        Retrieve all TeamAro relationships with a specific status.

        Args:
            status: The status to filter by (e.g., "active", "inactive").

        Returns:
            A list of TeamAro relationships with the specified status.
        """
        try:
            self.logger.info(
                f"Retrieving TeamAro relationships with status: {status}",
                extra={
                    "event_type": "team_aro_lookup",
                    "lookup_type": "status",
                    "status": status
                }
            )

            # Convert string status to enum value
            try:
                status_enum = AroTeamStatus(status)
            except ValueError:
                error_msg = f"Invalid status value: {status}"
                self.logger.error(
                    error_msg,
                    extra={
                        "event_type": "team_aro_lookup_error",
                        "lookup_type": "status",
                        "status": status,
                        "error_type": "ValueError"
                    }
                )
                raise RepositoryError(error_msg)

            with self.session_scope() as session:
                models = session.query(TeamAroModel).filter(
                    TeamAroModel.status == status_enum
                ).all()

                relationship_count = len(models)
                self.logger.info(
                    f"Found {relationship_count} TeamAro relationships with status: {status}",
                    extra={
                        "event_type": "team_aro_lookup_success",
                        "lookup_type": "status",
                        "status": status,
                        "relationship_count": relationship_count
                    }
                )

                return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving TeamAro relationships by status: {error_msg}",
                extra={
                    "event_type": "team_aro_lookup_error",
                    "lookup_type": "status",
                    "status": status,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving TeamAro relationships by status: {error_msg}")

    def update_status(self, team_aro_id: int, new_status: str) -> bool:
        """
        Update the status of a TeamAro relationship.

        Args:
            team_aro_id: The ID of the TeamAro relationship.
            new_status: The new status to set.

        Returns:
            True if the status was updated, False otherwise.
        """
        try:
            self.logger.info(
                f"Updating status of TeamAro relationship with ID: {team_aro_id} to {new_status}",
                extra={
                    "event_type": "team_aro_status_update",
                    "team_aro_id": team_aro_id,
                    "new_status": new_status
                }
            )

            # Convert string status to enum value
            try:
                status_enum = AroTeamStatus(new_status)
            except ValueError:
                error_msg = f"Invalid status value: {new_status}"
                self.logger.error(
                    error_msg,
                    extra={
                        "event_type": "team_aro_status_update_error",
                        "team_aro_id": team_aro_id,
                        "new_status": new_status,
                        "error_type": "ValueError"
                    }
                )
                raise RepositoryError(error_msg)

            with self.session_scope() as session:
                model = session.get(TeamAroModel, team_aro_id)
                if model is None:
                    self.logger.warning(
                        f"TeamAro relationship with ID: {team_aro_id} not found",
                        extra={
                            "event_type": "team_aro_status_update_failed",
                            "team_aro_id": team_aro_id,
                            "reason": "not_found"
                        }
                    )
                    return False

                old_status = model.status.value if isinstance(model.status, AroTeamStatus) else model.status
                model.status = status_enum

                self.logger.info(
                    f"Successfully updated status of TeamAro relationship with ID: {team_aro_id} from {old_status} to {new_status}",
                    extra={
                        "event_type": "team_aro_status_update_success",
                        "team_aro_id": team_aro_id,
                        "old_status": old_status,
                        "new_status": new_status
                    }
                )

                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating status of TeamAro relationship: {error_msg}",
                extra={
                    "event_type": "team_aro_status_update_error",
                    "team_aro_id": team_aro_id,
                    "new_status": new_status,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error updating status of TeamAro relationship: {error_msg}")

    def remove(self, team_aro_id: int) -> bool:
        """
        Remove a TeamAro relationship by its ID.

        Args:
            team_aro_id: The ID of the TeamAro relationship to remove.

        Returns:
            True if the relationship was removed, False otherwise.
        """
        return self.delete(team_aro_id)

    def _to_domain(self, model: TeamAroModel) -> TeamAro:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            self.logger.debug(
                "Converting TeamAro model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "employee_id": model.employee_id,
                    "team_id": model.team_id
                }
            )

            # Convert enum status to string value
            status = model.status.value if isinstance(model.status, AroTeamStatus) else model.status

            return TeamAro(
                id=model.id,
                employee_id=model.employee_id,
                team_id=model.team_id,
                status=status
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting TeamAro model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: TeamAro) -> TeamAroModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            self.logger.debug(
                "Converting TeamAro domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "employee_id": entity.employee_id,
                    "team_id": entity.team_id,
                    "status": entity.status
                }
            )

            # Convert string status to enum value
            try:
                status_enum = AroTeamStatus(entity.status)
            except ValueError:
                error_msg = f"Invalid status value: {entity.status}"
                self.logger.error(
                    error_msg,
                    extra={
                        "event_type": "domain_to_model_conversion_error",
                        "employee_id": entity.employee_id,
                        "team_id": entity.team_id,
                        "status": entity.status,
                        "error_type": "ValueError"
                    }
                )
                raise RepositoryError(error_msg)

            model = TeamAroModel(
                employee_id=entity.employee_id,
                team_id=entity.team_id,
                status=status_enum
            )

            # Set ID if it exists
            if entity.id is not None:
                model.id = entity.id

            return model
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting TeamAro domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "employee_id": entity.employee_id if entity and hasattr(entity, 'employee_id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: TeamAroModel, entity: TeamAro) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            self.logger.debug(
                "Updating TeamAro model from domain entity",
                extra={
                    "event_type": "team_aro_model_update",
                    "entity_id": model.id,
                    "employee_id": model.employee_id
                }
            )

            # Convert string status to enum value
            try:
                status_enum = AroTeamStatus(entity.status)
            except ValueError:
                error_msg = f"Invalid status value: {entity.status}"
                self.logger.error(
                    error_msg,
                    extra={
                        "event_type": "team_aro_model_update_error",
                        "entity_id": model.id,
                        "employee_id": model.employee_id,
                        "status": entity.status,
                        "error_type": "ValueError"
                    }
                )
                raise RepositoryError(error_msg)

            # Check for significant changes and log them
            if model.employee_id != entity.employee_id:
                self.logger.info(
                    "Changing TeamAro employee_id",
                    extra={
                        "event_type": "team_aro_field_change",
                        "entity_id": model.id,
                        "field": "employee_id",
                        "old_value": model.employee_id,
                        "new_value": entity.employee_id
                    }
                )

            if model.team_id != entity.team_id:
                self.logger.info(
                    "Changing TeamAro team_id",
                    extra={
                        "event_type": "team_aro_field_change",
                        "entity_id": model.id,
                        "field": "team_id",
                        "old_value": model.team_id,
                        "new_value": entity.team_id
                    }
                )

            current_status = model.status.value if isinstance(model.status, AroTeamStatus) else model.status
            if current_status != entity.status:
                self.logger.info(
                    "Changing TeamAro status",
                    extra={
                        "event_type": "team_aro_field_change",
                        "entity_id": model.id,
                        "field": "status",
                        "old_value": current_status,
                        "new_value": entity.status
                    }
                )

            # Update the model
            model.employee_id = entity.employee_id
            model.team_id = entity.team_id
            model.status = status_enum

            # Update timestamp if available
            self._stamp_updated(model)

            self.logger.debug(
                "Successfully updated TeamAro model",
                extra={
                    "event_type": "team_aro_model_update_success",
                    "entity_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating TeamAro model: {error_msg}",
                extra={
                    "event_type": "team_aro_model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise