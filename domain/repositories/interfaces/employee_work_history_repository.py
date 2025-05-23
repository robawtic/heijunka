# heijunka/domain/repositories/interfaces/employee_work_history_repository.py
from abc import abstractmethod
from typing import List, Optional, Tuple
from datetime import date

from domain.value_objects.work_history_entry import WorkHistoryEntry
from domain.repositories.interfaces.base_repository import BaseRepository


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
                    workstation_id: Optional[int] = None, start_date: Optional[date] = None, 
                    end_date: Optional[date] = None, period: Optional[int] = None,
                    skip: int = 0, limit: int = 100) -> Tuple[List[WorkHistoryEntry], int]:
        """
        Get work history entries with filtering applied at the database level.

        Args:
            team_id: Filter by team ID
            employee_id: Filter by employee ID
            workstation_id: Filter by workstation ID
            start_date: Filter by start date (inclusive)
            end_date: Filter by end date (inclusive)
            period: Filter by work period
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            A tuple containing a list of work history entries and the total count
        """
        pass
