# domain/repositories/buses/sqlalchemy_assignment_repository.py
from typing import List, Optional, Tuple
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from domain.contexts.assignment.value_objects.work_assignment import WorkAssignment
from domain.contexts.assignment.value_objects.work_assignment_validator import WorkAssignmentValidator
from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel, WorkHistoryStatus
from domain.repositories.interfaces.assignment_repository import AssignmentRepositoryInterface
from domain.factories.work_assignment_factory import WorkAssignmentFactory
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger


class SqlAlchemyAssignmentRepository(BaseSqlAlchemyRepository[WorkAssignment, EmployeeWorkHistoryModel],
                                     AssignmentRepositoryInterface):
    """
    SQLAlchemy implementation of the AssignmentRepository interface.

    This repository handles the persistence of WorkAssignment entities using SQLAlchemy ORM.
    It uses the WorkAssignmentFactory to convert between domain entities and database models,
    ensuring proper separation of concerns and DDD purity.
    """

    def __init__(self, session_factory):
        """
        Initialize the repository with a SQLAlchemy session factory.

        Args:
            session_factory: The SQLAlchemy session factory to use for database operations.
        """
        super().__init__(session_factory, EmployeeWorkHistoryModel, WorkAssignment)
        self.logger = get_logger("heijunka.repositories.assignment")
        self.rate_limited_logger = get_logger("heijunka.repositories.assignment", rate_limit=True)

    # -------------------------------------------------------------------------
    # Core CRUD Operations
    # -------------------------------------------------------------------------

    def get_all(self, page: int = 1, page_size: int = 50) -> Tuple[List[WorkAssignment], int]:
        """
        Retrieve work assignments with pagination.

        Args:
            page: The page number to retrieve (default: 1).
            page_size: The number of assignments per page (default: 50).

        Returns:
            A tuple of (assignments list, total count).
        """
        self.logger.info(
            "Entering AssignmentRepository.get_all",
            extra={"event_type": "assignments_list_all"}
        )
        try:
            from sqlalchemy.orm import joinedload
            offset = (page - 1) * page_size
            with self.session_scope() as session:
                total_count = session.query(EmployeeWorkHistoryModel).count()
                models = session.query(EmployeeWorkHistoryModel).options(
                    joinedload(EmployeeWorkHistoryModel.employee),
                    joinedload(EmployeeWorkHistoryModel.station)
                ).offset(offset).limit(page_size).all()
            self.logger.info(
                f"Retrieved {len(models)} work assignments (page {page} of {(total_count + page_size - 1) // page_size}, total: {total_count})",
                extra={
                    "event_type": "assignments_list_all_success",
                    "count": len(models),
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size
                }
            )
            assignments = self._convert_models_to_domain(models)
            return assignments, total_count
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving all work assignments: {error_msg}",
                extra={
                    "event_type": "assignments_list_all_error",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving all work assignments: {error_msg}")

    def get_by_id(self, assignment_id: int) -> Optional[WorkAssignment]:
        """
        Retrieve a work assignment by its ID.

        Args:
            assignment_id: The ID of the work assignment to retrieve.

        Returns:
            The work assignment if found, None otherwise.
        """
        self.logger.info(
            f"Entering AssignmentRepository.get_by_id (id={assignment_id})",
            extra={
                "event_type": "assignment_lookup",
                "lookup_type": "id",
                "assignment_id": assignment_id
            }
        )
        try:
            with self.session_scope() as session:
                model = session.get(EmployeeWorkHistoryModel, assignment_id)
                if not model:
                    self.logger.info(
                        f"No work assignment found with ID: {assignment_id}",
                        extra={
                            "event_type": "assignment_lookup_failed",
                            "lookup_type": "id",
                            "assignment_id": assignment_id,
                            "reason": "not_found"
                        }
                    )
                    return None
                self.logger.info(
                    f"Found work assignment with ID: {assignment_id}",
                    extra={
                        "event_type": "assignment_lookup_success",
                        "lookup_type": "id",
                        "assignment_id": assignment_id
                    }
                )
                self.rate_limited_logger.debug(
                    f"Converting EmployeeWorkHistoryModel [id={model.id}] to domain WorkAssignment",
                    "model_to_domain_conversion",
                    str(model.id),
                    extra={
                        "entity_id": model.id
                    }
                )
                return self._to_domain(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving work assignment by ID: {error_msg}",
                extra={
                    "event_type": "assignment_lookup_error",
                    "lookup_type": "id",
                    "assignment_id": assignment_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving work assignment by ID: {error_msg}")

    def add(self, assignment: WorkAssignment) -> WorkAssignment:
        """
        Add a new work assignment.

        Args:
            assignment: The work assignment to add.

        Returns:
            The added work assignment with updated metadata.
        """
        self.logger.info(
            "Entering AssignmentRepository.add",
            extra={
                "event_type": "assignment_add",
                "employee_id": assignment.employee.id,
                "workstation_id": assignment.workstation.id,
                "date": assignment.period.date.isoformat() if hasattr(assignment.period.date, 'isoformat') else str(
                    assignment.period.date),
                "period": assignment.period.period
            }
        )

        try:
            with self.session_scope() as session:
                self.rate_limited_logger.debug(
                    "Converting WorkAssignment to EmployeeWorkHistoryModel",
                    "domain_to_model_conversion",
                    str(assignment.employee.id),
                    extra={
                        "employee_id": assignment.employee.id,
                        "workstation_id": assignment.workstation.id
                    }
                )
                model = self._to_model(assignment)
                session.add(model)
                session.flush()  # Flush to get the ID

                self.logger.info(
                    f"Successfully added work assignment with ID: {model.id}",
                    extra={
                        "event_type": "assignment_add_success",
                        "assignment_id": model.id,
                        "employee_id": assignment.employee.id,
                        "workstation_id": assignment.workstation.id
                    }
                )

                # Convert back to domain entity with updated metadata
                self.rate_limited_logger.debug(
                    f"Converting EmployeeWorkHistoryModel [id={model.id}] to domain WorkAssignment",
                    "model_to_domain_conversion",
                    str(model.id),
                    extra={
                        "entity_id": model.id
                    }
                )
                return self._to_domain(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error adding work assignment: {error_msg}",
                extra={
                    "event_type": "assignment_add_error",
                    "employee_id": assignment.employee.id,
                    "workstation_id": assignment.workstation.id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error adding work assignment: {error_msg}")

    def update(self, assignment: WorkAssignment) -> WorkAssignment:
        """
        Update an existing work assignment.

        Args:
            assignment: The work assignment to update.

        Returns:
            The updated work assignment.

        Raises:
            RepositoryError: If the assignment doesn't have an ID or doesn't exist.
        """
        # Get the ID and version from metadata
        metadata = getattr(assignment, '_metadata', {})
        assignment_id = metadata.get('id')
        version = metadata.get('version')

        if not assignment_id:
            error_msg = "Cannot update assignment without ID"
            self.logger.error(
                error_msg,
                extra={
                    "event_type": "assignment_update_error",
                    "reason": "missing_id"
                }
            )
            raise RepositoryError(error_msg)

        self.logger.info(
            f"Entering AssignmentRepository.update (id={assignment_id})",
            extra={
                "event_type": "assignment_update",
                "assignment_id": assignment_id,
                "employee_id": assignment.employee.id,
                "workstation_id": assignment.workstation.id
            }
        )

        try:
            with self.session_scope() as session:
                # No version provided, just get the entity by ID
                model = session.get(EmployeeWorkHistoryModel, assignment_id)

                if not model:
                    error_msg = f"Work assignment with ID {assignment_id} not found"
                    self.logger.warning(
                        error_msg,
                        extra={
                            "event_type": "assignment_update_failed",
                            "assignment_id": assignment_id,
                            "reason": "not_found"
                        }
                    )
                    raise RepositoryError(error_msg)

                self.rate_limited_logger.debug(
                    f"Updating EmployeeWorkHistoryModel [id={model.id}] from domain WorkAssignment",
                    "model_update",
                    str(model.id),
                    extra={
                        "entity_id": model.id
                    }
                )
                self._update_model(model, assignment)

                self.logger.info(
                    f"Successfully updated work assignment with ID: {assignment_id}",
                    extra={
                        "event_type": "assignment_update_success",
                        "assignment_id": assignment_id
                    }
                )

                self.rate_limited_logger.debug(
                    f"Converting EmployeeWorkHistoryModel [id={model.id}] to domain WorkAssignment",
                    "model_to_domain_conversion",
                    str(model.id),
                    extra={
                        "entity_id": model.id
                    }
                )
                return self._to_domain(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating work assignment: {error_msg}",
                extra={
                    "event_type": "assignment_update_error",
                    "assignment_id": assignment_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error updating work assignment: {error_msg}")

    def delete(self, assignment_id: int) -> bool:
        """
        Delete a work assignment by its ID.

        Args:
            assignment_id: The ID of the work assignment to delete.

        Returns:
            True if the assignment was deleted, False if it wasn't found.
        """
        self.logger.info(
            f"Entering AssignmentRepository.delete (id={assignment_id})",
            extra={
                "event_type": "assignment_delete",
                "assignment_id": assignment_id
            }
        )

        try:
            with self.session_scope() as session:
                model = session.get(EmployeeWorkHistoryModel, assignment_id)

                if not model:
                    self.logger.info(
                        f"No work assignment found with ID: {assignment_id} to delete",
                        extra={
                            "event_type": "assignment_delete_failed",
                            "assignment_id": assignment_id,
                            "reason": "not_found"
                        }
                    )
                    return False

                session.delete(model)

                self.logger.info(
                    f"Successfully deleted work assignment with ID: {assignment_id}",
                    extra={
                        "event_type": "assignment_delete_success",
                        "assignment_id": assignment_id
                    }
                )

                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error deleting work assignment: {error_msg}",
                extra={
                    "event_type": "assignment_delete_error",
                    "assignment_id": assignment_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error deleting work assignment: {error_msg}")

    # -------------------------------------------------------------------------
    # Specialized Lookups
    # -------------------------------------------------------------------------

    def get_by_employee_id(self, employee_id: int) -> List[WorkAssignment]:
        """
        Retrieve all assignments for a specific employee.

        Args:
            employee_id: The ID of the employee.

        Returns:
            A list of work assignments for the employee.
        """
        self.logger.info(
            f"Entering AssignmentRepository.get_by_employee_id (employee_id={employee_id})",
            extra={
                "event_type": "assignments_lookup",
                "lookup_type": "employee_id",
                "employee_id": employee_id
            }
        )

        try:
            from sqlalchemy.orm import joinedload

            with self.session_scope() as session:
                # Use eager loading to prevent N+1 query problems
                models = session.query(EmployeeWorkHistoryModel).options(
                    joinedload(EmployeeWorkHistoryModel.station)
                ).filter(
                    EmployeeWorkHistoryModel.employee_id == employee_id
                ).all()

            self.logger.info(
                f"Found {len(models)} assignments for employee ID: {employee_id}",
                extra={
                    "event_type": "assignments_lookup_success",
                    "lookup_type": "employee_id",
                    "employee_id": employee_id,
                    "count": len(models)
                }
            )

            # Use the helper method to convert models to domain entities
            return self._convert_models_to_domain(models)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving assignments for employee: {error_msg}",
                extra={
                    "event_type": "assignments_lookup_error",
                    "lookup_type": "employee_id",
                    "employee_id": employee_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving assignments for employee: {error_msg}")

    def get_by_workstation_id(self, workstation_id: int) -> List[WorkAssignment]:
        """
        Retrieve all assignments for a specific workstation.

        Args:
            workstation_id: The ID of the workstation.

        Returns:
            A list of work assignments for the workstation.
        """
        self.logger.info(
            f"Entering AssignmentRepository.get_by_workstation_id (workstation_id={workstation_id})",
            extra={
                "event_type": "assignments_lookup",
                "lookup_type": "workstation_id",
                "workstation_id": workstation_id
            }
        )

        try:
            from sqlalchemy.orm import joinedload

            with self.session_scope() as session:
                # Use eager loading to prevent N+1 query problems
                models = session.query(EmployeeWorkHistoryModel).options(
                    joinedload(EmployeeWorkHistoryModel.employee)
                ).filter(
                    EmployeeWorkHistoryModel.station_id == workstation_id
                ).all()

            self.logger.info(
                f"Found {len(models)} assignments for workstation ID: {workstation_id}",
                extra={
                    "event_type": "assignments_lookup_success",
                    "lookup_type": "workstation_id",
                    "workstation_id": workstation_id,
                    "count": len(models)
                }
            )

            # Use the helper method to convert models to domain entities
            return self._convert_models_to_domain(models)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving assignments for workstation: {error_msg}",
                extra={
                    "event_type": "assignments_lookup_error",
                    "lookup_type": "workstation_id",
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving assignments for workstation: {error_msg}")

    def get_by_schedule_id(self, schedule_id: int) -> List[WorkAssignment]:
        """
        Retrieve all assignments for a specific schedule.

        Args:
            schedule_id: The ID of the schedule.

        Returns:
            A list of work assignments for the schedule.
        """
        self.logger.info(
            f"Entering AssignmentRepository.get_by_schedule_id (schedule_id={schedule_id})",
            extra={
                "event_type": "assignments_lookup",
                "lookup_type": "schedule_id",
                "schedule_id": schedule_id
            }
        )

        try:
            from sqlalchemy.orm import joinedload

            with self.session_scope() as session:
                # Use eager loading to prevent N+1 query problems
                models = session.query(EmployeeWorkHistoryModel).options(
                    joinedload(EmployeeWorkHistoryModel.employee),
                    joinedload(EmployeeWorkHistoryModel.station)
                ).filter(
                    EmployeeWorkHistoryModel.schedule_id == schedule_id
                ).all()

            self.logger.info(
                f"Found {len(models)} assignments for schedule ID: {schedule_id}",
                extra={
                    "event_type": "assignments_lookup_success",
                    "lookup_type": "schedule_id",
                    "schedule_id": schedule_id,
                    "count": len(models)
                }
            )

            # Use the helper method to convert models to domain entities
            return self._convert_models_to_domain(models)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving assignments for schedule: {error_msg}",
                extra={
                    "event_type": "assignments_lookup_error",
                    "lookup_type": "schedule_id",
                    "schedule_id": schedule_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving assignments for schedule: {error_msg}")

    def get_by_date(self, assignment_date: date) -> List[WorkAssignment]:
        """
        Retrieve all assignments for a specific date.

        Args:
            assignment_date: The date to retrieve assignments for.

        Returns:
            A list of work assignments for the date.
        """
        self.logger.info(
            f"Entering AssignmentRepository.get_by_date (date={assignment_date})",
            extra={
                "event_type": "assignments_lookup",
                "lookup_type": "date",
                "date": self._format_date(assignment_date)
            }
        )

        try:
            from sqlalchemy.orm import joinedload

            with self.session_scope() as session:
                # Use eager loading to prevent N+1 query problems
                models = session.query(EmployeeWorkHistoryModel).options(
                    joinedload(EmployeeWorkHistoryModel.employee),
                    joinedload(EmployeeWorkHistoryModel.station)
                ).filter(
                    EmployeeWorkHistoryModel.worked_date == assignment_date
                ).all()

            self.logger.info(
                f"Found {len(models)} assignments for date: {assignment_date}",
                extra={
                    "event_type": "assignments_lookup_success",
                    "lookup_type": "date",
                    "date": self._format_date(assignment_date),
                    "count": len(models)
                }
            )

            # Use the helper method to convert models to domain entities
            return self._convert_models_to_domain(models)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving assignments for date: {error_msg}",
                extra={
                    "event_type": "assignments_lookup_error",
                    "lookup_type": "date",
                    "date": self._format_date(assignment_date),
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving assignments for date: {error_msg}")

    def get_by_date_and_period(self, assignment_date: date, period: int) -> List[WorkAssignment]:
        """
        Retrieve all assignments for a specific date and period.

        Args:
            assignment_date: The date to retrieve assignments for.
            period: The period of the day (1-5).

        Returns:
            A list of work assignments for the date and period.
        """
        self.logger.info(
            f"Entering AssignmentRepository.get_by_date_and_period (date={assignment_date}, period={period})",
            extra={
                "event_type": "assignments_lookup",
                "lookup_type": "date_and_period",
                "date": self._format_date(assignment_date),
                "period": period
            }
        )

        try:
            from sqlalchemy.orm import joinedload

            with self.session_scope() as session:
                # Use eager loading to prevent N+1 query problems
                models = session.query(EmployeeWorkHistoryModel).options(
                    joinedload(EmployeeWorkHistoryModel.employee),
                    joinedload(EmployeeWorkHistoryModel.station)
                ).filter(
                    EmployeeWorkHistoryModel.worked_date == assignment_date,
                    EmployeeWorkHistoryModel.work_period == period
                ).all()

            self.logger.info(
                f"Found {len(models)} assignments for date: {assignment_date}, period: {period}",
                extra={
                    "event_type": "assignments_lookup_success",
                    "lookup_type": "date_and_period",
                    "date": self._format_date(assignment_date),
                    "period": period,
                    "count": len(models)
                }
            )

            # Use the helper method to convert models to domain entities
            return self._convert_models_to_domain(models)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving assignments for date and period: {error_msg}",
                extra={
                    "event_type": "assignments_lookup_error",
                    "lookup_type": "date_and_period",
                    "date": self._format_date(assignment_date),
                    "period": period,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving assignments for date and period: {error_msg}")

    def get_by_employee_and_date(self, employee_id: int, assignment_date: date) -> List[WorkAssignment]:
        """
        Retrieve all assignments for a specific employee on a specific date.

        Args:
            employee_id: The ID of the employee.
            assignment_date: The date to retrieve assignments for.

        Returns:
            A list of work assignments for the employee on the date.
        """
        self.logger.info(
            f"Entering AssignmentRepository.get_by_employee_and_date (employee_id={employee_id}, date={assignment_date})",
            extra={
                "event_type": "assignments_lookup",
                "lookup_type": "employee_and_date",
                "employee_id": employee_id,
                "date": self._format_date(assignment_date)
            }
        )

        try:
            from sqlalchemy.orm import joinedload

            with self.session_scope() as session:
                # Use eager loading to prevent N+1 query problems
                models = session.query(EmployeeWorkHistoryModel).options(
                    joinedload(EmployeeWorkHistoryModel.station)
                ).filter(
                    EmployeeWorkHistoryModel.employee_id == employee_id,
                    EmployeeWorkHistoryModel.worked_date == assignment_date
                ).all()

            self.logger.info(
                f"Found {len(models)} assignments for employee ID: {employee_id}, date: {assignment_date}",
                extra={
                    "event_type": "assignments_lookup_success",
                    "lookup_type": "employee_and_date",
                    "employee_id": employee_id,
                    "date": self._format_date(assignment_date),
                    "count": len(models)
                }
            )

            # Use the helper method to convert models to domain entities
            return self._convert_models_to_domain(models)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving assignments for employee and date: {error_msg}",
                extra={
                    "event_type": "assignments_lookup_error",
                    "lookup_type": "employee_and_date",
                    "employee_id": employee_id,
                    "date": self._format_date(assignment_date),
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving assignments for employee and date: {error_msg}")

    def get_by_team_and_workstation(self, team_id: int, workstation_id: int) -> List[WorkAssignment]:
        """
        Retrieve all assignments for a specific team and workstation.

        Args:
            team_id: The ID of the team.
            workstation_id: The ID of the workstation.

        Returns:
            A list of work assignments for the team and workstation.
        """
        self.logger.info(
            f"Entering AssignmentRepository.get_by_team_and_workstation (team_id={team_id}, workstation_id={workstation_id})",
            extra={
                "event_type": "assignments_lookup",
                "lookup_type": "team_and_workstation",
                "team_id": team_id,
                "workstation_id": workstation_id
            }
        )

        try:
            from sqlalchemy.orm import joinedload

            with self.session_scope() as session:
                # This requires a join with the employees table to filter by team
                # Use eager loading to prevent N+1 query problems
                models = session.query(EmployeeWorkHistoryModel).options(
                    joinedload(EmployeeWorkHistoryModel.employee),
                    joinedload(EmployeeWorkHistoryModel.station)
                ).join(
                    EmployeeWorkHistoryModel.employee
                ).filter(
                    EmployeeWorkHistoryModel.station_id == workstation_id,
                    EmployeeWorkHistoryModel.employee.has(team_id=team_id)
                ).all()

            self.logger.info(
                f"Found {len(models)} assignments for team ID: {team_id}, workstation ID: {workstation_id}",
                extra={
                    "event_type": "assignments_lookup_success",
                    "lookup_type": "team_and_workstation",
                    "team_id": team_id,
                    "workstation_id": workstation_id,
                    "count": len(models)
                }
            )

            # Use the helper method to convert models to domain entities
            return self._convert_models_to_domain(models)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving assignments for team and workstation: {error_msg}",
                extra={
                    "event_type": "assignments_lookup_error",
                    "lookup_type": "team_and_workstation",
                    "team_id": team_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving assignments for team and workstation: {error_msg}")

    # -------------------------------------------------------------------------
    # Specialized Operations
    # -------------------------------------------------------------------------

    def save_all(self, assignments: List[WorkAssignment], batch_size: int = 100) -> bool:
        """
        Save a list of work assignments.

        This method first validates all assignments, then deletes any existing entries 
        for the dates in the assignments to avoid duplicate schedules. It processes 
        assignments in batches to avoid long-running transactions, using the session_scope
        context manager to ensure proper commit/rollback handling for all batches.

        Args:
            assignments: The list of work assignments to save.
            batch_size: The number of assignments to process in a single batch (default: 100).

        Returns:
            True if all assignments were saved successfully, False otherwise.
        """
        if not assignments:
            self.logger.info(
                "Entering AssignmentRepository.save_all (no assignments to save)",
                extra={
                    "event_type": "assignments_save_skipped",
                    "reason": "no_assignments"
                }
            )
            return True

        self.logger.info(
            f"Entering AssignmentRepository.save_all (count={len(assignments)})",
            extra={
                "event_type": "assignments_save",
                "assignment_count": len(assignments)
            }
        )

        # Validate all assignments first
        invalid_assignments = WorkAssignmentValidator.validate_batch(assignments)
        if invalid_assignments:
            self.logger.warning(
                f"Found {len(invalid_assignments)} invalid assignments that will be skipped",
                extra={
                    "event_type": "assignments_validation_failures",
                    "invalid_count": len(invalid_assignments)
                }
            )

            # Enhanced logging for invalid assignments
            for i, (assignment, error_msg) in enumerate(invalid_assignments[:5]):
                self.logger.error(
                    f"Assignment validation failed: {error_msg}",
                    extra={
                        "event_type": "assignment_validation_failure_detail",
                        "employee_id": getattr(assignment.employee, 'id', None) if assignment.employee else None,
                        "employee_name": getattr(assignment.employee, 'name', None) if hasattr(assignment, 'employee') and hasattr(assignment.employee, 'name') else None,
                        "workstation_id": getattr(assignment.workstation, 'id', None) if assignment.workstation else None,
                        "workstation_name": getattr(assignment.workstation, 'name', None) if hasattr(assignment, 'workstation') and hasattr(assignment.workstation, 'name') else None,
                        "date": str(getattr(assignment.period, 'date', None)) if assignment.period else None,
                        "period": getattr(assignment.period, 'period', None) if assignment.period else None,
                        "validation_error": error_msg,
                        "employee_exists": assignment.employee is not None,
                        "workstation_exists": assignment.workstation is not None,
                        "period_exists": assignment.period is not None
                    }
                )

            if len(invalid_assignments) > 5:
                self.logger.warning(
                    f"... and {len(invalid_assignments) - 5} more invalid assignments"
                )

            # Filter out invalid assignments
            valid_assignments = [a for a in assignments if a not in [ia[0] for ia in invalid_assignments]]
            assignments = valid_assignments

            self.logger.info(
                f"Proceeding with {len(assignments)} valid assignments",
                extra={
                    "event_type": "assignments_validation_summary",
                    "valid_count": len(assignments),
                    "invalid_count": len(invalid_assignments)
                }
            )

            if not assignments:
                self.logger.warning(
                    "No valid assignments to save after validation",
                    extra={
                        "event_type": "assignments_save_skipped",
                        "reason": "no_valid_assignments"
                    }
                )
                return False

        # Group assignments by date
        dates = set(assignment.period.date for assignment in assignments)

        self.logger.info(
            f"Assignments span {len(dates)} unique dates",
            extra={
                "event_type": "assignments_dates",
                "date_count": len(dates)
            }
        )

        # Delete existing entries for each date
        failed_dates = []
        for date_obj in dates:
            try:
                self.delete_existing_entries_for_date(date_obj)
            except Exception as e:
                error_msg = sanitize_exception(e)
                self.logger.error(
                    f"Error deleting existing entries for date {date_obj}: {error_msg}",
                    extra={
                        "event_type": "assignments_save_error",
                        "date": self._format_date(date_obj),
                        "error_type": type(e).__name__
                    }
                )
                failed_dates.append((date_obj, error_msg))

        # If there were any failures, raise an error with a summary
        if failed_dates:
            error_summary = "; ".join([f"{self._format_date(date)}: {error}" for date, error in failed_dates])
            raise RepositoryError(f"Failed to delete existing entries for some dates: {error_summary}")

        # Use session_scope context manager to ensure proper commit/rollback handling
        success_count = 0
        failed_assignments = []

        try:
            with self.session_scope() as session:
                # Process assignments in batches within the same session
                for i in range(0, len(assignments), batch_size):
                    batch = assignments[i:i+batch_size]

                    self.logger.info(
                        f"Processing batch {i//batch_size + 1} of {(len(assignments) + batch_size - 1) // batch_size} (size: {len(batch)})",
                        extra={
                            "event_type": "assignments_batch_processing",
                            "batch_number": i//batch_size + 1,
                            "total_batches": (len(assignments) + batch_size - 1) // batch_size,
                            "batch_size": len(batch)
                        }
                    )

                    batch_success_count = 0
                    batch_failed_count = 0

                    for idx, assignment in enumerate(batch):
                        try:
                            # Convert to model
                            self.rate_limited_logger.debug(
                                "Converting WorkAssignment to EmployeeWorkHistoryModel",
                                "domain_to_model_conversion",
                                str(assignment.employee.id),
                                extra={
                                    "employee_id": assignment.employee.id,
                                    "workstation_id": assignment.workstation.id
                                }
                            )

                            model = self._to_model(assignment)
                            session.add(model)
                            batch_success_count += 1
                        except Exception as e:
                            error_msg = sanitize_exception(e)
                            self.logger.error(
                                f"Error saving assignment: {error_msg}",
                                extra={
                                    "event_type": "assignment_save_error",
                                    "employee_id": assignment.employee.id,
                                    "workstation_id": assignment.workstation.id,
                                    "date": self._format_date(assignment.period.date),
                                    "period": assignment.period.period,
                                    "error_type": type(e).__name__
                                }
                            )
                            failed_assignments.append(assignment)
                            batch_failed_count += 1

                    # Flush after each batch to ensure all assignments in this batch are processed
                    # The session_scope context manager will handle the final commit
                    try:
                        session.flush()
                        self.logger.info(
                            f"Batch {i//batch_size + 1}: Successfully flushed {batch_success_count} assignments",
                            extra={
                                "event_type": "assignments_batch_flush_success",
                                "batch_number": i//batch_size + 1,
                                "flushed_count": batch_success_count
                            }
                        )
                    except Exception as e:
                        error_msg = sanitize_exception(e)
                        self.logger.error(
                            f"Error flushing batch {i//batch_size + 1}: {error_msg}",
                            extra={
                                "event_type": "batch_flush_error",
                                "batch_number": i//batch_size + 1,
                                "error_type": type(e).__name__
                            }
                        )
                        # Re-raise the exception to trigger rollback via session_scope
                        raise

                    self.logger.info(
                        f"Batch {i//batch_size + 1}: Processed {batch_success_count} assignments, {batch_failed_count} failed",
                        extra={
                            "event_type": "assignments_batch_result",
                            "batch_number": i//batch_size + 1,
                            "success_count": batch_success_count,
                            "failed_count": batch_failed_count
                        }
                    )

                    success_count += batch_success_count

                # Check if there were any failed assignments before allowing commit
                if failed_assignments:
                    error_msg = f"Cannot commit due to {len(failed_assignments)} failed assignments"
                    self.logger.warning(
                        error_msg,
                        extra={
                            "event_type": "assignments_commit_prevented",
                            "failed_count": len(failed_assignments)
                        }
                    )
                    raise RepositoryError(error_msg)

                # If we reach here, all batches were processed successfully
                # The session_scope context manager will automatically commit
                self.logger.info(
                    f"All {success_count} assignments processed successfully, ready for commit",
                    extra={
                        "event_type": "assignments_ready_for_commit",
                        "total_count": success_count
                    }
                )

            # If we reach here, the session_scope has successfully committed
            self.logger.info(
                "Successfully committed all assignments to the database",
                extra={
                    "event_type": "assignments_commit_success",
                    "total_count": success_count
                }
            )

            self.logger.info(
                f"Total: Successfully processed {success_count} assignments, {len(failed_assignments)} failed",
                extra={
                    "event_type": "assignments_save_result",
                    "success_count": success_count,
                    "failed_count": len(failed_assignments)
                }
            )

            # Return true only if there were no failed assignments and no invalid assignments
            return len(failed_assignments) == 0 and len(invalid_assignments) == 0

        except RepositoryError:
            # Re-raise RepositoryError as-is (these are already properly logged)
            raise
        except Exception as e:
            # Handle any unexpected errors not caught by session_scope
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in save_all: {error_msg}",
                extra={
                    "event_type": "assignments_save_unexpected_error",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Unexpected error saving assignments: {error_msg}")

    def delete_existing_entries_for_date(self, date_obj: date) -> int:
        """
        Delete all existing work history entries for a specific date.

        This method only deletes entries that were generated by the scheduler and are not temporary.

        Args:
            date_obj: The date for which to delete entries.

        Returns:
            The number of entries deleted.
        """
        self.logger.info(
            f"Entering AssignmentRepository.delete_existing_entries_for_date (date={date_obj})",
            extra={
                "event_type": "work_history_entries_deletion",
                "date": date_obj.isoformat() if hasattr(date_obj, 'isoformat') else str(date_obj)
            }
        )

        try:
            with self.session_scope() as session:
                # Find all entries for the given date that were generated by the scheduler and are not temporary
                query = session.query(EmployeeWorkHistoryModel).filter(
                    EmployeeWorkHistoryModel.worked_date == date_obj,
                    EmployeeWorkHistoryModel.status == WorkHistoryStatus.GENERATED
                )

                # Get the count before deleting
                count = query.count()

                self.logger.info(
                    f"Found {count} entries to delete for date: {date_obj}",
                    extra={
                        "event_type": "work_history_entries_found",
                        "date": date_obj.isoformat() if hasattr(date_obj, 'isoformat') else str(date_obj),
                        "count": count
                    }
                )

                if count > 0:
                    # Delete the entries
                    query.delete(synchronize_session='fetch')

                    # Flush the session to ensure the delete operation is executed
                    session.flush()

                    self.logger.info(
                        f"Successfully deleted {count} work history entries for date: {date_obj}",
                        extra={
                            "event_type": "work_history_entries_deletion_success",
                            "date": date_obj.isoformat() if hasattr(date_obj, 'isoformat') else str(date_obj),
                            "count": count
                        }
                    )
                else:
                    self.logger.info(
                        f"No work history entries found to delete for date: {date_obj}",
                        extra={
                            "event_type": "work_history_entries_deletion_skipped",
                            "date": date_obj.isoformat() if hasattr(date_obj, 'isoformat') else str(date_obj),
                            "reason": "no_entries_found"
                        }
                    )

                return count
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error deleting work history entries for date: {error_msg}",
                extra={
                    "event_type": "work_history_entries_deletion_error",
                    "date": date_obj.isoformat() if hasattr(date_obj, 'isoformat') else str(date_obj),
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error deleting work history entries: {error_msg}")

    def delete_by_schedule_id(self, schedule_id: int) -> bool:
        """
        Delete all assignments for a specific schedule.

        Args:
            schedule_id: ID of the schedule

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(
            f"Entering AssignmentRepository.delete_by_schedule_id (schedule_id={schedule_id})",
            extra={
                "event_type": "assignments_deletion",
                "schedule_id": schedule_id
            }
        )

        try:
            with self.session_scope() as session:
                # First, count how many assignments will be deleted
                count = session.query(EmployeeWorkHistoryModel).filter(
                    EmployeeWorkHistoryModel.schedule_id == schedule_id
                ).count()

                self.logger.info(
                    f"Found {count} assignments to delete for schedule ID: {schedule_id}",
                    extra={
                        "event_type": "assignments_deletion_count",
                        "schedule_id": schedule_id,
                        "count": count
                    }
                )

                if count > 0:
                    # Delete the assignments
                    session.query(EmployeeWorkHistoryModel).filter(
                        EmployeeWorkHistoryModel.schedule_id == schedule_id
                    ).delete(synchronize_session='fetch')

                    self.logger.info(
                        f"Successfully deleted {count} assignments for schedule ID: {schedule_id}",
                        extra={
                            "event_type": "assignments_deletion_success",
                            "schedule_id": schedule_id,
                            "count": count
                        }
                    )
                else:
                    self.logger.info(
                        f"No assignments found for schedule ID: {schedule_id}",
                        extra={
                            "event_type": "assignments_deletion_skipped",
                            "schedule_id": schedule_id,
                            "reason": "no_assignments_found"
                        }
                    )

                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error deleting assignments for schedule ID: {error_msg}",
                extra={
                    "event_type": "assignments_deletion_error",
                    "schedule_id": schedule_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error deleting assignments for schedule: {error_msg}")

    def create_temporary_assignment(self, employee_id: int, workstation_id: int, date_obj: date, period: int,
                                    schedule_id: int = None) -> bool:
        """
        Create a temporary assignment for an employee at a workstation.

        This method is used when an employee temporarily takes over a station from another employee.

        Args:
            employee_id: The ID of the employee taking over the station.
            workstation_id: The ID of the workstation being taken over.
            date_obj: The date of the assignment.
            period: The period of the day.
            schedule_id: Optional ID of the schedule this assignment belongs to.

        Returns:
            True if the assignment was created successfully, False otherwise.
        """
        self.logger.info(
            f"Entering AssignmentRepository.create_temporary_assignment (employee_id={employee_id}, workstation_id={workstation_id})",
            extra={
                "event_type": "temporary_assignment_creation",
                "employee_id": employee_id,
                "workstation_id": workstation_id,
                "date": date_obj.isoformat() if hasattr(date_obj, 'isoformat') else str(date_obj),
                "period": period,
                "schedule_id": schedule_id
            }
        )

        try:
            with self.session_scope() as session:
                # Create a new model for the temporary assignment
                model = EmployeeWorkHistoryModel(
                    employee_id=employee_id,
                    station_id=workstation_id,
                    schedule_id=schedule_id,
                    worked_date=date_obj,
                    work_period=period,
                    end_flag=False,  # Default value
                    status=WorkHistoryStatus.TEMPORARY  # This is a temporary assignment
                )
                session.add(model)

                self.logger.info(
                    "Successfully created temporary assignment",
                    extra={
                        "event_type": "temporary_assignment_creation_success",
                        "employee_id": employee_id,
                        "workstation_id": workstation_id,
                        "date": date_obj.isoformat() if hasattr(date_obj, 'isoformat') else str(date_obj),
                        "period": period,
                        "schedule_id": schedule_id
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error creating temporary assignment: {error_msg}",
                extra={
                    "event_type": "temporary_assignment_creation_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "date": self._format_date(date_obj),
                    "period": period,
                    "schedule_id": schedule_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error creating temporary assignment: {error_msg}")

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _format_date(self, date_obj: date) -> str:
        """
        Format a date object to string, handling different date types.

        Args:
            date_obj: The date object to format.

        Returns:
            A string representation of the date.
        """
        return date_obj.isoformat() if hasattr(date_obj, 'isoformat') else str(date_obj)

    def _convert_models_to_domain(self, models: List[EmployeeWorkHistoryModel], session: Optional[Session] = None) -> List[WorkAssignment]:
        """
        Convert a list of models to domain entities.

        Args:
            models: The list of SQLAlchemy models to convert.
            session: Optional existing session to use. If None, a new session will be created for each conversion.

        Returns:
            A list of domain entities.
        """
        assignments = []
        for model in models:
            self.rate_limited_logger.debug(
                f"Converting EmployeeWorkHistoryModel [id={model.id}] to domain WorkAssignment",
                "model_to_domain_conversion",
                str(model.id),
                extra={
                    "entity_id": model.id
                }
            )
            assignment = self._to_domain(model, session)
            if assignment:
                assignments.append(assignment)
        return assignments

    # -------------------------------------------------------------------------
    # Conversion Helpers
    # -------------------------------------------------------------------------

    def _to_domain(self, model: EmployeeWorkHistoryModel, session: Optional[Session] = None) -> Optional[WorkAssignment]:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert.
            session: Optional existing session to use. If None, a new session will be created.

        Returns:
            The domain entity, or None if conversion fails.
        """
        if session:
            return WorkAssignmentFactory.create_from_model(model, session, self.logger)
        else:
            with self.session_scope() as new_session:
                return WorkAssignmentFactory.create_from_model(model, new_session, self.logger)

    def _to_model(self, entity: WorkAssignment) -> EmployeeWorkHistoryModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        # Get metadata if available
        metadata = getattr(entity, '_metadata', {})

        # Extract metadata values or use defaults
        schedule_id = metadata.get('schedule_id', None)
        end_flag = metadata.get('end_flag', False)

        # Get status from metadata if available
        status = metadata.get('status', None)

        # For backward compatibility, also pass the boolean flags
        is_temporary = metadata.get('is_temporary', False)
        is_generated = metadata.get('is_generated', True)

        return WorkAssignmentFactory.create_model_from_entity(
            entity,
            schedule_id=schedule_id,
            status=status,
            is_temporary=is_temporary,
            is_generated=is_generated,
            end_flag=end_flag,
            logger=self.logger
        )

    def _update_model(self, model: EmployeeWorkHistoryModel, entity: WorkAssignment) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        WorkAssignmentFactory.update_model_from_entity(model, entity, self.logger)
