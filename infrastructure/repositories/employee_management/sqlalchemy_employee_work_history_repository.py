# heijunka/domain/repositories/buses/sqlalchemy_employee_work_history_repository.py
from typing import List, Optional, Tuple, Set, Dict, Union
from datetime import date, datetime
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from domain.contexts.employee_management.value_objects.work_history_entry import WorkHistoryEntry
from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel, WorkHistoryStatus
from domain.repositories.interfaces.employee_work_history_repository import EmployeeWorkHistoryRepositoryInterface
from domain.factories.work_history_entry_factory import WorkHistoryEntryFactory
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger


class SqlAlchemyEmployeeWorkHistoryRepository(BaseSqlAlchemyRepository[WorkHistoryEntry, EmployeeWorkHistoryModel], EmployeeWorkHistoryRepositoryInterface):
    """
    SQLAlchemy implementation of the EmployeeWorkHistoryRepository interface.

    This class provides the actual implementation for accessing and manipulating
    employee work history entries in the database using SQLAlchemy.
    """

    def __init__(self, session_factory):
        """
        Initialize the repository with a SQLAlchemy session factory.

        Args:
            session_factory: The SQLAlchemy session factory to use for database operations.
        """
        super().__init__(session_factory, EmployeeWorkHistoryModel, WorkHistoryEntry)
        self.logger = get_logger("heijunka.repositories.employee_work_history")
        self.rate_limited_logger = get_logger("heijunka.repositories.employee_work_history", rate_limit=True)


    def add(self, work_history_entry: WorkHistoryEntry) -> WorkHistoryEntry:
        """
        Add a new work history entry.

        Args:
            work_history_entry: The work history entry to add

        Returns:
            The added work history entry

        Raises:
            RepositoryError: If there was an error adding the work history entry
        """
        self.logger.info(
            "Entering EmployeeWorkHistoryRepository.add",
            extra={
                "event_type": "work_history_entry_add",
                "employee_id": work_history_entry.employee_id,
                "workstation_id": work_history_entry.workstation_id,
                "worked_date": work_history_entry.worked_date.isoformat() if hasattr(work_history_entry.worked_date, 'isoformat') else str(work_history_entry.worked_date),
                "work_period": work_history_entry.work_period
            }
        )

        try:
            with self.session_scope() as session:
                # Use the factory to create the model
                model = WorkHistoryEntryFactory.create_from_entity(work_history_entry)
                session.add(model)
                session.flush()  # Flush to get the ID

                self.logger.info(
                    "Successfully added work history entry",
                    extra={
                        "event_type": "work_history_entry_add_success",
                        "entity_id": model.id,
                        "employee_id": work_history_entry.employee_id,
                        "workstation_id": work_history_entry.workstation_id
                    }
                )

                # Use the factory to convert back to domain entity
                return WorkHistoryEntryFactory.create_from_model(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeWorkHistoryRepository.add: {error_msg}",
                extra={
                    "event_type": "work_history_entry_add_error",
                    "employee_id": work_history_entry.employee_id,
                    "workstation_id": work_history_entry.workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to add work history entry: {error_msg}")

    def create(self, employee_id: int, workstation_id: int, date_obj: date, period: int, 
               schedule_id: Optional[int] = None, status: Optional[WorkHistoryStatus] = None,
               is_generated: bool = False, is_temporary: bool = False) -> WorkHistoryEntry:
        """
        Create a new work history entry with all fields.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            date_obj: The date of the work
            period: The period of the day
            schedule_id: Optional ID of the schedule this assignment belongs to
            status: The status of the work history entry (REGULAR, GENERATED, TEMPORARY, GENERATED_TEMPORARY)
            is_generated: (Deprecated) Whether this entry was generated by the scheduler
            is_temporary: (Deprecated) Whether this is a temporary assignment

        Returns:
            The created work history entry

        Raises:
            RepositoryError: If there was an error creating the work history entry
        """
        # Determine status based on parameters
        entry_status = status
        if entry_status is None:
            # Determine status from boolean flags for backward compatibility
            if is_generated and is_temporary:
                entry_status = WorkHistoryStatus.GENERATED_TEMPORARY
            elif is_generated:
                entry_status = WorkHistoryStatus.GENERATED
            elif is_temporary:
                entry_status = WorkHistoryStatus.TEMPORARY
            else:
                entry_status = WorkHistoryStatus.REGULAR

        self.logger.info(
            "Entering EmployeeWorkHistoryRepository.create",
            extra={
                "event_type": "work_history_entry_create",
                "employee_id": employee_id,
                "workstation_id": workstation_id,
                "worked_date": date_obj.isoformat() if hasattr(date_obj, 'isoformat') else str(date_obj),
                "work_period": period,
                "schedule_id": schedule_id,
                "status": entry_status.value if entry_status else None,
                "is_generated": is_generated,  # Keep for backward compatibility
                "is_temporary": is_temporary   # Keep for backward compatibility
            }
        )

        try:
            with self.session_scope() as session:
                # Use the factory to create the model with all fields
                model = WorkHistoryEntryFactory.create_with_all_fields(
                    employee_id=employee_id,
                    workstation_id=workstation_id,
                    worked_date=date_obj,
                    work_period=period,
                    end_flag=False,  # Default value
                    schedule_id=schedule_id,
                    status=entry_status
                )
                session.add(model)
                session.flush()

                # We need to refresh the model to get the ID
                session.refresh(model)

                self.logger.info(
                    "Successfully created work history entry",
                    extra={
                        "event_type": "work_history_entry_create_success",
                        "entity_id": model.id,
                        "employee_id": employee_id,
                        "workstation_id": workstation_id
                    }
                )

                # Use the factory to convert back to domain entity
                return WorkHistoryEntryFactory.create_from_model(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeWorkHistoryRepository.create: {error_msg}",
                extra={
                    "event_type": "work_history_entry_create_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to create work history entry: {error_msg}")

    def get_by_employee_and_workstation(self, employee_id: int, workstation_id: int) -> List[WorkHistoryEntry]:
        """
        Get all work history entries for a specific employee and workstation.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation

        Returns:
            A list of work history entries

        Raises:
            RepositoryError: If there was an error retrieving the work history entries
        """
        self.logger.info(
            "Entering EmployeeWorkHistoryRepository.get_by_employee_and_workstation",
            extra={
                "event_type": "work_history_entries_lookup",
                "lookup_type": "employee_and_workstation",
                "employee_id": employee_id,
                "workstation_id": workstation_id
            }
        )

        try:
            with self.session_scope() as session:
                models = session.query(EmployeeWorkHistoryModel).filter(
                    and_(
                        EmployeeWorkHistoryModel.employee_id == employee_id,
                        EmployeeWorkHistoryModel.station_id == workstation_id
                    )
                ).all()

                entry_count = len(models)
                self.logger.info(
                    f"Found {entry_count} work history entries for employee and workstation",
                    extra={
                        "event_type": "work_history_entries_lookup_success",
                        "lookup_type": "employee_and_workstation",
                        "employee_id": employee_id,
                        "workstation_id": workstation_id,
                        "entry_count": entry_count
                    }
                )

                # Use the factory to convert models to domain entities
                return [WorkHistoryEntryFactory.create_from_model(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeWorkHistoryRepository.get_by_employee_and_workstation: {error_msg}",
                extra={
                    "event_type": "work_history_entries_lookup_error",
                    "lookup_type": "employee_and_workstation",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get work history entries: {error_msg}")

    def get_last_worked_date(self, employee_id: int, workstation_id: int) -> Tuple[Optional[date], Optional[int]]:
        """
        Get the last date an employee worked at a specific workstation.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation

        Returns:
            A tuple containing the date and period, or (None, None) if no history exists

        Raises:
            RepositoryError: If there was an error retrieving the last worked date
        """
        self.logger.info(
            "Entering EmployeeWorkHistoryRepository.get_last_worked_date",
            extra={
                "event_type": "last_worked_date_lookup",
                "employee_id": employee_id,
                "workstation_id": workstation_id
            }
        )

        try:
            with self.session_scope() as session:
                entry = session.query(EmployeeWorkHistoryModel).filter(
                    and_(
                        EmployeeWorkHistoryModel.employee_id == employee_id,
                        EmployeeWorkHistoryModel.station_id == workstation_id
                    )
                ).order_by(
                    EmployeeWorkHistoryModel.worked_date.desc(),
                    EmployeeWorkHistoryModel.work_period.desc()
                ).first()

                if entry:
                    self.logger.info(
                        "Found last worked date for employee at workstation",
                        extra={
                            "event_type": "last_worked_date_lookup_success",
                            "employee_id": employee_id,
                            "workstation_id": workstation_id,
                            "worked_date": entry.worked_date.isoformat() if hasattr(entry.worked_date, 'isoformat') else str(entry.worked_date),
                            "work_period": entry.work_period
                        }
                    )
                    return entry.worked_date, entry.work_period

                self.logger.info(
                    "No work history found for employee at workstation",
                    extra={
                        "event_type": "last_worked_date_lookup_empty",
                        "employee_id": employee_id,
                        "workstation_id": workstation_id
                    }
                )
                return None, None
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeWorkHistoryRepository.get_last_worked_date: {error_msg}",
                extra={
                    "event_type": "last_worked_date_lookup_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get last worked date: {error_msg}")

    def get_by_date_range(self, start_date: Union[date, str], end_date: Union[date, str]) -> List[WorkHistoryEntry]:
        """
        Get all work history entries within a date range.

        Args:
            start_date: The start date (inclusive) - can be a date object or a string in YYYY-MM-DD format
            end_date: The end date (inclusive) - can be a date object or a string in YYYY-MM-DD format

        Returns:
            A list of work history entries

        Raises:
            RepositoryError: If there was an error retrieving the work history entries
        """
        # Convert string dates to date objects if needed
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise RepositoryError(f"Invalid start date format: {start_date}. Use YYYY-MM-DD")

        if isinstance(end_date, str):
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise RepositoryError(f"Invalid end date format: {end_date}. Use YYYY-MM-DD")

        self.logger.info(
            "Entering EmployeeWorkHistoryRepository.get_by_date_range",
            extra={
                "event_type": "work_history_entries_lookup",
                "lookup_type": "date_range",
                "start_date": start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date),
                "end_date": end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date)
            }
        )

        try:
            with self.session_scope() as session:
                models = session.query(EmployeeWorkHistoryModel).filter(
                    and_(
                        EmployeeWorkHistoryModel.worked_date >= start_date,
                        EmployeeWorkHistoryModel.worked_date <= end_date
                    )
                ).all()

                entry_count = len(models)
                self.logger.info(
                    f"Found {entry_count} work history entries in date range",
                    extra={
                        "event_type": "work_history_entries_lookup_success",
                        "lookup_type": "date_range",
                        "start_date": start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date),
                        "end_date": end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date),
                        "entry_count": entry_count
                    }
                )

                # Use the factory to convert models to domain entities
                return [WorkHistoryEntryFactory.create_from_model(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeWorkHistoryRepository.get_by_date_range: {error_msg}",
                extra={
                    "event_type": "work_history_entries_lookup_error",
                    "lookup_type": "date_range",
                    "start_date": start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date),
                    "end_date": end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date),
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get work history entries by date range: {error_msg}")

    def get_by_employee_date_range(self, employee_id: int, start_date: Union[date, str], end_date: Union[date, str]) -> List[WorkHistoryEntry]:
        """
        Get all work history entries for a specific employee within a date range.

        Args:
            employee_id: The ID of the employee
            start_date: The start date (inclusive) - can be a date object or a string in YYYY-MM-DD format
            end_date: The end date (inclusive) - can be a date object or a string in YYYY-MM-DD format

        Returns:
            A list of work history entries

        Raises:
            RepositoryError: If there was an error retrieving the work history entries
        """
        # Convert string dates to date objects if needed
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise RepositoryError(f"Invalid start date format: {start_date}. Use YYYY-MM-DD")

        if isinstance(end_date, str):
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise RepositoryError(f"Invalid end date format: {end_date}. Use YYYY-MM-DD")

        self.logger.info(
            "Entering EmployeeWorkHistoryRepository.get_by_employee_date_range",
            extra={
                "event_type": "work_history_entries_lookup",
                "lookup_type": "employee_date_range",
                "employee_id": employee_id,
                "start_date": start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date),
                "end_date": end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date)
            }
        )

        try:
            with self.session_scope() as session:
                models = session.query(EmployeeWorkHistoryModel).filter(
                    and_(
                        EmployeeWorkHistoryModel.employee_id == employee_id,
                        EmployeeWorkHistoryModel.worked_date >= start_date,
                        EmployeeWorkHistoryModel.worked_date <= end_date
                    )
                ).all()

                entry_count = len(models)
                self.logger.info(
                    f"Found {entry_count} work history entries for employee in date range",
                    extra={
                        "event_type": "work_history_entries_lookup_success",
                        "lookup_type": "employee_date_range",
                        "employee_id": employee_id,
                        "start_date": start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date),
                        "end_date": end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date),
                        "entry_count": entry_count
                    }
                )

                # Use the factory to convert models to domain entities
                return [WorkHistoryEntryFactory.create_from_model(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeWorkHistoryRepository.get_by_employee_date_range: {error_msg}",
                extra={
                    "event_type": "work_history_entries_lookup_error",
                    "lookup_type": "employee_date_range",
                    "employee_id": employee_id,
                    "start_date": start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date),
                    "end_date": end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date),
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get work history entries by employee and date range: {error_msg}")

    def delete(self, employee_id: int, workstation_id: int, worked_date: date, work_period: int) -> bool:
        """
        Delete a work history entry.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            worked_date: The date the work was performed
            work_period: The period of the day the work was performed

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If there was an error deleting the work history entry
        """
        self.logger.info(
            "Entering EmployeeWorkHistoryRepository.delete",
            extra={
                "event_type": "work_history_entry_delete",
                "employee_id": employee_id,
                "workstation_id": workstation_id,
                "worked_date": worked_date.isoformat() if hasattr(worked_date, 'isoformat') else str(worked_date),
                "work_period": work_period
            }
        )

        try:
            with self.session_scope() as session:
                entry = session.query(EmployeeWorkHistoryModel).filter(
                    and_(
                        EmployeeWorkHistoryModel.employee_id == employee_id,
                        EmployeeWorkHistoryModel.station_id == workstation_id,
                        EmployeeWorkHistoryModel.worked_date == worked_date,
                        EmployeeWorkHistoryModel.work_period == work_period
                    )
                ).first()

                if not entry:
                    self.logger.info(
                        "No work history entry found to delete",
                        extra={
                            "event_type": "work_history_entry_delete_failed",
                            "employee_id": employee_id,
                            "workstation_id": workstation_id,
                            "worked_date": worked_date.isoformat() if hasattr(worked_date, 'isoformat') else str(worked_date),
                            "work_period": work_period,
                            "reason": "not_found"
                        }
                    )
                    return False

                entity_id = entry.id

                # Log the entity being deleted
                self.logger.debug(
                    f"Deleting EmployeeWorkHistoryModel [id={entity_id}]",
                    extra={
                        "event_type": "entity_delete",
                        "entity_id": entity_id,
                        "employee_id": employee_id,
                        "workstation_id": workstation_id
                    }
                )

                session.delete(entry)

                self.logger.info(
                    "Successfully deleted work history entry",
                    extra={
                        "event_type": "work_history_entry_delete_success",
                        "entity_id": entity_id,
                        "employee_id": employee_id,
                        "workstation_id": workstation_id,
                        "worked_date": worked_date.isoformat() if hasattr(worked_date, 'isoformat') else str(worked_date),
                        "work_period": work_period
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeWorkHistoryRepository.delete: {error_msg}",
                extra={
                    "event_type": "work_history_entry_delete_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "worked_date": worked_date.isoformat() if hasattr(worked_date, 'isoformat') else str(worked_date),
                    "work_period": work_period,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to delete work history entry: {error_msg}")

    def delete_by_id(self, id: int) -> bool:
        """
        Delete a work history entry by its ID.

        Args:
            id: The ID of the work history entry to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            self.logger.info(
                "Deleting work history entry by ID",
                extra={
                    "event_type": "work_history_entry_delete",
                    "lookup_type": "id",
                    "entity_id": id
                }
            )

            with self.session_scope() as session:
                model = session.query(EmployeeWorkHistoryModel).get(id)
                if model is None:
                    self.logger.info(
                        "No work history entry found with the provided ID",
                        extra={
                            "event_type": "work_history_entry_delete_failed",
                            "lookup_type": "id",
                            "entity_id": id,
                            "reason": "not_found"
                        }
                    )
                    return False

                # Log details before deletion
                self.logger.info(
                    "Found work history entry to delete",
                    extra={
                        "event_type": "work_history_entry_delete_processing",
                        "entity_id": id,
                        "employee_id": model.employee_id,
                        "workstation_id": model.station_id,
                        "worked_date": model.worked_date.isoformat() if hasattr(model.worked_date, 'isoformat') else str(model.worked_date),
                        "work_period": model.work_period
                    }
                )

                session.delete(model)

                self.logger.info(
                    "Successfully deleted work history entry",
                    extra={
                        "event_type": "work_history_entry_delete_success",
                        "entity_id": id
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error deleting work history entry by ID: {error_msg}",
                extra={
                    "event_type": "work_history_entry_delete_error",
                    "lookup_type": "id",
                    "entity_id": id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to delete work history entry by ID: {error_msg}")

    def get(self, id: int) -> Optional[WorkHistoryEntry]:
        """
        Get an entity by ID.

        This method is required by the BaseRepository interface.

        Args:
            id: The ID of the entity to retrieve

        Returns:
            The work history entry if found, None otherwise
        """
        self.logger.debug(
            f"Calling get_by_id from get method for ID: {id}",
            extra={
                "event_type": "method_delegation",
                "from_method": "get",
                "to_method": "get_by_id",
                "entity_id": id
            }
        )
        return self.get_by_id(id)

    def get_by_id(self, id: int) -> Optional[WorkHistoryEntry]:
        """
        Get a work history entry by its ID.

        Args:
            id: The ID of the work history entry to retrieve

        Returns:
            The work history entry if found, None otherwise
        """
        try:
            self.logger.info(
                f"Retrieving work history entry by ID: {id}",
                extra={
                    "event_type": "work_history_entry_lookup",
                    "lookup_type": "id",
                    "entity_id": id
                }
            )

            with self.session_scope() as session:
                model = session.query(EmployeeWorkHistoryModel).get(id)
                if model is None:
                    self.logger.info(
                        f"No work history entry found with ID: {id}",
                        extra={
                            "event_type": "work_history_entry_lookup_failed",
                            "lookup_type": "id",
                            "entity_id": id,
                            "reason": "not_found"
                        }
                    )
                    return None

                self.logger.info(
                    f"Found work history entry with ID: {id}",
                    extra={
                        "event_type": "work_history_entry_lookup_success",
                        "lookup_type": "id",
                        "entity_id": id,
                        "employee_id": model.employee_id,
                        "workstation_id": model.station_id
                    }
                )
                return self._to_domain(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving work history entry by ID: {error_msg}",
                extra={
                    "event_type": "work_history_entry_lookup_error",
                    "lookup_type": "id",
                    "entity_id": id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get work history entry by ID: {error_msg}")

    def get_all_entities(self) -> List[WorkHistoryEntry]:
        """
        Get all entities.

        Returns:
            A list of all work history entries
        """
        try:
            self.logger.info(
                "Retrieving all work history entries",
                extra={
                    "event_type": "work_history_entries_list_all"
                }
            )

            with self.session_scope() as session:
                models = session.query(EmployeeWorkHistoryModel).all()

                entry_count = len(models)
                self.logger.info(
                    f"Retrieved {entry_count} work history entries",
                    extra={
                        "event_type": "work_history_entries_list_all_success",
                        "entry_count": entry_count
                    }
                )

                return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving all work history entries: {error_msg}",
                extra={
                    "event_type": "work_history_entries_list_all_error",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get all work history entries: {error_msg}")

    def _to_domain(self, model: EmployeeWorkHistoryModel) -> WorkHistoryEntry:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert

        Returns:
            The domain entity
        """
        try:
            self.logger.debug(
                f"Converting EmployeeWorkHistoryModel [id={model.id}] to domain WorkHistoryEntry",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "employee_id": model.employee_id,
                    "workstation_id": model.station_id
                }
            )

            # Use the factory to create the domain entity
            entry = WorkHistoryEntryFactory.create_from_model(model)

            self.logger.debug(
                "Successfully converted work history model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion_success",
                    "entity_id": model.id
                }
            )

            return entry
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting work history model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: WorkHistoryEntry) -> EmployeeWorkHistoryModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert

        Returns:
            The SQLAlchemy model
        """
        try:
            self.logger.debug(
                "Converting WorkHistoryEntry domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "employee_id": entity.employee_id,
                    "workstation_id": entity.workstation_id,
                    "worked_date": entity.worked_date.isoformat() if hasattr(entity.worked_date, 'isoformat') else str(entity.worked_date),
                    "work_period": entity.work_period
                }
            )

            # Use the factory to create the model
            model = WorkHistoryEntryFactory.create_from_entity(entity)

            self.logger.debug(
                "Successfully converted work history domain entity to model",
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
                f"Error converting work history domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "employee_id": entity.employee_id if entity and hasattr(entity, 'employee_id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: EmployeeWorkHistoryModel, entity: WorkHistoryEntry) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update
            entity: The domain entity with updated values
        """
        try:
            self.logger.debug(
                f"Updating EmployeeWorkHistoryModel [id={model.id}] from domain entity",
                extra={
                    "event_type": "work_history_model_update",
                    "entity_id": model.id,
                    "employee_id": model.employee_id,
                    "workstation_id": model.station_id
                }
            )

            # Use the factory to update the model
            WorkHistoryEntryFactory.update_model_from_entity(model, entity)

            self.logger.debug(
                "Successfully updated work history model",
                extra={
                    "event_type": "work_history_model_update_success",
                    "entity_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating work history model: {error_msg}",
                extra={
                    "event_type": "work_history_model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def update_by_id(self, id: int, employee_id: Optional[int] = None, 
                    workstation_id: Optional[int] = None, date_obj: Optional[date] = None, 
                    period: Optional[int] = None, schedule_id: Optional[int] = None,
                    status: Optional[WorkHistoryStatus] = None,
                    is_generated: Optional[bool] = None, is_temporary: Optional[bool] = None) -> Optional[WorkHistoryEntry]:
        """
        Update a work history entry by its ID.

        Args:
            id: The ID of the work history entry to update
            employee_id: Optional new employee ID
            workstation_id: Optional new workstation ID
            date_obj: Optional new date
            period: Optional new period
            schedule_id: Optional new schedule ID
            status: Optional new status (REGULAR, GENERATED, TEMPORARY, GENERATED_TEMPORARY)
            is_generated: (Deprecated) Optional new is_generated flag
            is_temporary: (Deprecated) Optional new is_temporary flag

        Returns:
            The updated work history entry if found, None otherwise
        """
        try:
            self.logger.info(
                f"Updating work history entry by ID: {id}",
                extra={
                    "event_type": "work_history_entry_update",
                    "entity_id": id
                }
            )

            # Build a log of what's being updated
            update_fields = {}
            if employee_id is not None:
                update_fields["employee_id"] = employee_id
            if workstation_id is not None:
                update_fields["workstation_id"] = workstation_id
            if date_obj is not None:
                update_fields["worked_date"] = date_obj.isoformat() if hasattr(date_obj, 'isoformat') else str(date_obj)
            if period is not None:
                update_fields["work_period"] = period
            if schedule_id is not None:
                update_fields["schedule_id"] = schedule_id
            if status is not None:
                update_fields["status"] = status.value
            # For backward compatibility
            if is_generated is not None:
                update_fields["is_generated"] = is_generated
            if is_temporary is not None:
                update_fields["is_temporary"] = is_temporary

            self.logger.info(
                "Fields to update",
                extra={
                    "event_type": "work_history_entry_update_fields",
                    "entity_id": id,
                    "update_fields": update_fields
                }
            )

            with self.session_scope() as session:
                model = session.query(EmployeeWorkHistoryModel).get(id)
                if model is None:
                    self.logger.info(
                        f"No work history entry found with ID: {id}",
                        extra={
                            "event_type": "work_history_entry_update_failed",
                            "entity_id": id,
                            "reason": "not_found"
                        }
                    )
                    return None

                # Log the current state before updates
                self.logger.debug(
                    "Current state before update",
                    extra={
                        "event_type": "work_history_entry_update_before",
                        "entity_id": id,
                        "employee_id": model.employee_id,
                        "workstation_id": model.station_id,
                        "worked_date": model.worked_date.isoformat() if hasattr(model.worked_date, 'isoformat') else str(model.worked_date),
                        "work_period": model.work_period,
                        "schedule_id": model.schedule_id,
                        "status": model.status.value if model.status else None
                    }
                )

                # Update fields if provided
                if employee_id is not None:
                    if model.employee_id != employee_id:
                        self.logger.info(
                            "Changing employee ID",
                            extra={
                                "event_type": "work_history_field_change",
                                "entity_id": id,
                                "field": "employee_id",
                                "old_value": model.employee_id,
                                "new_value": employee_id
                            }
                        )
                    model.employee_id = employee_id

                if workstation_id is not None:
                    if model.station_id != workstation_id:
                        self.logger.info(
                            "Changing workstation ID",
                            extra={
                                "event_type": "work_history_field_change",
                                "entity_id": id,
                                "field": "station_id",
                                "old_value": model.station_id,
                                "new_value": workstation_id
                            }
                        )
                    model.station_id = workstation_id

                if date_obj is not None:
                    if model.worked_date != date_obj:
                        self.logger.info(
                            "Changing worked date",
                            extra={
                                "event_type": "work_history_field_change",
                                "entity_id": id,
                                "field": "worked_date",
                                "old_value": model.worked_date.isoformat() if hasattr(model.worked_date, 'isoformat') else str(model.worked_date),
                                "new_value": date_obj.isoformat() if hasattr(date_obj, 'isoformat') else str(date_obj)
                            }
                        )
                    model.worked_date = date_obj

                if period is not None:
                    if model.work_period != period:
                        self.logger.info(
                            "Changing work period",
                            extra={
                                "event_type": "work_history_field_change",
                                "entity_id": id,
                                "field": "work_period",
                                "old_value": model.work_period,
                                "new_value": period
                            }
                        )
                    model.work_period = period

                if schedule_id is not None:
                    if model.schedule_id != schedule_id:
                        self.logger.info(
                            "Changing schedule ID",
                            extra={
                                "event_type": "work_history_field_change",
                                "entity_id": id,
                                "field": "schedule_id",
                                "old_value": model.schedule_id,
                                "new_value": schedule_id
                            }
                        )
                    model.schedule_id = schedule_id

                # Handle status update
                if status is not None:
                    if model.status != status:
                        self.logger.info(
                            "Changing status",
                            extra={
                                "event_type": "work_history_field_change",
                                "entity_id": id,
                                "field": "status",
                                "old_value": model.status.value if model.status else None,
                                "new_value": status.value
                            }
                        )
                    model.status = status
                # For backward compatibility, handle is_generated and is_temporary
                elif is_generated is not None or is_temporary is not None:
                    # Determine the new status based on the boolean flags
                    current_is_generated = is_generated if is_generated is not None else (model.status == WorkHistoryStatus.GENERATED or model.status == WorkHistoryStatus.GENERATED_TEMPORARY)
                    current_is_temporary = is_temporary if is_temporary is not None else (model.status == WorkHistoryStatus.TEMPORARY or model.status == WorkHistoryStatus.GENERATED_TEMPORARY)

                    if current_is_generated and current_is_temporary:
                        new_status = WorkHistoryStatus.GENERATED_TEMPORARY
                    elif current_is_generated:
                        new_status = WorkHistoryStatus.GENERATED
                    elif current_is_temporary:
                        new_status = WorkHistoryStatus.TEMPORARY
                    else:
                        new_status = WorkHistoryStatus.REGULAR

                    if model.status != new_status:
                        self.logger.info(
                            "Changing status based on boolean flags",
                            extra={
                                "event_type": "work_history_field_change",
                                "entity_id": id,
                                "field": "status",
                                "old_value": model.status.value if model.status else None,
                                "new_value": new_status.value,
                                "is_generated": current_is_generated,
                                "is_temporary": current_is_temporary
                            }
                        )
                    model.status = new_status

                session.flush()
                session.refresh(model)

                self.logger.info(
                    "Successfully updated work history entry",
                    extra={
                        "event_type": "work_history_entry_update_success",
                        "entity_id": id,
                        "employee_id": model.employee_id,
                        "workstation_id": model.station_id
                    }
                )

                return self._to_domain(model)
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating work history entry: {error_msg}",
                extra={
                    "event_type": "work_history_entry_update_error",
                    "entity_id": id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to update work history entry: {error_msg}")

    def get_filtered(self, team_id: Optional[int] = None, employee_id: Optional[int] = None, 
                    workstation_id: Optional[int] = None, start_date: Optional[Union[date, str]] = None, 
                    end_date: Optional[Union[date, str]] = None, period: Optional[int] = None,
                    status: Optional[WorkHistoryStatus] = None, is_generated: Optional[bool] = None, 
                    skip: int = 0, limit: int = 100) -> Tuple[List[WorkHistoryEntry], int]:
        """
        Get work history entries with filtering applied at the database level.

        Args:
            team_id: Filter by team ID
            employee_id: Filter by employee ID
            workstation_id: Filter by workstation ID
            start_date: Filter by start date (inclusive) - can be a date object or a string in YYYY-MM-DD format
            end_date: Filter by end date (inclusive) - can be a date object or a string in YYYY-MM-DD format
            period: Filter by work period
            status: Filter by status (REGULAR, GENERATED, TEMPORARY, GENERATED_TEMPORARY)
            is_generated: (Deprecated) Filter by whether the entry was generated by the scheduler
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            A tuple containing a list of work history entries and the total count
        """
        from domain.models.EmployeeModel import EmployeeModel
        from domain.models.WorkstationModel import WorkstationModel

        # Convert string dates to date objects if needed
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise RepositoryError(f"Invalid start date format: {start_date}. Use YYYY-MM-DD")

        if isinstance(end_date, str):
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise RepositoryError(f"Invalid end date format: {end_date}. Use YYYY-MM-DD")

        try:
            # Build a log of the filters being applied
            filters = {}
            if team_id is not None:
                filters["team_id"] = team_id
            if employee_id is not None:
                filters["employee_id"] = employee_id
            if workstation_id is not None:
                filters["workstation_id"] = workstation_id
            if start_date is not None:
                filters["start_date"] = start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date)
            if end_date is not None:
                filters["end_date"] = end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date)
            if period is not None:
                filters["period"] = period
            if status is not None:
                filters["status"] = status.value
            # For backward compatibility
            if is_generated is not None:
                filters["is_generated"] = is_generated

            self.logger.info(
                "Retrieving filtered work history entries",
                extra={
                    "event_type": "work_history_entries_filtered_lookup",
                    "filters": filters,
                    "pagination": {"skip": skip, "limit": limit}
                }
            )

            with self.session_scope() as session:
                # Start with a base query that joins with Employee and Workstation
                query = session.query(EmployeeWorkHistoryModel).\
                    join(EmployeeModel, EmployeeWorkHistoryModel.employee_id == EmployeeModel.id).\
                    join(WorkstationModel, EmployeeWorkHistoryModel.station_id == WorkstationModel.id)

                # Apply filters
                if team_id is not None:
                    # We can filter by either employee's team or workstation's team
                    query = query.filter(
                        or_(
                            EmployeeModel.team_id == team_id,
                            WorkstationModel.team_id == team_id
                        )
                    )

                if employee_id is not None:
                    query = query.filter(EmployeeWorkHistoryModel.employee_id == employee_id)

                if workstation_id is not None:
                    query = query.filter(EmployeeWorkHistoryModel.station_id == workstation_id)

                if start_date is not None:
                    query = query.filter(EmployeeWorkHistoryModel.worked_date >= start_date)

                if end_date is not None:
                    query = query.filter(EmployeeWorkHistoryModel.worked_date <= end_date)

                if period is not None:
                    query = query.filter(EmployeeWorkHistoryModel.work_period == period)

                if status is not None:
                    query = query.filter(EmployeeWorkHistoryModel.status == status)
                # For backward compatibility
                elif is_generated is not None:
                    # If is_generated is True, filter for GENERATED or GENERATED_TEMPORARY status
                    if is_generated:
                        query = query.filter(or_(
                            EmployeeWorkHistoryModel.status == WorkHistoryStatus.GENERATED,
                            EmployeeWorkHistoryModel.status == WorkHistoryStatus.GENERATED_TEMPORARY
                        ))
                    # If is_generated is False, filter for REGULAR or TEMPORARY status
                    else:
                        query = query.filter(or_(
                            EmployeeWorkHistoryModel.status == WorkHistoryStatus.REGULAR,
                            EmployeeWorkHistoryModel.status == WorkHistoryStatus.TEMPORARY
                        ))

                # Get total count for pagination
                total = query.count()

                # Apply pagination
                query = query.order_by(EmployeeWorkHistoryModel.worked_date.desc()).\
                    offset(skip).limit(limit)

                # Execute query
                models = query.all()
                entry_count = len(models)

                self.logger.info(
                    f"Found {entry_count} work history entries (total: {total}) with applied filters",
                    extra={
                        "event_type": "work_history_entries_filtered_lookup_success",
                        "filters": filters,
                        "pagination": {"skip": skip, "limit": limit},
                        "entry_count": entry_count,
                        "total_count": total
                    }
                )

                # Convert to domain entities
                return [self._to_domain(model) for model in models], total

        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving filtered work history entries: {error_msg}",
                extra={
                    "event_type": "work_history_entries_filtered_lookup_error",
                    "filters": filters if 'filters' in locals() else {},
                    "pagination": {"skip": skip, "limit": limit},
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get filtered work history entries: {error_msg}")

    def get_distinct_stations(
        self, employee_id: int, since: Union[date, str], until: Union[date, str]
    ) -> Set[int]:
        """
        Get all station IDs the employee worked at any period between since (inclusive) and until (exclusive).

        Args:
            employee_id: The ID of the employee
            since: The start date (inclusive) - can be a date object or a string in YYYY-MM-DD format
            until: The end date (exclusive) - can be a date object or a string in YYYY-MM-DD format

        Returns:
            A set of station IDs the employee worked at in the date range
        """
        # Convert string dates to date objects if needed
        if isinstance(since, str):
            try:
                since = datetime.strptime(since, "%Y-%m-%d").date()
            except ValueError:
                raise RepositoryError(f"Invalid since date format: {since}. Use YYYY-MM-DD")

        if isinstance(until, str):
            try:
                until = datetime.strptime(until, "%Y-%m-%d").date()
            except ValueError:
                raise RepositoryError(f"Invalid until date format: {until}. Use YYYY-MM-DD")

        try:
            self.logger.info(
                "Retrieving distinct stations for employee in date range",
                extra={
                    "event_type": "distinct_stations_lookup",
                    "employee_id": employee_id,
                    "since_date": since.isoformat() if hasattr(since, 'isoformat') else str(since),
                    "until_date": until.isoformat() if hasattr(until, 'isoformat') else str(until)
                }
            )

            with self.session_scope() as session:
                # Use a single optimized query with distinct to get all unique station_ids
                distinct_stations = (
                    session.query(EmployeeWorkHistoryModel.station_id)
                    .filter(
                        EmployeeWorkHistoryModel.employee_id == employee_id,
                        EmployeeWorkHistoryModel.worked_date >= since,
                        EmployeeWorkHistoryModel.worked_date < until
                    )
                    .distinct()
                    .all()
                )

                # Convert the result to a set of station IDs
                result = {station_id for (station_id,) in distinct_stations}

                self.logger.info(
                    f"Found {len(result)} distinct stations for employee in date range",
                    extra={
                        "event_type": "distinct_stations_lookup_success",
                        "employee_id": employee_id,
                        "station_count": len(result)
                    }
                )

                return result

        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving distinct stations: {error_msg}",
                extra={
                    "event_type": "distinct_stations_lookup_error",
                    "employee_id": employee_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get distinct stations: {error_msg}")

    def get_distinct_station_periods(
        self, employee_id: int, since: Union[date, str], until: Union[date, str]
    ) -> Set[Tuple[int, int]]:
        """
        Get all (station_id, work_period) pairs for that employee in the window.

        Args:
            employee_id: The ID of the employee
            since: The start date (inclusive) - can be a date object or a string in YYYY-MM-DD format
            until: The end date (exclusive) - can be a date object or a string in YYYY-MM-DD format

        Returns:
            A set of (station_id, work_period) tuples the employee worked in the date range
        """
        # Convert string dates to date objects if needed
        if isinstance(since, str):
            try:
                since = datetime.strptime(since, "%Y-%m-%d").date()
            except ValueError:
                raise RepositoryError(f"Invalid since date format: {since}. Use YYYY-MM-DD")

        if isinstance(until, str):
            try:
                until = datetime.strptime(until, "%Y-%m-%d").date()
            except ValueError:
                raise RepositoryError(f"Invalid until date format: {until}. Use YYYY-MM-DD")

        try:
            self.logger.info(
                "Retrieving distinct station-period pairs for employee in date range",
                extra={
                    "event_type": "distinct_station_periods_lookup",
                    "employee_id": employee_id,
                    "since_date": since.isoformat() if hasattr(since, 'isoformat') else str(since),
                    "until_date": until.isoformat() if hasattr(until, 'isoformat') else str(until)
                }
            )

            with self.session_scope() as session:
                # Use a single optimized query with distinct to get all unique (station_id, work_period) pairs
                distinct_pairs = (
                    session.query(
                        EmployeeWorkHistoryModel.station_id,
                        EmployeeWorkHistoryModel.work_period
                    )
                    .filter(
                        EmployeeWorkHistoryModel.employee_id == employee_id,
                        EmployeeWorkHistoryModel.worked_date >= since,
                        EmployeeWorkHistoryModel.worked_date < until
                    )
                    .distinct()
                    .all()
                )

                # Convert the result to a set of (station_id, work_period) tuples
                # Convert 1-based period to 0-based for the domain logic
                result = {(station_id, work_period - 1) for station_id, work_period in distinct_pairs}

                self.logger.info(
                    f"Found {len(result)} distinct station-period pairs for employee in date range",
                    extra={
                        "event_type": "distinct_station_periods_lookup_success",
                        "employee_id": employee_id,
                        "pair_count": len(result)
                    }
                )

                return result

        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving distinct station-period pairs: {error_msg}",
                extra={
                    "event_type": "distinct_station_periods_lookup_error",
                    "employee_id": employee_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get distinct station-period pairs: {error_msg}")

    def get_station_period_counts(
        self, employee_id: int, since: Union[date, str], until: Union[date, str]
    ) -> Dict[int, Dict[int, int]]:
        """
        Get mapping station_id → {period_index: count} over the date range.

        Args:
            employee_id: The ID of the employee
            since: The start date (inclusive) - can be a date object or a string in YYYY-MM-DD format
            until: The end date (exclusive) - can be a date object or a string in YYYY-MM-DD format

        Returns:
            A dictionary mapping station_id to a dictionary of period_index to count
        """
        # Convert string dates to date objects if needed
        if isinstance(since, str):
            try:
                since = datetime.strptime(since, "%Y-%m-%d").date()
            except ValueError:
                raise RepositoryError(f"Invalid since date format: {since}. Use YYYY-MM-DD")

        if isinstance(until, str):
            try:
                until = datetime.strptime(until, "%Y-%m-%d").date()
            except ValueError:
                raise RepositoryError(f"Invalid until date format: {until}. Use YYYY-MM-DD")

        try:
            self.logger.info(
                "Retrieving station-period counts for employee in date range",
                extra={
                    "event_type": "station_period_counts_lookup",
                    "employee_id": employee_id,
                    "since_date": since.isoformat() if hasattr(since, 'isoformat') else str(since),
                    "until_date": until.isoformat() if hasattr(until, 'isoformat') else str(until)
                }
            )

            # Use a single optimized query with aggregation to count occurrences
            counts = (
                self._session.query(
                    EmployeeWorkHistoryModel.station_id,
                    EmployeeWorkHistoryModel.work_period,
                    func.count().label("count")
                )
                .filter(
                    EmployeeWorkHistoryModel.employee_id == employee_id,
                    EmployeeWorkHistoryModel.worked_date >= since,
                    EmployeeWorkHistoryModel.worked_date < until
                )
                .group_by(
                    EmployeeWorkHistoryModel.station_id,
                    EmployeeWorkHistoryModel.work_period
                )
                .all()
            )

            # Convert the result to the required dictionary structure
            # Convert 1-based period to 0-based for the domain logic
            result = {}
            for station_id, work_period, count in counts:
                if station_id not in result:
                    result[station_id] = {}
                result[station_id][work_period - 1] = count

            self.logger.info(
                f"Found counts for {len(result)} stations for employee in date range",
                extra={
                    "event_type": "station_period_counts_lookup_success",
                    "employee_id": employee_id,
                    "station_count": len(result)
                }
            )

            return result

        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving station-period counts: {error_msg}",
                extra={
                    "event_type": "station_period_counts_lookup_error",
                    "employee_id": employee_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get station-period counts: {error_msg}")
