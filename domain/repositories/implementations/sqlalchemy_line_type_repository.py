# heijunka/domain/repositories/implementations/sqlalchemy_line_type_repository.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from domain.value_objects.line_type import LineType
from domain.models.LineTypeModel import LineTypeModel
from domain.repositories.interfaces.line_type_repository import LineTypeRepositoryInterface
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger


class SqlAlchemyLineTypeRepository(BaseSqlAlchemyRepository, LineTypeRepositoryInterface):
    """
    SQLAlchemy implementation of the LineTypeRepository interface.

    This class provides the actual implementation for accessing and manipulating
    LineType entities in the database using SQLAlchemy.
    """

    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session: The SQLAlchemy session to use
        """
        super().__init__(session, LineTypeModel, LineType)
        self.logger = get_logger("heijunka.repositories.line_type")
        self.rate_limited_logger = get_logger("heijunka.repositories.line_type", rate_limit=True)

    def _to_domain(self, model: LineTypeModel) -> LineType:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            self.logger.debug(
                "Converting line type model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "entity_name": model.name
                }
            )

            line_type = model.to_value_object()

            self.logger.debug(
                "Successfully converted line type model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion_success",
                    "entity_id": model.id
                }
            )

            return line_type
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting line type model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: LineType) -> LineTypeModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            self.logger.debug(
                "Converting line type domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "entity_name": entity.name
                }
            )

            model = LineTypeModel.from_value_object(entity)

            self.logger.debug(
                "Successfully converted line type domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion_success",
                    "entity_name": entity.name
                }
            )

            return model
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting line type domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "entity_name": entity.name if entity and hasattr(entity, 'name') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: LineTypeModel, entity: LineType) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            self.logger.debug(
                "Updating line type model from domain entity",
                extra={
                    "event_type": "line_type_model_update",
                    "entity_id": model.id,
                    "entity_name": model.name
                }
            )

            # Check for significant changes and log them
            if model.name != entity.name:
                self.logger.info(
                    "Changing line type name",
                    extra={
                        "event_type": "line_type_field_change",
                        "entity_id": model.id,
                        "field": "name",
                        "old_value": model.name,
                        "new_value": entity.name
                    }
                )

            if model.description != entity.description:
                self.logger.info(
                    "Changing line type description",
                    extra={
                        "event_type": "line_type_field_change",
                        "entity_id": model.id,
                        "field": "description",
                        "old_value": model.description,
                        "new_value": entity.description
                    }
                )

            # Update the model
            model.name = entity.name
            model.description = entity.description

            self.logger.debug(
                "Successfully updated line type model",
                extra={
                    "event_type": "line_type_model_update_success",
                    "entity_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating line type model: {error_msg}",
                extra={
                    "event_type": "line_type_model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def add(self, line_type: LineType) -> LineType:
        """
        Add a new line type to the repository.

        Args:
            line_type: The line type to add

        Returns:
            The added line type with updated ID
        """
        try:
            self.logger.info(
                "Adding new line type",
                extra={
                    "event_type": "line_type_add",
                    "line_type_name": line_type.name
                }
            )

            with self.session_scope() as session:
                model = self._to_model(line_type)
                session.add(model)
                session.flush()

                self.logger.info(
                    "Successfully added line type",
                    extra={
                        "event_type": "line_type_add_success",
                        "line_type_id": model.id,
                        "line_type_name": model.name
                    }
                )

                return self._to_domain(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error adding line type: {error_msg}",
                extra={
                    "event_type": "line_type_add_error",
                    "line_type_name": line_type.name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to add line type: {error_msg}")

    def get_by_id(self, line_type_id: int) -> Optional[LineType]:
        """
        Get a line type by its ID.

        Args:
            line_type_id: The ID of the line type to retrieve

        Returns:
            The line type if found, None otherwise
        """
        try:
            self.logger.info(
                f"Retrieving line type by ID: {line_type_id}",
                extra={
                    "event_type": "line_type_lookup",
                    "lookup_type": "id",
                    "line_type_id": line_type_id
                }
            )

            model = self._session.query(LineTypeModel).filter(LineTypeModel.id == line_type_id).first()

            if not model:
                self.logger.info(
                    f"No line type found with ID: {line_type_id}",
                    extra={
                        "event_type": "line_type_lookup_failed",
                        "lookup_type": "id",
                        "line_type_id": line_type_id,
                        "reason": "not_found"
                    }
                )
                return None

            self.logger.info(
                f"Found line type with ID: {line_type_id}",
                extra={
                    "event_type": "line_type_lookup_success",
                    "lookup_type": "id",
                    "line_type_id": line_type_id,
                    "line_type_name": model.name
                }
            )

            return self._to_domain(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving line type by ID: {error_msg}",
                extra={
                    "event_type": "line_type_lookup_error",
                    "lookup_type": "id",
                    "line_type_id": line_type_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get line type by ID: {error_msg}")

    def get_by_name(self, name: str) -> Optional[LineType]:
        """
        Get a line type by its name.

        Args:
            name: The name of the line type to retrieve

        Returns:
            The line type if found, None otherwise
        """
        try:
            self.logger.info(
                f"Retrieving line type by name: {name}",
                extra={
                    "event_type": "line_type_lookup",
                    "lookup_type": "name",
                    "line_type_name": name
                }
            )

            model = self._session.query(LineTypeModel).filter(LineTypeModel.name == name).first()

            if not model:
                self.logger.info(
                    f"No line type found with name: {name}",
                    extra={
                        "event_type": "line_type_lookup_failed",
                        "lookup_type": "name",
                        "line_type_name": name,
                        "reason": "not_found"
                    }
                )
                return None

            self.logger.info(
                f"Found line type with name: {name}",
                extra={
                    "event_type": "line_type_lookup_success",
                    "lookup_type": "name",
                    "line_type_id": model.id,
                    "line_type_name": name
                }
            )

            return self._to_domain(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving line type by name: {error_msg}",
                extra={
                    "event_type": "line_type_lookup_error",
                    "lookup_type": "name",
                    "line_type_name": name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get line type by name: {error_msg}")

    def get_all(self) -> List[LineType]:
        """
        Get all line types.

        Returns:
            A list of all line types
        """
        try:
            self.logger.info(
                "Retrieving all line types",
                extra={
                    "event_type": "line_type_list_all"
                }
            )

            models = self._session.query(LineTypeModel).all()
            line_types = [self._to_domain(model) for model in models]

            count = len(line_types)
            self.logger.info(
                f"Retrieved {count} line types",
                extra={
                    "event_type": "line_type_list_all_success",
                    "count": count
                }
            )

            return line_types
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving all line types: {error_msg}",
                extra={
                    "event_type": "line_type_list_all_error",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get all line types: {error_msg}")

    def update(self, line_type_id: int, line_type: LineType) -> LineType:
        """
        Update an existing line type.

        Args:
            line_type_id: The ID of the line type to update
            line_type: The new line type value object

        Returns:
            The updated line type
        """
        try:
            self.logger.info(
                f"Updating line type with ID: {line_type_id}",
                extra={
                    "event_type": "line_type_update",
                    "line_type_id": line_type_id,
                    "line_type_name": line_type.name
                }
            )

            with self.session_scope() as session:
                model = session.query(LineTypeModel).filter(LineTypeModel.id == line_type_id).first()
                if not model:
                    error_msg = f"Line type with ID {line_type_id} not found"
                    self.logger.warning(
                        error_msg,
                        extra={
                            "event_type": "line_type_update_failed",
                            "line_type_id": line_type_id,
                            "reason": "not_found"
                        }
                    )
                    raise RepositoryError(error_msg)

                self._update_model(model, line_type)
                session.flush()

                self.logger.info(
                    f"Successfully updated line type with ID: {line_type_id}",
                    extra={
                        "event_type": "line_type_update_success",
                        "line_type_id": line_type_id,
                        "line_type_name": model.name
                    }
                )

                return self._to_domain(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating line type: {error_msg}",
                extra={
                    "event_type": "line_type_update_error",
                    "line_type_id": line_type_id,
                    "line_type_name": line_type.name if line_type else None,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to update line type: {error_msg}")

    def delete(self, line_type_id: int) -> bool:
        """
        Delete a line type by its ID.

        Args:
            line_type_id: The ID of the line type to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            self.logger.info(
                f"Deleting line type with ID: {line_type_id}",
                extra={
                    "event_type": "line_type_delete",
                    "line_type_id": line_type_id
                }
            )

            with self.session_scope() as session:
                model = session.query(LineTypeModel).filter(LineTypeModel.id == line_type_id).first()
                if not model:
                    self.logger.info(
                        f"No line type found with ID: {line_type_id} to delete",
                        extra={
                            "event_type": "line_type_delete_failed",
                            "line_type_id": line_type_id,
                            "reason": "not_found"
                        }
                    )
                    return False

                # Log the name before deletion for audit purposes
                line_type_name = model.name

                session.delete(model)

                self.logger.info(
                    f"Successfully deleted line type with ID: {line_type_id}",
                    extra={
                        "event_type": "line_type_delete_success",
                        "line_type_id": line_type_id,
                        "line_type_name": line_type_name
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error deleting line type: {error_msg}",
                extra={
                    "event_type": "line_type_delete_error",
                    "line_type_id": line_type_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to delete line type: {error_msg}")
