# heijunka/domain/contexts/employee_management/repositories/interfaces/employee_work_history_repository.py
from abc import abstractmethod
from typing import List, Optional, Tuple, Set, Dict, Union
from datetime import date

from domain.contexts.employee_management.value_objects.work_history_entry import WorkHistoryEntry
from domain.repositories.interfaces.base_repository import BaseRepository
from domain.models.EmployeeWorkHistoryModel import WorkHistoryStatus


class EmployeeWorkHistoryRepositoryInterface(BaseRepository[WorkHistoryEntry]):
    """
    Repository interface for employee work history operations.

    This interface defines the contract for accessing and manipulating
    employee work history entries in the persistence layer.
    """

    @abstractmethod
    def add(self, work_history_entry: WorkHistoryEntry) -> WorkHistoryEntry:
        """
        Add a new work history entry.

        Args:
            work_history_entry: The work history entry to add

        Returns:
            The added work history entry
        """
        pass

    @abstractmethod
    def create(self, employee_id: int, workstation_id: int, date_obj: date, period: int, 
               schedule_id: Optional[int] = None, status: Optional[WorkHistoryStatus] = None,
               ) -> WorkHistoryEntry:
        """
        Create a new work history entry with all fields.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            date_obj: The date of the work
            period: The period of the day
            schedule_id: Optional ID of the schedule this assignment belongs to
            status: The status of the work history entry (REGULAR, GENERATED, TEMPORARY, GENERATED_TEMPORARY)

        Returns:
            The created work history entry
        """
        pass

    @abstractmethod
    def get_by_employee_and_workstation(self, employee_id: int, workstation_id: int) -> List[WorkHistoryEntry]:
        """
        Get all work history entries for a specific employee and workstation.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation

        Returns:
            A list of work history entries
        """
        pass

    @abstractmethod
    def get_last_worked_date(self, employee_id: int, workstation_id: int) -> Tuple[Optional[date], Optional[int]]:
        """
        Get the last date an employee worked at a specific workstation.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation

        Returns:
            A tuple containing the date and period, or (None, None) if no history exists
        """
        pass

    @abstractmethod
    def get_by_date_range(self, start_date: date, end_date: date) -> List[WorkHistoryEntry]:
        """
        Get all work history entries within a date range.

        Args:
            start_date: The start date (inclusive)
            end_date: The end date (inclusive)

        Returns:
            A list of work history entries
        """
        pass

    @abstractmethod
    def get_by_employee_date_range(self, employee_id: int, start_date: date, end_date: date) -> List[WorkHistoryEntry]:
        """
        Get all work history entries for a specific employee within a date range.

        Args:
            employee_id: The ID of the employee
            start_date: The start date (inclusive)
            end_date: The end date (inclusive)

        Returns:
            A list of work history entries
        """
        pass

    @abstractmethod
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
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def get_distinct_stations(
        self, employee_id: int, since: date, until: date
    ) -> Set[int]:
        """
        Get all station IDs the employee worked at any period between since (inclusive) and until (exclusive).

        Args:
            employee_id: The ID of the employee
            since: The start date (inclusive)
            until: The end date (exclusive)

        Returns:
            A set of station IDs the employee worked at in the date range
        """
        pass

    @abstractmethod
    def get_distinct_station_periods(
        self, employee_id: int, since: date, until: date
    ) -> Set[Tuple[int, int]]:
        """
        Get all (station_id, work_period) pairs for that employee in the window.

        Args:
            employee_id: The ID of the employee
            since: The start date (inclusive)
            until: The end date (exclusive)

        Returns:
            A set of (station_id, work_period) tuples the employee worked in the date range
        """
        pass

    @abstractmethod
    def get_station_period_counts(
        self, employee_id: int, since: date, until: date
    ) -> Dict[int, Dict[int, int]]:
        """
        Get mapping station_id → {period_index: count} over the date range.

        Args:
            employee_id: The ID of the employee
            since: The start date (inclusive)
            until: The end date (exclusive)

        Returns:
            A dictionary mapping station_id to a dictionary of period_index to count
        """
        pass

    @abstractmethod
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
        pass