# heijunka/domain/repositories/implementations/sqlalchemy_employee_training_repository.py
from typing import List, Optional, Type
from datetime import date
from sqlalchemy import and_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from domain.value_objects.employee_training import EmployeeTraining
from domain.models.EmployeeTrainingModel import EmployeeTrainingModel
from domain.repositories.interfaces.employee_training_repository import EmployeeTrainingRepositoryInterface
from domain.factories.employee_training_factory import EmployeeTrainingFactory
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger


class SqlAlchemyEmployeeTrainingRepository(BaseSqlAlchemyRepository[EmployeeTraining, EmployeeTrainingModel], EmployeeTrainingRepositoryInterface):
    """
    SQLAlchemy implementation of the EmployeeTrainingRepository interface.

    This class provides the actual implementation for accessing and manipulating
    employee training records in the database using SQLAlchemy.
    """

    def __init__(self, session_factory):
        """
        Initialize the repository with a SQLAlchemy session factory.

        Args:
            session_factory: The SQLAlchemy session factory to use for database operations.
        """
        super().__init__(session_factory, EmployeeTrainingModel, EmployeeTraining)
        self.logger = get_logger("heijunka.repositories.employee_training")
        self.rate_limited_logger = get_logger("heijunka.repositories.employee_training", rate_limit=True)

    def add(self, training: EmployeeTraining) -> EmployeeTraining:
        """
        Add a new training record.

        Args:
            training: The training record to add

        Returns:
            The added training record

        Raises:
            RepositoryError: If there was an error adding the training record
        """
        self.logger.info(
            "Entering EmployeeTrainingRepository.add",
            extra={
                "event_type": "employee_training_add",
                "employee_id": training.employee_id,
                "workstation_id": training.workstation_id
            }
        )

        try:
            with self.session_scope() as session:
                model = EmployeeTrainingFactory.create_from_entity(training)
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

                return EmployeeTrainingFactory.create_from_model(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeTrainingRepository.add: {error_msg}",
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

        Raises:
            RepositoryError: If there was an error retrieving the training record
        """
        self.logger.info(
            "Entering EmployeeTrainingRepository.get_by_employee_and_workstation",
            extra={
                "event_type": "employee_training_lookup",
                "lookup_type": "employee_and_workstation",
                "employee_id": employee_id,
                "workstation_id": workstation_id
            }
        )

        try:
            with self.session_scope() as session:
                model = session.query(EmployeeTrainingModel).filter(
                    and_(
                        EmployeeTrainingModel.employee_id == employee_id,
                        EmployeeTrainingModel.station_id == workstation_id
                    )
                ).first()

            if not model:
                self.logger.info(
                    "No training record found for employee and workstation",
                    extra={
                        "event_type": "employee_training_lookup_result",
                        "lookup_type": "employee_and_workstation",
                        "employee_id": employee_id,
                        "workstation_id": workstation_id,
                        "result": "not_found"
                    }
                )
                return None

            self.logger.debug(
                f"Converting EmployeeTrainingModel [id={model.id}] to domain EmployeeTraining",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "employee_id": employee_id,
                    "workstation_id": workstation_id
                }
            )

            return EmployeeTrainingFactory.create_from_model(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeTrainingRepository.get_by_employee_and_workstation: {error_msg}",
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

        Raises:
            RepositoryError: If there was an error retrieving the training records
        """
        self.logger.info(
            "Entering EmployeeTrainingRepository.get_by_employee",
            extra={
                "event_type": "employee_training_lookup",
                "lookup_type": "employee",
                "employee_id": employee_id
            }
        )

        try:
            with self.session_scope() as session:
                models = session.query(EmployeeTrainingModel).filter(
                    EmployeeTrainingModel.employee_id == employee_id
                ).all()

            record_count = len(models)
            self.logger.info(
                f"Found {record_count} training records for employee",
                extra={
                    "event_type": "employee_training_lookup_result",
                    "lookup_type": "employee",
                    "employee_id": employee_id,
                    "record_count": record_count
                }
            )

            result = []
            for model in models:
                self.logger.debug(
                    f"Converting EmployeeTrainingModel [id={model.id}] to domain EmployeeTraining",
                    extra={
                        "event_type": "model_to_domain_conversion",
                        "entity_id": model.id,
                        "employee_id": employee_id,
                        "workstation_id": model.station_id
                    }
                )
                result.append(EmployeeTrainingFactory.create_from_model(model))

            return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeTrainingRepository.get_by_employee: {error_msg}",
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

        Raises:
            RepositoryError: If there was an error retrieving the training records
        """
        self.logger.info(
            "Entering EmployeeTrainingRepository.get_by_workstation",
            extra={
                "event_type": "employee_training_lookup",
                "lookup_type": "workstation",
                "workstation_id": workstation_id
            }
        )

        try:
            with self.session_scope() as session:
                models = session.query(EmployeeTrainingModel).filter(
                    EmployeeTrainingModel.station_id == workstation_id
                ).all()

            record_count = len(models)
            self.logger.info(
                f"Found {record_count} training records for workstation",
                extra={
                    "event_type": "employee_training_lookup_result",
                    "lookup_type": "workstation",
                    "workstation_id": workstation_id,
                    "record_count": record_count
                }
            )

            result = []
            for model in models:
                self.logger.debug(
                    f"Converting EmployeeTrainingModel [id={model.id}] to domain EmployeeTraining",
                    extra={
                        "event_type": "model_to_domain_conversion",
                        "entity_id": model.id,
                        "employee_id": model.employee_id,
                        "workstation_id": workstation_id
                    }
                )
                result.append(EmployeeTrainingFactory.create_from_model(model))

            return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeTrainingRepository.get_by_workstation: {error_msg}",
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

        Raises:
            RepositoryError: If there was an error retrieving the training records
        """
        self.logger.info(
            "Entering EmployeeTrainingRepository.get_completed_trainings",
            extra={
                "event_type": "employee_training_lookup",
                "lookup_type": "completed_trainings",
                "employee_id": employee_id
            }
        )

        try:
            with self.session_scope() as session:
                models = session.query(EmployeeTrainingModel).filter(
                    and_(
                        EmployeeTrainingModel.employee_id == employee_id,
                        EmployeeTrainingModel.date_completed.isnot(None)
                    )
                ).all()

            record_count = len(models)
            self.logger.info(
                f"Found {record_count} completed training records for employee",
                extra={
                    "event_type": "employee_training_lookup_result",
                    "lookup_type": "completed_trainings",
                    "employee_id": employee_id,
                    "record_count": record_count
                }
            )

            result = []
            for model in models:
                self.logger.debug(
                    f"Converting EmployeeTrainingModel [id={model.id}] to domain EmployeeTraining",
                    extra={
                        "event_type": "model_to_domain_conversion",
                        "entity_id": model.id,
                        "employee_id": employee_id,
                        "workstation_id": model.station_id
                    }
                )
                result.append(EmployeeTrainingFactory.create_from_model(model))

            return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeTrainingRepository.get_completed_trainings: {error_msg}",
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

        Raises:
            RepositoryError: If there was an error retrieving the training records
        """
        self.logger.info(
            "Entering EmployeeTrainingRepository.get_required_trainings",
            extra={
                "event_type": "employee_training_lookup",
                "lookup_type": "required_trainings",
                "employee_id": employee_id
            }
        )

        try:
            with self.session_scope() as session:
                models = session.query(EmployeeTrainingModel).filter(
                    and_(
                        EmployeeTrainingModel.employee_id == employee_id,
                        EmployeeTrainingModel.required_training == True
                    )
                ).all()

            record_count = len(models)
            self.logger.info(
                f"Found {record_count} required training records for employee",
                extra={
                    "event_type": "employee_training_lookup_result",
                    "lookup_type": "required_trainings",
                    "employee_id": employee_id,
                    "record_count": record_count
                }
            )

            result = []
            for model in models:
                self.logger.debug(
                    f"Converting EmployeeTrainingModel [id={model.id}] to domain EmployeeTraining",
                    extra={
                        "event_type": "model_to_domain_conversion",
                        "entity_id": model.id,
                        "employee_id": employee_id,
                        "workstation_id": model.station_id
                    }
                )
                result.append(EmployeeTrainingFactory.create_from_model(model))

            return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeTrainingRepository.get_required_trainings: {error_msg}",
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

        Raises:
            RepositoryError: If there was an error updating the training record
        """
        self.logger.info(
            "Entering EmployeeTrainingRepository.update_training_status",
            extra={
                "event_type": "employee_training_update",
                "employee_id": employee_id,
                "workstation_id": workstation_id
            }
        )

        try:
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
                            "event_type": "employee_training_update_result",
                            "employee_id": employee_id,
                            "workstation_id": workstation_id,
                            "result": "not_found"
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

                self.logger.debug(
                    f"Converting updated EmployeeTrainingModel [id={model.id}] to domain EmployeeTraining",
                    extra={
                        "event_type": "model_to_domain_conversion",
                        "entity_id": model.id,
                        "employee_id": employee_id,
                        "workstation_id": workstation_id
                    }
                )

                return EmployeeTrainingFactory.create_from_model(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeTrainingRepository.update_training_status: {error_msg}",
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

        Raises:
            RepositoryError: If there was an error deleting the training record
        """
        self.logger.info(
            "Entering EmployeeTrainingRepository.delete",
            extra={
                "event_type": "employee_training_delete",
                "employee_id": employee_id,
                "workstation_id": workstation_id
            }
        )

        try:
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
                            "event_type": "employee_training_delete_result",
                            "employee_id": employee_id,
                            "workstation_id": workstation_id,
                            "result": "not_found"
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
                f"Error in EmployeeTrainingRepository.delete: {error_msg}",
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
        for EmployeeTraining since it's identified by a composite key (employee_id, workstation_id).
        Use get_by_employee_and_workstation instead.

        Args:
            id: The ID of the entity to retrieve

        Returns:
            The training record if found, None otherwise
        """
        self.logger.info(
            "Entering EmployeeTrainingRepository.get",
            extra={
                "event_type": "employee_training_lookup",
                "lookup_type": "id",
                "entity_id": id
            }
        )

        try:
            # Try to find by internal ID
            with self.session_scope() as session:
                model = session.query(EmployeeTrainingModel).filter(
                    EmployeeTrainingModel.id == id
                ).first()

            if not model:
                self.logger.info(
                    "No training record found with the given ID",
                    extra={
                        "event_type": "employee_training_lookup_result",
                        "lookup_type": "id",
                        "entity_id": id,
                        "result": "not_found"
                    }
                )
                return None

            self.logger.debug(
                f"Converting EmployeeTrainingModel [id={model.id}] to domain EmployeeTraining",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "employee_id": model.employee_id,
                    "workstation_id": model.station_id
                }
            )

            return EmployeeTrainingFactory.create_from_model(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeTrainingRepository.get: {error_msg}",
                extra={
                    "event_type": "employee_training_lookup_error",
                    "lookup_type": "id",
                    "entity_id": id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get training record by ID: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in EmployeeTrainingRepository.get: {error_msg}",
                extra={
                    "event_type": "employee_training_lookup_error",
                    "lookup_type": "id",
                    "entity_id": id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Unexpected error retrieving training record: {error_msg}")

    def get_all_entities(self) -> List[EmployeeTraining]:
        """
        Get all training records.

        Returns:
            A list of all training records

        Raises:
            RepositoryError: If there was an error retrieving the training records
        """
        self.logger.info(
            "Entering EmployeeTrainingRepository.get_all_entities",
            extra={
                "event_type": "employee_training_list_all"
            }
        )

        try:
            with self.session_scope() as session:
                models = session.query(EmployeeTrainingModel).all()

            record_count = len(models)
            self.logger.info(
                f"Retrieved {record_count} employee training records",
                extra={
                    "event_type": "employee_training_list_all_result",
                    "record_count": record_count
                }
            )

            result = []
            for model in models:
                self.logger.debug(
                    f"Converting EmployeeTrainingModel [id={model.id}] to domain EmployeeTraining",
                    extra={
                        "event_type": "model_to_domain_conversion",
                        "entity_id": model.id,
                        "employee_id": model.employee_id,
                        "workstation_id": model.station_id
                    }
                )
                result.append(EmployeeTrainingFactory.create_from_model(model))

            return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeTrainingRepository.get_all_entities: {error_msg}",
                extra={
                    "event_type": "employee_training_list_all_error",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get all training records: {error_msg}")

    # The _to_domain, _to_model, and _update_model methods have been replaced by the EmployeeTrainingFactory
    # which provides better separation of concerns and follows DDD principles
