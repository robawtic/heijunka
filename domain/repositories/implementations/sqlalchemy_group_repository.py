from contextlib import contextmanager
from typing import Optional, List, Generator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.entities.group import Group
from domain.models.GroupModel import GroupModel
from domain.repositories.interfaces.group_repository import GroupRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import redact_log_message, sanitize_exception
from utilities.logging_factory import get_logger


class SqlAlchemyGroupRepository(BaseSqlAlchemyRepository[Group, GroupModel], GroupRepositoryInterface):
    """
    SQLAlchemy implementation of the GroupRepository interface.
    """

    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session: The SQLAlchemy session to use for database operations.
        """
        super().__init__(session, GroupModel, Group)
        self.logger = get_logger("heijunka.repositories.group")
        self.rate_limited_logger = get_logger("heijunka.repositories.group", rate_limit=True)

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
                    "repository": "group"
                }
            )
            raise RepositoryError(f"Database error: {error_msg}")
        except Exception as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in group repository: {error_msg}",
                extra={
                    "event_type": "unexpected_error",
                    "error_type": type(e).__name__,
                    "repository": "group"
                }
            )
            raise RepositoryError(f"Repository error: {error_msg}")

    def get_by_name(self, group_name: str) -> Optional[Group]:
        """
        Retrieve a group by its name.

        Args:
            group_name: The name of the group to retrieve.

        Returns:
            The group if found, None otherwise.
        """
        try:
            self.logger.info(
                f"Retrieving group by name: {group_name}",
                extra={
                    "event_type": "group_lookup",
                    "lookup_type": "name",
                    "group_name": group_name
                }
            )

            group_model = self._session.query(GroupModel).filter(
                GroupModel.name == group_name
            ).first()

            if group_model is None:
                self.logger.info(
                    f"No group found with name: {group_name}",
                    extra={
                        "event_type": "group_lookup_failed",
                        "lookup_type": "name",
                        "group_name": group_name,
                        "reason": "not_found"
                    }
                )
                return None

            self.logger.info(
                f"Found group with ID: {group_model.id}",
                extra={
                    "event_type": "group_lookup_success",
                    "lookup_type": "name",
                    "group_name": group_name,
                    "group_id": group_model.id
                }
            )

            return self._to_domain(group_model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving group by name: {error_msg}",
                extra={
                    "event_type": "group_lookup_error",
                    "lookup_type": "name",
                    "group_name": group_name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving group by name: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error retrieving group by name: {error_msg}",
                extra={
                    "event_type": "group_lookup_error",
                    "lookup_type": "name",
                    "group_name": group_name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving group by name: {error_msg}")

    def _to_domain(self, model: GroupModel) -> Group:
        """
        Convert a GroupModel to a Group domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            self.logger.debug(
                "Converting group model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "group_name": model.name
                }
            )

            group = Group(
                id=model.id,
                name=model.name,
                department_id=model.department_id
            )

            self.logger.debug(
                "Successfully converted group model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion_success",
                    "entity_id": model.id
                }
            )

            return group
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting group model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: Group) -> GroupModel:
        """
        Convert a Group domain entity to a GroupModel.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            entity_id = entity.id if entity.id is not None else "new"
            self.logger.debug(
                "Converting group domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "entity_id": entity_id,
                    "group_name": entity.name
                }
            )

            model = GroupModel(
                name=entity.name,
                department_id=entity.department_id
            )

            if entity.id is not None:
                model.id = entity.id

            self.logger.debug(
                "Successfully converted group domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion_success",
                    "entity_id": entity_id
                }
            )

            return model
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting group domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "entity_id": entity.id if entity and hasattr(entity, 'id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: GroupModel, entity: Group) -> None:
        """
        Update a GroupModel with values from a Group domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            self.logger.debug(
                "Updating group model from domain entity",
                extra={
                    "event_type": "group_model_update",
                    "entity_id": model.id,
                    "group_name": model.name
                }
            )

            # Check for significant changes and log them
            if model.name != entity.name:
                self.logger.info(
                    "Changing group name",
                    extra={
                        "event_type": "group_field_change",
                        "entity_id": model.id,
                        "field": "name",
                        "old_value": model.name,
                        "new_value": entity.name
                    }
                )

            if model.department_id != entity.department_id:
                self.logger.info(
                    "Changing group department",
                    extra={
                        "event_type": "group_field_change",
                        "entity_id": model.id,
                        "field": "department_id",
                        "old_value": model.department_id,
                        "new_value": entity.department_id
                    }
                )

            # Update the model
            model.name = entity.name
            model.department_id = entity.department_id

            self.logger.debug(
                "Successfully updated group model",
                extra={
                    "event_type": "group_model_update_success",
                    "entity_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating group model: {error_msg}",
                extra={
                    "event_type": "group_model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise
