from contextlib import contextmanager
from typing import Optional, List, Generator
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.entities.department import Department
from domain.models.DepartmentModel import DepartmentModel
from domain.repositories.interfaces.department_repository import DepartmentRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger


class SqlAlchemyDepartmentRepository(BaseSqlAlchemyRepository[Department, DepartmentModel], DepartmentRepositoryInterface):
    """
    SQLAlchemy implementation of the DepartmentRepository interface.
    """

    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session: The SQLAlchemy session to use for database operations.
        """
        super().__init__(session, DepartmentModel, Department)
        self.logger = get_logger("heijunka.repositories.department")
        self.rate_limited_logger = get_logger("heijunka.repositories.department", rate_limit=True)

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
                    "repository": "department"
                }
            )
            raise RepositoryError(f"Database error: {error_msg}")
        except Exception as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in department repository: {error_msg}",
                extra={
                    "event_type": "unexpected_error",
                    "error_type": type(e).__name__,
                    "repository": "department"
                }
            )
            raise RepositoryError(f"Repository error: {error_msg}")

    def get_by_name(self, department_name: str) -> Optional[Department]:
        """
        Retrieve a department by its name.

        Args:
            department_name: The name of the department to retrieve.

        Returns:
            The department if found, None otherwise.
        """
        try:
            self.logger.info(
                f"Retrieving department by name: {department_name}",
                extra={
                    "event_type": "department_lookup",
                    "lookup_type": "name",
                    "department_name": department_name
                }
            )

            department_model = self._session.query(DepartmentModel).filter(
                DepartmentModel.name == department_name
            ).first()

            if department_model is None:
                self.logger.info(
                    f"No department found with name: {department_name}",
                    extra={
                        "event_type": "department_lookup_failed",
                        "lookup_type": "name",
                        "department_name": department_name,
                        "reason": "not_found"
                    }
                )
                return None

            self.logger.info(
                f"Found department with ID: {department_model.id}",
                extra={
                    "event_type": "department_lookup_success",
                    "lookup_type": "name",
                    "department_name": department_name,
                    "department_id": department_model.id
                }
            )

            return self._to_domain(department_model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving department by name: {error_msg}",
                extra={
                    "event_type": "department_lookup_error",
                    "lookup_type": "name",
                    "department_name": department_name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving department by name: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error retrieving department by name: {error_msg}",
                extra={
                    "event_type": "department_lookup_error",
                    "lookup_type": "name",
                    "department_name": department_name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving department by name: {error_msg}")

    def get_all_with_groups(self) -> List[Department]:
        """
        Retrieve all departments with their associated groups.

        Returns:
            A list of all departments with their associated groups.
        """
        try:
            self.logger.info(
                "Retrieving all departments with groups",
                extra={
                    "event_type": "departments_with_groups_lookup"
                }
            )

            from domain.models.GroupModel import GroupModel

            departments = []
            department_models = self._session.query(DepartmentModel).all()

            department_count = len(department_models)
            self.logger.info(
                f"Found {department_count} departments",
                extra={
                    "event_type": "departments_with_groups_lookup_success",
                    "department_count": department_count
                }
            )

            for department_model in department_models:
                department = self._to_domain(department_model)
                departments.append(department)

                self.rate_limited_logger.debug(
                    f"Processed department: {department.name}",
                    event_type="department_processed",
                    identifier=str(department.id),
                    extra={
                        "department_id": department.id,
                        "department_name": department.name
                    }
                )

            return departments
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving departments with groups: {error_msg}",
                extra={
                    "event_type": "departments_with_groups_lookup_error",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving departments with groups: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error retrieving departments with groups: {error_msg}",
                extra={
                    "event_type": "departments_with_groups_lookup_error",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving departments with groups: {error_msg}")

    def _to_domain(self, model: DepartmentModel) -> Department:
        """
        Convert a DepartmentModel to a Department domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            self.logger.debug(
                "Converting department model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "department_name": model.name
                }
            )

            department = Department(
                id=model.id,
                name=model.name,
                description=model.description
            )

            self.logger.debug(
                "Successfully converted department model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion_success",
                    "entity_id": model.id
                }
            )

            return department
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting department model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: Department) -> DepartmentModel:
        """
        Convert a Department domain entity to a DepartmentModel.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            entity_id = entity.id if entity.id is not None else "new"
            self.logger.debug(
                "Converting department domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "entity_id": entity_id,
                    "department_name": entity.name
                }
            )

            model = DepartmentModel(
                name=entity.name,
                description=entity.description
            )

            if entity.id is not None:
                model.id = entity.id

            self.logger.debug(
                "Successfully converted department domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion_success",
                    "entity_id": entity_id
                }
            )

            return model
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting department domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "entity_id": entity.id if entity and hasattr(entity, 'id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: DepartmentModel, entity: Department) -> None:
        """
        Update a DepartmentModel with values from a Department domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            self.logger.debug(
                "Updating department model from domain entity",
                extra={
                    "event_type": "department_model_update",
                    "entity_id": model.id,
                    "department_name": model.name
                }
            )

            # Check for significant changes and log them
            if model.name != entity.name:
                self.logger.info(
                    "Changing department name",
                    extra={
                        "event_type": "department_field_change",
                        "entity_id": model.id,
                        "field": "name",
                        "old_value": model.name,
                        "new_value": entity.name
                    }
                )

            if model.description != entity.description:
                self.logger.info(
                    "Changing department description",
                    extra={
                        "event_type": "department_field_change",
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
                "Successfully updated department model",
                extra={
                    "event_type": "department_model_update_success",
                    "entity_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating department model: {error_msg}",
                extra={
                    "event_type": "department_model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise
