# heijunka/domain/repositories/tests/mock_employee_work_history_repository.py
from typing import List, Optional, Tuple, Dict
from datetime import date

from domain.value_objects.work_history_entry import WorkHistoryEntry
from domain.repositories.interfaces.employee_work_history_repository import EmployeeWorkHistoryRepositoryInterface


class MockEmployeeWorkHistoryRepository(EmployeeWorkHistoryRepositoryInterface):
    """
    Mock implementation of EmployeeWorkHistoryRepositoryInterface for testing.
    
    This class provides an in-memory implementation of the EmployeeWorkHistoryRepositoryInterface
    that can be used in unit tests without requiring a database connection.
    """
    
    def __init__(self):
        """Initialize with an empty list of work history entries."""
        self._entries: List[WorkHistoryEntry] = []
    
    def add(self, work_history_entry: WorkHistoryEntry) -> WorkHistoryEntry:
        """
        Add a new work history entry.
        
        Args:
            work_history_entry: The work history entry to add
            
        Returns:
            The added work history entry
        """
        # Check if entry already exists
        for entry in self._entries:
            if (entry.employee_id == work_history_entry.employee_id and
                entry.workstation_id == work_history_entry.workstation_id and
                entry.worked_date == work_history_entry.worked_date and
                entry.work_period == work_history_entry.work_period):
                # Entry already exists, replace it
                self._entries.remove(entry)
                break
        
        # Add the new entry
        self._entries.append(work_history_entry)
        return work_history_entry
    
    def get_by_employee_and_workstation(self, employee_id: int, workstation_id: int) -> List[WorkHistoryEntry]:
        """
        Get all work history entries for a specific employee and workstation.
        
        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            
        Returns:
            A list of work history entries
        """
        return [
            entry for entry in self._entries
            if entry.employee_id == employee_id and entry.workstation_id == workstation_id
        ]
    
    def get_last_worked_date(self, employee_id: int, workstation_id: int) -> Tuple[Optional[date], Optional[int]]:
        """
        Get the last date an employee worked at a specific workstation.
        
        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            
        Returns:
            A tuple containing the date and period, or (None, None) if no history exists
        """
        entries = self.get_by_employee_and_workstation(employee_id, workstation_id)
        if not entries:
            return None, None
        
        # Sort by date and period in descending order
        entries.sort(key=lambda e: (e.worked_date, e.work_period), reverse=True)
        return entries[0].worked_date, entries[0].work_period
    
    def get_by_date_range(self, start_date: date, end_date: date) -> List[WorkHistoryEntry]:
        """
        Get all work history entries within a date range.
        
        Args:
            start_date: The start date (inclusive)
            end_date: The end date (inclusive)
            
        Returns:
            A list of work history entries
        """
        return [
            entry for entry in self._entries
            if start_date <= entry.worked_date <= end_date
        ]
    
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
        return [
            entry for entry in self._entries
            if entry.employee_id == employee_id and start_date <= entry.worked_date <= end_date
        ]
    
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
        for entry in self._entries:
            if (entry.employee_id == employee_id and
                entry.workstation_id == workstation_id and
                entry.worked_date == worked_date and
                entry.work_period == work_period):
                self._entries.remove(entry)
                return True
        return False
    
    def get(self, id: int) -> Optional[WorkHistoryEntry]:
        """
        Get an entity by ID.
        
        This method is required by the BaseRepository interface but is not applicable
        for WorkHistoryEntry since it doesn't have a single ID field.
        
        Args:
            id: The ID of the entity to retrieve
            
        Returns:
            None (not applicable for WorkHistoryEntry)
        """
        return None
    
    def get_all_entities(self) -> List[WorkHistoryEntry]:
        """
        Get all entities.
        
        Returns:
            A list of all work history entries
        """
        return self._entries.copy()
    
    def clear(self) -> None:
        """
        Clear all entries from the repository.
        
        This method is useful for testing to reset the repository state.
        """
        self._entries.clear()