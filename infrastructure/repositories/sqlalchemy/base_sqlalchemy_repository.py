from typing import Generic, TypeVar, Optional, List, Type, Generator
from contextlib import contextmanager
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from domain.repositories.interfaces.base_repository import BaseRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger

T = TypeVar('T')
M = TypeVar('M')  # SQLAlchemy model type


class BaseSqlAlchemyRepository(Generic[T, M], BaseRepository[T]):
    """
    Base SQLAlchemy repository implementation that provides common functionality
    for all SQLAlchemy-backed repositories.
    """

    def __init__(self, session: Session, model_class: Type[M], entity_class: Type[T]):
        """
        Initialize the repository with a SQLAlchemy session and model class.

        Args:
            session: The SQLAlchemy session to use for database operations.
            model_class: The SQLAlchemy model class.
            entity_class: The domain entity class.
        """
        self._session = session
        self._model_class = model_class
        self._entity_class = entity_class

        # Initialize loggers - these can be overridden by subclasses
        self.logger = get_logger("heijunka.repositories.base")
        self.rate_limited_logger = get_logger("heijunka.repositories.base", rate_limit=True)

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
                    "repository": self._model_class.__name__
                }
            )
            raise RepositoryError(f"Database error: {error_msg}")
        except Exception as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in repository: {error_msg}",
                extra={
                    "event_type": "unexpected_error",
                    "error_type": type(e).__name__,
                    "repository": self._model_class.__name__
                }
            )
            raise RepositoryError(f"Repository error: {error_msg}")

    def get_by_id(self, entity_id: int) -> Optional[T]:
        """
        Retrieve an entity by its ID.

        Args:
            entity_id: The ID of the entity to retrieve.

        Returns:
            The entity if found, None otherwise.
        """
        try:
            self.logger.info(
                f"Retrieving {self._model_class.__name__} by ID: {entity_id}",
                extra={
                    "event_type": "entity_lookup",
                    "lookup_type": "id",
                    "entity_type": self._model_class.__name__,
                    "entity_id": entity_id
                }
            )

            model = self._session.get(self._model_class, entity_id)

            if model is None:
                self.logger.info(
                    f"No {self._model_class.__name__} found with ID: {entity_id}",
                    extra={
                        "event_type": "entity_lookup_failed",
                        "lookup_type": "id",
                        "entity_type": self._model_class.__name__,
                        "entity_id": entity_id
                    }
                )
                return None

            self.logger.info(
                f"Found {self._model_class.__name__} with ID: {entity_id}",
                extra={
                    "event_type": "entity_lookup_success",
                    "lookup_type": "id",
                    "entity_type": self._model_class.__name__,
                    "entity_id": entity_id
                }
            )

            return self._to_domain(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving {self._model_class.__name__} by ID: {error_msg}",
                extra={
                    "event_type": "entity_lookup_error",
                    "lookup_type": "id",
                    "entity_type": self._model_class.__name__,
                    "entity_id": entity_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving {self._model_class.__name__} by ID: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error retrieving {self._model_class.__name__} by ID: {error_msg}",
                extra={
                    "event_type": "entity_lookup_error",
                    "lookup_type": "id",
                    "entity_type": self._model_class.__name__,
                    "entity_id": entity_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving {self._model_class.__name__} by ID: {error_msg}")

    def list_all(self) -> List[T]:
        """
        Retrieve all entities.

        Returns:
            A list of all entities.
        """
        try:
            self.logger.info(
                f"Retrieving all {self._model_class.__name__} entities",
                extra={
                    "event_type": "entity_list_all",
                    "entity_type": self._model_class.__name__
                }
            )

            models = self._session.query(self._model_class).all()
            count = len(models)

            self.logger.info(
                f"Retrieved {count} {self._model_class.__name__} entities",
                extra={
                    "event_type": "entity_list_all_success",
                    "entity_type": self._model_class.__name__,
                    "count": count
                }
            )

            entities = []
            for model in models:
                self.rate_limited_logger.debug(
                    f"Converting {self._model_class.__name__} [id={model.id}] to domain entity",
                    extra={
                        "event_type": "model_to_domain_conversion",
                        "entity_id": model.id,
                        "entity_type": self._model_class.__name__
                    }
                )
                entities.append(self._to_domain(model))
            return entities
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving all {self._model_class.__name__} entities: {error_msg}",
                extra={
                    "event_type": "entity_list_all_error",
                    "entity_type": self._model_class.__name__,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving all {self._model_class.__name__} entities: {error_msg}")

    def add(self, entity: T) -> T:
        """
        Add a new entity.

        Args:
            entity: The entity to add.

        Returns:
            The added entity.
        """
        try:
            entity_id = getattr(entity, 'id', 'new')
            self.logger.info(
                f"Adding new {self._entity_class.__name__}",
                extra={
                    "event_type": "entity_add",
                    "entity_type": self._entity_class.__name__,
                    "entity_id": entity_id
                }
            )

            with self.session_scope() as session:
                model = self._to_model(entity)
                session.add(model)
                session.flush()  # Flush to get the ID if it's auto-generated

                # Get the ID after flush
                model_id = getattr(model, 'id', None)

                self.logger.info(
                    f"Successfully added {self._entity_class.__name__} with ID: {model_id}",
                    extra={
                        "event_type": "entity_add_success",
                        "entity_type": self._entity_class.__name__,
                        "entity_id": model_id
                    }
                )

                return self._to_domain(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error adding {self._entity_class.__name__}: {error_msg}",
                extra={
                    "event_type": "entity_add_error",
                    "entity_type": self._entity_class.__name__,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error adding {self._entity_class.__name__}: {error_msg}")

    def update(self, entity: T) -> T:
        """
        Update an existing entity.

        Args:
            entity: The entity to update.

        Returns:
            The updated entity.
        """
        try:
            entity_id = getattr(entity, 'id', None)
            if entity_id is None:
                error_msg = "Cannot update entity without ID"
                self.logger.error(
                    error_msg,
                    extra={
                        "event_type": "entity_update_error",
                        "entity_type": self._entity_class.__name__,
                        "reason": "missing_id"
                    }
                )
                raise RepositoryError(error_msg)

            self.logger.info(
                f"Updating {self._entity_class.__name__} with ID: {entity_id}",
                extra={
                    "event_type": "entity_update",
                    "entity_type": self._entity_class.__name__,
                    "entity_id": entity_id
                }
            )

            with self.session_scope() as session:
                model = session.get(self._model_class, entity_id)
                if model is None:
                    error_msg = f"Entity with ID {entity_id} not found"
                    self.logger.warning(
                        error_msg,
                        extra={
                            "event_type": "entity_update_failed",
                            "entity_type": self._entity_class.__name__,
                            "entity_id": entity_id,
                            "reason": "not_found"
                        }
                    )
                    raise RepositoryError(error_msg)

                self._update_model(model, entity)

                self.logger.info(
                    f"Successfully updated {self._entity_class.__name__} with ID: {entity_id}",
                    extra={
                        "event_type": "entity_update_success",
                        "entity_type": self._entity_class.__name__,
                        "entity_id": entity_id
                    }
                )

                return self._to_domain(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating {self._entity_class.__name__}: {error_msg}",
                extra={
                    "event_type": "entity_update_error",
                    "entity_type": self._entity_class.__name__,
                    "entity_id": getattr(entity, 'id', None),
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error updating {self._entity_class.__name__}: {error_msg}")

    def delete(self, entity_id: int) -> bool:
        """
        Delete an entity by its ID.

        Args:
            entity_id: The ID of the entity to delete.

        Returns:
            True if the entity was deleted, False otherwise.
        """
        try:
            self.logger.info(
                f"Deleting {self._model_class.__name__} with ID: {entity_id}",
                extra={
                    "event_type": "entity_delete",
                    "entity_type": self._model_class.__name__,
                    "entity_id": entity_id
                }
            )

            with self.session_scope() as session:
                model = session.get(self._model_class, entity_id)
                if model is None:
                    self.logger.info(
                        f"No {self._model_class.__name__} found with ID: {entity_id} to delete",
                        extra={
                            "event_type": "entity_delete_failed",
                            "entity_type": self._model_class.__name__,
                            "entity_id": entity_id,
                            "reason": "not_found"
                        }
                    )
                    return False

                session.delete(model)

                self.logger.info(
                    f"Successfully deleted {self._model_class.__name__} with ID: {entity_id}",
                    extra={
                        "event_type": "entity_delete_success",
                        "entity_type": self._model_class.__name__,
                        "entity_id": entity_id
                    }
                )

                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error deleting {self._model_class.__name__} with ID {entity_id}: {error_msg}",
                extra={
                    "event_type": "entity_delete_error",
                    "entity_type": self._model_class.__name__,
                    "entity_id": entity_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error deleting {self._model_class.__name__} with ID {entity_id}: {error_msg}")

    def _to_domain(self, model: M) -> T:
        """
        Convert a SQLAlchemy model to a domain entity.

        Implementation should include appropriate logging and error handling.
        Example:
        ```python
        try:
            self.logger.debug(
                f"Converting {self._model_class.__name__} model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id
                }
            )

            # Conversion logic here

            return entity
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise
        ```

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        raise NotImplementedError("Subclasses must implement _to_domain")

    def _to_model(self, entity: T) -> M:
        """
        Convert a domain entity to a SQLAlchemy model.

        Implementation should include appropriate logging and error handling.
        Example:
        ```python
        try:
            entity_id = entity.id if hasattr(entity, 'id') else "new"
            self.logger.debug(
                f"Converting {self._entity_class.__name__} domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "entity_id": entity_id
                }
            )

            # Conversion logic here

            return model
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "entity_id": entity.id if entity and hasattr(entity, 'id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise
        ```

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        raise NotImplementedError("Subclasses must implement _to_model")

    def _find_first(self, **kwargs) -> Optional[T]:
        """
        Generic "filter by column=value" helper.

        Example:
            repo._find_first(name="foo") will do
            session.query(Model).filter_by(name="foo").first() and convert to domain.

        Args:
            **kwargs: The filter criteria as keyword arguments.

        Returns:
            The domain entity if found, None otherwise.

        Raises:
            RepositoryError: If there is an error finding the entity.
        """
        try:
            self.logger.info(
                f"Finding {self._model_class.__name__} by criteria",
                extra={
                    "event_type": "entity_lookup",
                    "lookup_type": "filter",
                    "entity_type": self._model_class.__name__,
                    "criteria": str(kwargs)
                }
            )

            model = self._session.query(self._model_class).filter_by(**kwargs).first()

            if model is None:
                self.logger.info(
                    f"No {self._model_class.__name__} found matching criteria",
                    extra={
                        "event_type": "entity_lookup_failed",
                        "lookup_type": "filter",
                        "entity_type": self._model_class.__name__,
                        "criteria": str(kwargs),
                        "reason": "not_found"
                    }
                )
                return None

            self.logger.info(
                f"Found {self._model_class.__name__} with ID: {model.id}",
                extra={
                    "event_type": "entity_lookup_success",
                    "lookup_type": "filter",
                    "entity_type": self._model_class.__name__,
                    "entity_id": model.id
                }
            )

            self.rate_limited_logger.debug(
                f"Converting {self._model_class.__name__} [id={model.id}] to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "entity_type": self._model_class.__name__
                }
            )

            return self._to_domain(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in _find_first: {error_msg}",
                extra={
                    "event_type": "entity_lookup_error",
                    "lookup_type": "filter",
                    "entity_type": self._model_class.__name__,
                    "criteria": str(kwargs),
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error finding {self._model_class.__name__}: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in _find_first: {error_msg}",
                extra={
                    "event_type": "entity_lookup_error",
                    "lookup_type": "filter",
                    "entity_type": self._model_class.__name__,
                    "criteria": str(kwargs),
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error finding {self._model_class.__name__}: {error_msg}")

    def _stamp_updated(self, model: M) -> None:
        """
        Update the updated_at timestamp on a model if it has that field.

        Args:
            model: The SQLAlchemy model to update.
        """
        if hasattr(model, "updated_at"):
            model.updated_at = datetime.utcnow()

    def _update_model(self, model: M, entity: T) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Implementation should include appropriate logging and error handling.
        Example:
        ```python
        try:
            self.logger.debug(
                f"Updating {self._model_class.__name__} model from domain entity",
                extra={
                    "event_type": "model_update",
                    "entity_id": model.id
                }
            )

            # Check for significant changes and log them
            if model.some_field != entity.some_field:
                self.logger.info(
                    f"Changing {self._model_class.__name__} field value",
                    extra={
                        "event_type": "field_change",
                        "entity_id": model.id,
                        "field": "some_field",
                        "old_value": model.some_field,
                        "new_value": entity.some_field
                    }
                )

            # Update logic here
            model.some_field = entity.some_field

            # Update timestamp
            self._stamp_updated(model)

            self.logger.debug(
                f"Successfully updated {self._model_class.__name__} model",
                extra={
                    "event_type": "model_update_success",
                    "entity_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating model: {error_msg}",
                extra={
                    "event_type": "model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise
        ```

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        raise NotImplementedError("Subclasses must implement _update_model")
