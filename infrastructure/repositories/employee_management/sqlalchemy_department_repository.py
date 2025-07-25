# domain/repositories/buses/refactored_sqlalchemy_department_repository.py
from typing import Optional, List
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import func

from domain.contexts.employee_management.entities.department import Department
from domain.models.DepartmentModel import DepartmentModel
from domain.repositories.interfaces.department_repository import DepartmentRepositoryInterface
from domain.factories.department_factory import DepartmentFactory
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger


class SqlAlchemyDepartmentRepository(BaseSqlAlchemyRepository[Department, DepartmentModel],
                                     DepartmentRepositoryInterface):
    """
    SQLAlchemy implementation of the DepartmentRepository interface.

    This repository is responsible for:
    1. Retrieving Department entities from the database
    2. Persisting Department entities to the database
    3. Converting between DepartmentModel and Department using DepartmentFactory

    It does not contain any business logic, which is encapsulated in the domain entities.
    """

    def __init__(self, session_factory):
        """
        Initialize the repository with a SQLAlchemy session factory.

        Args:
            session_factory: The SQLAlchemy session factory to use for database operations.
        """
        super().__init__(session_factory, DepartmentModel, Department)
        self.logger = get_logger("heijunka.repositories.department")
        self.rate_limited_logger = get_logger("heijunka.repositories.department", rate_limit=True)

    def get_by_name(self, department_name: str) -> Optional[Department]:
        """
        Retrieve a department by its name (case-insensitive).

        Args:
            department_name: The name of the department to retrieve.

        Returns:
            The department if found, None otherwise.

        Raises:
            RepositoryError: If there is an error retrieving the department.
        """
        try:
            self.logger.info(
                f"Entering DepartmentRepository.get_by_name (name={department_name})",
                extra={
                    "event_type": "department_lookup",
                    "lookup_type": "name",
                    "department_name": department_name
                }
            )

            with self.session_scope() as session:
                department_model = session.query(DepartmentModel).filter(
                    func.lower(DepartmentModel.name) == func.lower(department_name)
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

                self.logger.debug(
                    f"Converting DepartmentModel [id={department_model.id}] to domain Department",
                    extra={
                        "event_type": "model_to_domain_conversion",
                        "entity_id": department_model.id,
                        "entity_type": "Department"
                    }
                )

                return DepartmentFactory.create_from_model(department_model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in DepartmentRepository.get_by_name: {error_msg}",
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
                f"Unexpected error in DepartmentRepository.get_by_name: {error_msg}",
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

        Raises:
            RepositoryError: If there is an error retrieving the departments.
        """
        try:
            self.logger.info(
                "Entering DepartmentRepository.get_all_with_groups",
                extra={
                    "event_type": "departments_with_groups_lookup"
                }
            )

            with self.session_scope() as session:
                department_models = session.query(DepartmentModel).all()

                department_count = len(department_models)
                self.logger.info(
                    f"Found {department_count} departments",
                    extra={
                        "event_type": "departments_with_groups_lookup_success",
                        "department_count": department_count
                    }
                )

                departments = []
                for department_model in department_models:
                    self.logger.debug(
                        f"Converting DepartmentModel [id={department_model.id}] to domain Department",
                        extra={
                            "event_type": "model_to_domain_conversion",
                            "entity_id": department_model.id,
                            "entity_type": "Department"
                        }
                    )

                    department = DepartmentFactory.create_from_model(department_model)
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
                f"Error in DepartmentRepository.get_all_with_groups: {error_msg}",
                extra={
                    "event_type": "departments_with_groups_lookup_error",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving departments with groups: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in DepartmentRepository.get_all_with_groups: {error_msg}",
                extra={
                    "event_type": "departments_with_groups_lookup_error",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving departments with groups: {error_msg}")

    def _to_domain(self, model: DepartmentModel) -> Department:
        """
        Convert a DepartmentModel to a Department domain entity using the DepartmentFactory.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            self.logger.debug(
                f"Converting DepartmentModel [id={model.id}] to domain Department",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "entity_type": "Department"
                }
            )

            return DepartmentFactory.create_from_model(model)
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
        Convert a Department domain entity to a DepartmentModel using the DepartmentFactory.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            entity_id = entity.id if entity.id is not None else "new"
            self.logger.debug(
                f"Converting Department domain entity [id={entity_id}] to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "entity_id": entity_id,
                    "entity_type": "Department"
                }
            )

            return DepartmentFactory.to_model(entity)
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
        Update a DepartmentModel with values from a Department domain entity using the DepartmentFactory.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            self.logger.debug(
                f"Updating DepartmentModel [id={model.id}] from domain entity",
                extra={
                    "event_type": "model_update",
                    "entity_id": model.id,
                    "entity_type": "Department"
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

            # Use the factory to update the model
            DepartmentFactory.update_model(model, entity)

            # Update timestamp if available
            self._stamp_updated(model)

            self.logger.debug(
                "Successfully updated department model",
                extra={
                    "event_type": "model_update_success",
                    "entity_id": model.id,
                    "entity_type": "Department"
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating department model: {error_msg}",
                extra={
                    "event_type": "model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise
