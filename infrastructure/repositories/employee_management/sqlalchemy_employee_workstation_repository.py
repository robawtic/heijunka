# heijunka/domain/repositories/buses/sqlalchemy_employee_workstation_repository.py
from typing import List, Optional
from datetime import date
from sqlalchemy import and_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from domain.contexts.assignment.value_objects.workstation_assignment import WorkstationAssignment
from domain.models.EmployeeWorkstationModel import EmployeeWorkstationModel
from domain.models.WorkstationModel import WorkstationModel
from domain.repositories.interfaces.employee_workstation_repository import EmployeeWorkstationRepositoryInterface
from domain.factories.workstation_assignment_factory import WorkstationAssignmentFactory
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger


class SqlAlchemyEmployeeWorkstationRepository(BaseSqlAlchemyRepository[WorkstationAssignment, EmployeeWorkstationModel], EmployeeWorkstationRepositoryInterface):
    """
    SQLAlchemy implementation of the EmployeeWorkstationRepository interface.

    This class provides the actual implementation for accessing and manipulating
    employee workstation assignments in the database using SQLAlchemy.
    """

    def __init__(self, session_factory):
        """
        Initialize the repository with a SQLAlchemy session factory.

        Args:
            session_factory: The SQLAlchemy session factory to use for database operations.
        """
        super().__init__(session_factory, EmployeeWorkstationModel, WorkstationAssignment)
        self.logger = get_logger("heijunka.repositories.employee_workstation")
        self.rate_limited_logger = get_logger("heijunka.repositories.employee_workstation", rate_limit=True)

    def add(self, assignment: WorkstationAssignment) -> WorkstationAssignment:
        """
        Add a new workstation assignment.

        Args:
            assignment: The workstation assignment to add

        Returns:
            The added workstation assignment

        Raises:
            RepositoryError: If there was an error adding the workstation assignment
        """
        self.logger.info(
            "Entering EmployeeWorkstationRepository.add",
            extra={
                "event_type": "workstation_assignment_add",
                "employee_id": assignment.employee_id,
                "workstation_id": assignment.workstation_id
            }
        )

        try:
            with self.session_scope() as session:
                model = WorkstationAssignmentFactory.create_from_entity(assignment)
                session.add(model)
                session.flush()  # Flush to get the ID

                self.logger.info(
                    "Successfully added workstation assignment",
                    extra={
                        "event_type": "workstation_assignment_add_success",
                        "entity_id": model.id,
                        "employee_id": assignment.employee_id,
                        "workstation_id": assignment.workstation_id,
                        "workstation_name": assignment.workstation_name
                    }
                )

                return WorkstationAssignmentFactory.create_from_model_with_session(model, session)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeWorkstationRepository.add: {error_msg}",
                extra={
                    "event_type": "workstation_assignment_add_error",
                    "employee_id": assignment.employee_id,
                    "workstation_id": assignment.workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to add workstation assignment: {error_msg}")

    def get_by_employee_and_workstation(self, employee_id: int, workstation_id: int) -> Optional[WorkstationAssignment]:
        """
        Get a workstation assignment for a specific employee and workstation.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation

        Returns:
            The workstation assignment if found, None otherwise

        Raises:
            RepositoryError: If there was an error retrieving the workstation assignment
        """
        self.logger.info(
            "Entering EmployeeWorkstationRepository.get_by_employee_and_workstation",
            extra={
                "event_type": "workstation_assignment_lookup",
                "lookup_type": "employee_and_workstation",
                "employee_id": employee_id,
                "workstation_id": workstation_id
            }
        )

        try:
            with self.session_scope() as session:
                model = session.query(EmployeeWorkstationModel).filter(
                    and_(
                        EmployeeWorkstationModel.employee_id == employee_id,
                        EmployeeWorkstationModel.station_id == workstation_id
                    )
                ).first()

                if not model:
                    self.logger.info(
                        "No workstation assignment found for employee and workstation",
                        extra={
                            "event_type": "workstation_assignment_lookup_failed",
                            "lookup_type": "employee_and_workstation",
                            "employee_id": employee_id,
                            "workstation_id": workstation_id,
                            "reason": "not_found"
                        }
                    )
                    return None

                self.logger.debug(
                    f"Converting EmployeeWorkstationModel [id={model.id}] to domain WorkstationAssignment",
                    extra={
                        "event_type": "model_to_domain_conversion",
                        "entity_id": model.id,
                        "employee_id": employee_id,
                        "workstation_id": workstation_id
                    }
                )

                result = WorkstationAssignmentFactory.create_from_model_with_session(model, session)

                self.logger.info(
                    "Found workstation assignment for employee and workstation",
                    extra={
                        "event_type": "workstation_assignment_lookup_success",
                        "lookup_type": "employee_and_workstation",
                        "employee_id": employee_id,
                        "workstation_id": workstation_id,
                        "workstation_name": result.workstation_name
                    }
                )

            return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeWorkstationRepository.get_by_employee_and_workstation: {error_msg}",
                extra={
                    "event_type": "workstation_assignment_lookup_error",
                    "lookup_type": "employee_and_workstation",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get workstation assignment: {error_msg}")

    def get_by_employee(self, employee_id: int) -> List[WorkstationAssignment]:
        """
        Get all workstation assignments for a specific employee.

        Args:
            employee_id: The ID of the employee

        Returns:
            A list of workstation assignments

        Raises:
            RepositoryError: If there was an error retrieving the workstation assignments
        """
        self.logger.info(
            "Entering EmployeeWorkstationRepository.get_by_employee",
            extra={
                "event_type": "workstation_assignments_lookup",
                "lookup_type": "employee",
                "employee_id": employee_id
            }
        )

        try:
            result = []
            with self.session_scope() as session:
                models = session.query(EmployeeWorkstationModel).filter(
                    EmployeeWorkstationModel.employee_id == employee_id
                ).all()

                for model in models:
                    self.rate_limited_logger.debug(
                        f"Converting EmployeeWorkstationModel [id={model.id}] to domain WorkstationAssignment",
                        extra={
                            "event_type": "model_to_domain_conversion",
                            "entity_id": model.id,
                            "employee_id": employee_id,
                            "workstation_id": model.station_id
                        }
                    )
                    result.append(WorkstationAssignmentFactory.create_from_model_with_session(model, session))

            assignment_count = len(result)
            self.logger.info(
                f"Found {assignment_count} workstation assignments for employee ID: {employee_id}",
                extra={
                    "event_type": "workstation_assignments_lookup_success",
                    "lookup_type": "employee",
                    "employee_id": employee_id,
                    "assignment_count": assignment_count
                }
            )

            return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeWorkstationRepository.get_by_employee: {error_msg}",
                extra={
                    "event_type": "workstation_assignments_lookup_error",
                    "lookup_type": "employee",
                    "employee_id": employee_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get workstation assignments by employee: {error_msg}")

    def get_by_workstation(self, workstation_id: int) -> List[WorkstationAssignment]:
        """
        Get all workstation assignments for a specific workstation.

        Args:
            workstation_id: The ID of the workstation

        Returns:
            A list of workstation assignments

        Raises:
            RepositoryError: If there was an error retrieving the workstation assignments
        """
        self.logger.info(
            "Entering EmployeeWorkstationRepository.get_by_workstation",
            extra={
                "event_type": "workstation_assignments_lookup",
                "lookup_type": "workstation",
                "workstation_id": workstation_id
            }
        )

        try:
            result = []
            with self.session_scope() as session:
                models = session.query(EmployeeWorkstationModel).filter(
                    EmployeeWorkstationModel.station_id == workstation_id
                ).all()

                # Fetch the workstation name once for logging
                workstation = session.query(WorkstationModel).get(workstation_id)
                workstation_name = workstation.name if workstation else "Unknown"

                for model in models:
                    self.rate_limited_logger.debug(
                        f"Converting EmployeeWorkstationModel [id={model.id}] to domain WorkstationAssignment",
                        extra={
                            "event_type": "model_to_domain_conversion",
                            "entity_id": model.id,
                            "employee_id": model.employee_id,
                            "workstation_id": workstation_id
                        }
                    )
                    # We can use the workstation name we already fetched
                    result.append(WorkstationAssignmentFactory.create_from_model(model, workstation_name))

            assignment_count = len(result)
            self.logger.info(
                f"Found {assignment_count} workstation assignments for workstation ID: {workstation_id}",
                extra={
                    "event_type": "workstation_assignments_lookup_success",
                    "lookup_type": "workstation",
                    "workstation_id": workstation_id,
                    "workstation_name": workstation_name,
                    "assignment_count": assignment_count
                }
            )

            return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeWorkstationRepository.get_by_workstation: {error_msg}",
                extra={
                    "event_type": "workstation_assignments_lookup_error",
                    "lookup_type": "workstation",
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get workstation assignments by workstation: {error_msg}")

    def update_last_worked_date(self, employee_id: int, workstation_id: int, 
                               last_worked_date: Optional[date]) -> Optional[WorkstationAssignment]:
        """
        Update the last worked date of a workstation assignment.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            last_worked_date: The date the employee last worked at the workstation, or None

        Returns:
            The updated workstation assignment if found, None otherwise

        Raises:
            RepositoryError: If there was an error updating the workstation assignment
        """
        self.logger.info(
            "Entering EmployeeWorkstationRepository.update_last_worked_date",
            extra={
                "event_type": "workstation_assignment_update",
                "update_type": "last_worked_date",
                "employee_id": employee_id,
                "workstation_id": workstation_id,
                "last_worked_date": last_worked_date.isoformat() if last_worked_date else None
            }
        )

        try:
            with self.session_scope() as session:
                model = session.query(EmployeeWorkstationModel).filter(
                    and_(
                        EmployeeWorkstationModel.employee_id == employee_id,
                        EmployeeWorkstationModel.station_id == workstation_id
                    )
                ).first()

                if not model:
                    self.logger.info(
                        "No workstation assignment found to update",
                        extra={
                            "event_type": "workstation_assignment_update_failed",
                            "update_type": "last_worked_date",
                            "employee_id": employee_id,
                            "workstation_id": workstation_id,
                            "reason": "not_found"
                        }
                    )
                    return None

                # Log the change
                old_date = model.last_worked_date
                self.logger.info(
                    "Changing last worked date",
                    extra={
                        "event_type": "workstation_assignment_field_change",
                        "field": "last_worked_date",
                        "entity_id": model.id,
                        "employee_id": employee_id,
                        "workstation_id": workstation_id,
                        "old_value": old_date.isoformat() if old_date else None,
                        "new_value": last_worked_date.isoformat() if last_worked_date else None
                    }
                )

                model.last_worked_date = last_worked_date
                session.flush()

                self.logger.debug(
                    f"Converting updated EmployeeWorkstationModel [id={model.id}] to domain WorkstationAssignment",
                    extra={
                        "event_type": "model_to_domain_conversion",
                        "entity_id": model.id,
                        "employee_id": employee_id,
                        "workstation_id": workstation_id
                    }
                )

                result = WorkstationAssignmentFactory.create_from_model_with_session(model, session)

                self.logger.info(
                    "Successfully updated last worked date",
                    extra={
                        "event_type": "workstation_assignment_update_success",
                        "update_type": "last_worked_date",
                        "entity_id": model.id,
                        "employee_id": employee_id,
                        "workstation_id": workstation_id,
                        "workstation_name": result.workstation_name
                    }
                )

                return result
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeWorkstationRepository.update_last_worked_date: {error_msg}",
                extra={
                    "event_type": "workstation_assignment_update_error",
                    "update_type": "last_worked_date",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to update last worked date: {error_msg}")

    def delete(self, employee_id: int, workstation_id: int) -> bool:
        """
        Delete a workstation assignment.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If there was an error deleting the workstation assignment
        """
        self.logger.info(
            "Entering EmployeeWorkstationRepository.delete",
            extra={
                "event_type": "workstation_assignment_delete",
                "employee_id": employee_id,
                "workstation_id": workstation_id
            }
        )

        try:
            with self.session_scope() as session:
                model = session.query(EmployeeWorkstationModel).filter(
                    and_(
                        EmployeeWorkstationModel.employee_id == employee_id,
                        EmployeeWorkstationModel.station_id == workstation_id
                    )
                ).first()

                if not model:
                    self.logger.info(
                        "No workstation assignment found to delete",
                        extra={
                            "event_type": "workstation_assignment_delete_failed",
                            "employee_id": employee_id,
                            "workstation_id": workstation_id,
                            "reason": "not_found"
                        }
                    )
                    return False

                # Fetch the workstation name for logging
                workstation = session.query(WorkstationModel).get(workstation_id)
                workstation_name = workstation.name if workstation else "Unknown"

                # Log the entity being deleted
                self.logger.debug(
                    f"Deleting EmployeeWorkstationModel [id={model.id}]",
                    extra={
                        "event_type": "entity_delete",
                        "entity_id": model.id,
                        "employee_id": employee_id,
                        "workstation_id": workstation_id
                    }
                )

                session.delete(model)

                self.logger.info(
                    "Successfully deleted workstation assignment",
                    extra={
                        "event_type": "workstation_assignment_delete_success",
                        "entity_id": model.id,
                        "employee_id": employee_id,
                        "workstation_id": workstation_id,
                        "workstation_name": workstation_name
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeWorkstationRepository.delete: {error_msg}",
                extra={
                    "event_type": "workstation_assignment_delete_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to delete workstation assignment: {error_msg}")

    def get(self, id: int) -> Optional[WorkstationAssignment]:
        """
        Get an entity by ID.

        This method is required by the BaseRepository interface but is not directly applicable
        for WorkstationAssignment since it's identified by a composite key.

        Args:
            id: The ID of the entity to retrieve

        Returns:
            None (not directly applicable for WorkstationAssignment)

        Raises:
            RepositoryError: If there was an error retrieving the workstation assignment
        """
        self.logger.info(
            "Entering EmployeeWorkstationRepository.get",
            extra={
                "event_type": "workstation_assignment_lookup",
                "lookup_type": "id",
                "entity_id": id
            }
        )

        self.logger.debug(
            f"Get by ID called with ID: {id}, but WorkstationAssignment uses composite key",
            extra={
                "event_type": "method_not_applicable",
                "method": "get",
                "entity_type": "WorkstationAssignment",
                "entity_id": id,
                "reason": "composite_key"
            }
        )
        return None

    def get_all_entities(self) -> List[WorkstationAssignment]:
        """
        Get all workstation assignments.

        Returns:
            A list of all workstation assignments

        Raises:
            RepositoryError: If there was an error retrieving the workstation assignments
        """
        self.logger.info(
            "Entering EmployeeWorkstationRepository.get_all_entities",
            extra={
                "event_type": "workstation_assignments_list_all"
            }
        )

        try:
            result = []
            with self.session_scope() as session:
                models = session.query(EmployeeWorkstationModel).all()

                for model in models:
                    self.rate_limited_logger.debug(
                        f"Converting EmployeeWorkstationModel [id={model.id}] to domain WorkstationAssignment",
                        extra={
                            "event_type": "model_to_domain_conversion",
                            "entity_id": model.id,
                            "employee_id": model.employee_id,
                            "workstation_id": model.station_id
                        }
                    )
                    result.append(WorkstationAssignmentFactory.create_from_model_with_session(model, session))

            assignment_count = len(result)
            self.logger.info(
                f"Retrieved {assignment_count} workstation assignments",
                extra={
                    "event_type": "workstation_assignments_list_all_success",
                    "assignment_count": assignment_count
                }
            )

            return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeWorkstationRepository.get_all_entities: {error_msg}",
                extra={
                    "event_type": "workstation_assignments_list_all_error",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get all workstation assignments: {error_msg}")

    def _to_domain(self, model: EmployeeWorkstationModel) -> WorkstationAssignment:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            self.logger.debug(
                f"Converting EmployeeWorkstationModel [id={model.id}] to domain WorkstationAssignment",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "employee_id": model.employee_id,
                    "workstation_id": model.station_id
                }
            )

            # Use the factory to create the domain entity
            with self.session_scope() as session:
                result = WorkstationAssignmentFactory.create_from_model_with_session(model, session)

            self.logger.debug(
                "Successfully converted workstation assignment model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion_success",
                    "entity_id": model.id
                }
            )

            return result
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting workstation assignment model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: WorkstationAssignment) -> EmployeeWorkstationModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            self.logger.debug(
                "Converting WorkstationAssignment domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "employee_id": entity.employee_id,
                    "workstation_id": entity.workstation_id
                }
            )

            # Use the factory to create the model
            model = WorkstationAssignmentFactory.create_from_entity(entity)

            self.logger.debug(
                "Successfully converted workstation assignment domain entity to model",
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
                f"Error converting workstation assignment domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "employee_id": entity.employee_id if entity and hasattr(entity, 'employee_id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: EmployeeWorkstationModel, entity: WorkstationAssignment) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            self.logger.debug(
                f"Updating EmployeeWorkstationModel [id={model.id}] from domain entity",
                extra={
                    "event_type": "workstation_assignment_model_update",
                    "entity_id": model.id,
                    "employee_id": model.employee_id,
                    "workstation_id": model.station_id
                }
            )

            # Use the factory to update the model
            WorkstationAssignmentFactory.update_model_from_entity(model, entity)

            self.logger.debug(
                "Successfully updated workstation assignment model",
                extra={
                    "event_type": "workstation_assignment_model_update_success",
                    "entity_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating workstation assignment model: {error_msg}",
                extra={
                    "event_type": "workstation_assignment_model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise
