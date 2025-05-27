# heijunka/domain/repositories/implementations/sqlalchemy_employee_training_repository.py
from typing import List, Optional, Generator
from datetime import date
from contextlib import contextmanager
from sqlalchemy import and_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from domain.value_objects.employee_training import EmployeeTraining
from domain.models.EmployeeTrainingModel import EmployeeTrainingModel
from domain.repositories.interfaces.employee_training_repository import EmployeeTrainingRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger


class SqlAlchemyEmployeeTrainingRepository(BaseSqlAlchemyRepository, EmployeeTrainingRepositoryInterface):
    """
    SQLAlchemy implementation of the EmployeeTrainingRepository interface.

    This class provides the actual implementation for accessing and manipulating
    employee training records in the database using SQLAlchemy.
    """

    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session: The SQLAlchemy session to use for database operations.
        """
        super().__init__(session, EmployeeTrainingModel, EmployeeTraining)
        self.logger = get_logger("heijunka.repositories.employee_training")
        self.rate_limited_logger = get_logger("heijunka.repositories.employee_training", rate_limit=True)

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
                    "repository": "employee_training"
                }
            )
            raise RepositoryError(f"Database error: {error_msg}")
        except Exception as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in employee training repository: {error_msg}",
                extra={
                    "event_type": "unexpected_error",
                    "error_type": type(e).__name__,
                    "repository": "employee_training"
                }
            )
            raise RepositoryError(f"Repository error: {error_msg}")

    def add(self, training: EmployeeTraining) -> EmployeeTraining:
        """
        Add a new training record.

        Args:
            training: The training record to add

        Returns:
            The added training record
        """
        try:
            self.logger.info(
                "Adding new employee training record",
                extra={
                    "event_type": "employee_training_add",
                    "employee_id": training.employee_id,
                    "workstation_id": training.workstation_id
                }
            )

            with self.session_scope() as session:
                model = self._to_model(training)
                session.add(model)
                session.flush()  # Flush to get the ID

                self.logger.info(
                    "Successfully added employee training record",
                    extra={
                        "event_type": "employee_training_add_success",
                        "entity_id": model.id,
                        "employee_id": training.employee_id,
                        "workstation_id": training.workstation_id
                    }
                )

                return self._to_domain(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error adding employee training record: {error_msg}",
                extra={
                    "event_type": "employee_training_add_error",
                    "employee_id": training.employee_id,
                    "workstation_id": training.workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to add training record: {error_msg}")

    def get_by_employee_and_workstation(self, employee_id: int, workstation_id: int) -> Optional[EmployeeTraining]:
        """
        Get a training record for a specific employee and workstation.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation

        Returns:
            The training record if found, None otherwise
        """
        try:
            self.logger.info(
                "Retrieving training record for employee and workstation",
                extra={
                    "event_type": "employee_training_lookup",
                    "lookup_type": "employee_and_workstation",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id
                }
            )

            model = self._session.query(EmployeeTrainingModel).filter(
                and_(
                    EmployeeTrainingModel.employee_id == employee_id,
                    EmployeeTrainingModel.station_id == workstation_id
                )
            ).first()

            if not model:
                self.logger.info(
                    "No training record found for employee and workstation",
                    extra={
                        "event_type": "employee_training_lookup_failed",
                        "lookup_type": "employee_and_workstation",
                        "employee_id": employee_id,
                        "workstation_id": workstation_id,
                        "reason": "not_found"
                    }
                )
                return None

            self.logger.info(
                "Found training record for employee and workstation",
                extra={
                    "event_type": "employee_training_lookup_success",
                    "lookup_type": "employee_and_workstation",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "entity_id": model.id
                }
            )

            return self._to_domain(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving training record for employee and workstation: {error_msg}",
                extra={
                    "event_type": "employee_training_lookup_error",
                    "lookup_type": "employee_and_workstation",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get training record: {error_msg}")

    def get_by_employee(self, employee_id: int) -> List[EmployeeTraining]:
        """
        Get all training records for a specific employee.

        Args:
            employee_id: The ID of the employee

        Returns:
            A list of training records
        """
        try:
            self.logger.info(
                "Retrieving training records for employee",
                extra={
                    "event_type": "employee_training_lookup",
                    "lookup_type": "employee",
                    "employee_id": employee_id
                }
            )

            models = self._session.query(EmployeeTrainingModel).filter(
                EmployeeTrainingModel.employee_id == employee_id
            ).all()

            record_count = len(models)
            self.logger.info(
                f"Found {record_count} training records for employee",
                extra={
                    "event_type": "employee_training_lookup_success",
                    "lookup_type": "employee",
                    "employee_id": employee_id,
                    "record_count": record_count
                }
            )

            return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving training records for employee: {error_msg}",
                extra={
                    "event_type": "employee_training_lookup_error",
                    "lookup_type": "employee",
                    "employee_id": employee_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get training records by employee: {error_msg}")

    def get_by_workstation(self, workstation_id: int) -> List[EmployeeTraining]:
        """
        Get all training records for a specific workstation.

        Args:
            workstation_id: The ID of the workstation

        Returns:
            A list of training records
        """
        try:
            self.logger.info(
                "Retrieving training records for workstation",
                extra={
                    "event_type": "employee_training_lookup",
                    "lookup_type": "workstation",
                    "workstation_id": workstation_id
                }
            )

            models = self._session.query(EmployeeTrainingModel).filter(
                EmployeeTrainingModel.station_id == workstation_id
            ).all()

            record_count = len(models)
            self.logger.info(
                f"Found {record_count} training records for workstation",
                extra={
                    "event_type": "employee_training_lookup_success",
                    "lookup_type": "workstation",
                    "workstation_id": workstation_id,
                    "record_count": record_count
                }
            )

            return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving training records for workstation: {error_msg}",
                extra={
                    "event_type": "employee_training_lookup_error",
                    "lookup_type": "workstation",
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get training records by workstation: {error_msg}")

    def get_completed_trainings(self, employee_id: int) -> List[EmployeeTraining]:
        """
        Get all completed training records for a specific employee.

        Args:
            employee_id: The ID of the employee

        Returns:
            A list of completed training records
        """
        try:
            self.logger.info(
                "Retrieving completed training records for employee",
                extra={
                    "event_type": "employee_training_lookup",
                    "lookup_type": "completed_trainings",
                    "employee_id": employee_id
                }
            )

            models = self._session.query(EmployeeTrainingModel).filter(
                and_(
                    EmployeeTrainingModel.employee_id == employee_id,
                    EmployeeTrainingModel.date_completed != None
                )
            ).all()

            record_count = len(models)
            self.logger.info(
                f"Found {record_count} completed training records for employee",
                extra={
                    "event_type": "employee_training_lookup_success",
                    "lookup_type": "completed_trainings",
                    "employee_id": employee_id,
                    "record_count": record_count
                }
            )

            return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving completed training records for employee: {error_msg}",
                extra={
                    "event_type": "employee_training_lookup_error",
                    "lookup_type": "completed_trainings",
                    "employee_id": employee_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get completed training records: {error_msg}")

    def get_required_trainings(self, employee_id: int) -> List[EmployeeTraining]:
        """
        Get all required training records for a specific employee.

        Args:
            employee_id: The ID of the employee

        Returns:
            A list of required training records
        """
        try:
            self.logger.info(
                "Retrieving required training records for employee",
                extra={
                    "event_type": "employee_training_lookup",
                    "lookup_type": "required_trainings",
                    "employee_id": employee_id
                }
            )

            models = self._session.query(EmployeeTrainingModel).filter(
                and_(
                    EmployeeTrainingModel.employee_id == employee_id,
                    EmployeeTrainingModel.required_training == True
                )
            ).all()

            record_count = len(models)
            self.logger.info(
                f"Found {record_count} required training records for employee",
                extra={
                    "event_type": "employee_training_lookup_success",
                    "lookup_type": "required_trainings",
                    "employee_id": employee_id,
                    "record_count": record_count
                }
            )

            return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving required training records for employee: {error_msg}",
                extra={
                    "event_type": "employee_training_lookup_error",
                    "lookup_type": "required_trainings",
                    "employee_id": employee_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get required training records: {error_msg}")

    def update_training_status(self, employee_id: int, workstation_id: int, 
                              required: bool, date_completed: Optional[date] = None) -> Optional[EmployeeTraining]:
        """
        Update the status of a training record.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            required: Whether the training is required
            date_completed: The date the training was completed, or None if not completed

        Returns:
            The updated training record if found, None otherwise
        """
        try:
            self.logger.info(
                "Updating training status",
                extra={
                    "event_type": "employee_training_update",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id
                }
            )

            with self.session_scope() as session:
                model = session.query(EmployeeTrainingModel).filter(
                    and_(
                        EmployeeTrainingModel.employee_id == employee_id,
                        EmployeeTrainingModel.station_id == workstation_id
                    )
                ).first()

                if not model:
                    self.logger.info(
                        "No training record found to update",
                        extra={
                            "event_type": "employee_training_update_failed",
                            "employee_id": employee_id,
                            "workstation_id": workstation_id,
                            "reason": "not_found"
                        }
                    )
                    return None

                # Log changes
                if model.required_training != required:
                    self.logger.info(
                        "Changing training required status",
                        extra={
                            "event_type": "employee_training_field_change",
                            "entity_id": model.id,
                            "field": "required_training",
                            "old_value": model.required_training,
                            "new_value": required
                        }
                    )

                if model.date_completed != date_completed:
                    self.logger.info(
                        "Changing training completion date",
                        extra={
                            "event_type": "employee_training_field_change",
                            "entity_id": model.id,
                            "field": "date_completed",
                            "old_value": model.date_completed.isoformat() if model.date_completed else None,
                            "new_value": date_completed.isoformat() if date_completed else None
                        }
                    )

                # Update the model
                model.required_training = required
                model.date_completed = date_completed

                session.flush()

                self.logger.info(
                    "Successfully updated training status",
                    extra={
                        "event_type": "employee_training_update_success",
                        "entity_id": model.id,
                        "employee_id": employee_id,
                        "workstation_id": workstation_id
                    }
                )

                return self._to_domain(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating training status: {error_msg}",
                extra={
                    "event_type": "employee_training_update_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to update training status: {error_msg}")

    def delete(self, employee_id: int, workstation_id: int) -> bool:
        """
        Delete a training record.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation

        Returns:
            True if deleted, False if not found
        """
        try:
            self.logger.info(
                "Deleting training record",
                extra={
                    "event_type": "employee_training_delete",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id
                }
            )

            with self.session_scope() as session:
                model = session.query(EmployeeTrainingModel).filter(
                    and_(
                        EmployeeTrainingModel.employee_id == employee_id,
                        EmployeeTrainingModel.station_id == workstation_id
                    )
                ).first()

                if not model:
                    self.logger.info(
                        "No training record found to delete",
                        extra={
                            "event_type": "employee_training_delete_failed",
                            "employee_id": employee_id,
                            "workstation_id": workstation_id,
                            "reason": "not_found"
                        }
                    )
                    return False

                entity_id = model.id
                session.delete(model)

                self.logger.info(
                    "Successfully deleted training record",
                    extra={
                        "event_type": "employee_training_delete_success",
                        "entity_id": entity_id,
                        "employee_id": employee_id,
                        "workstation_id": workstation_id
                    }
                )

                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error deleting training record: {error_msg}",
                extra={
                    "event_type": "employee_training_delete_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to delete training record: {error_msg}")

    def get(self, id: int) -> Optional[EmployeeTraining]:
        """
        Get an entity by ID.

        This method is required by the BaseRepository interface but is not directly applicable
        for EmployeeTraining since it's identified by a composite key.

        Args:
            id: The ID of the entity to retrieve

        Returns:
            None (not directly applicable for EmployeeTraining)
        """
        try:
            self.logger.info(
                f"Attempting to retrieve employee training by ID: {id}",
                extra={
                    "event_type": "employee_training_lookup",
                    "lookup_type": "id",
                    "entity_id": id
                }
            )

            self.logger.info(
                "Employee training is identified by composite key (employee_id, workstation_id), not by ID",
                extra={
                    "event_type": "employee_training_lookup_failed",
                    "lookup_type": "id",
                    "entity_id": id,
                    "reason": "not_applicable"
                }
            )

            return None
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in get method: {error_msg}",
                extra={
                    "event_type": "employee_training_lookup_error",
                    "lookup_type": "id",
                    "entity_id": id,
                    "error_type": type(e).__name__
                }
            )
            return None

    def get_all_entities(self) -> List[EmployeeTraining]:
        """
        Get all entities.

        Returns:
            A list of all training records
        """
        try:
            self.logger.info(
                "Retrieving all employee training records",
                extra={
                    "event_type": "employee_training_list_all"
                }
            )

            models = self._session.query(EmployeeTrainingModel).all()

            record_count = len(models)
            self.logger.info(
                f"Retrieved {record_count} employee training records",
                extra={
                    "event_type": "employee_training_list_all_success",
                    "record_count": record_count
                }
            )

            return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving all employee training records: {error_msg}",
                extra={
                    "event_type": "employee_training_list_all_error",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get all training records: {error_msg}")

    def _to_domain(self, model: EmployeeTrainingModel) -> EmployeeTraining:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            self.logger.debug(
                "Converting employee training model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "employee_id": model.employee_id,
                    "workstation_id": model.station_id
                }
            )

            training = EmployeeTraining(
                employee_id=model.employee_id,
                workstation_id=model.station_id,
                required_training=model.required_training,
                date_completed=model.date_completed
            )

            self.logger.debug(
                "Successfully converted employee training model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion_success",
                    "entity_id": model.id
                }
            )

            return training
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting employee training model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: EmployeeTraining) -> EmployeeTrainingModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            self.logger.debug(
                "Converting employee training domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "employee_id": entity.employee_id,
                    "workstation_id": entity.workstation_id
                }
            )

            model = EmployeeTrainingModel(
                employee_id=entity.employee_id,
                station_id=entity.workstation_id,
                required_training=entity.required_training,
                date_completed=entity.date_completed
            )

            self.logger.debug(
                "Successfully converted employee training domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion_success",
                    "employee_id": entity.employee_id,
                    "workstation_id": entity.workstation_id
                }
            )

            return model
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting employee training domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "employee_id": entity.employee_id if entity and hasattr(entity, 'employee_id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: EmployeeTrainingModel, entity: EmployeeTraining) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            self.logger.debug(
                "Updating employee training model from domain entity",
                extra={
                    "event_type": "employee_training_model_update",
                    "entity_id": model.id,
                    "employee_id": model.employee_id,
                    "workstation_id": model.station_id
                }
            )

            # Check for significant changes and log them
            if model.required_training != entity.required_training:
                self.logger.info(
                    "Changing employee training required status",
                    extra={
                        "event_type": "employee_training_field_change",
                        "entity_id": model.id,
                        "field": "required_training",
                        "old_value": model.required_training,
                        "new_value": entity.required_training
                    }
                )

            if model.date_completed != entity.date_completed:
                self.logger.info(
                    "Changing employee training completion date",
                    extra={
                        "event_type": "employee_training_field_change",
                        "entity_id": model.id,
                        "field": "date_completed",
                        "old_value": model.date_completed.isoformat() if model.date_completed else None,
                        "new_value": entity.date_completed.isoformat() if entity.date_completed else None
                    }
                )

            # Update the model
            model.employee_id = entity.employee_id
            model.station_id = entity.workstation_id
            model.required_training = entity.required_training
            model.date_completed = entity.date_completed

            self.logger.debug(
                "Successfully updated employee training model",
                extra={
                    "event_type": "employee_training_model_update_success",
                    "entity_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating employee training model: {error_msg}",
                extra={
                    "event_type": "employee_training_model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise
