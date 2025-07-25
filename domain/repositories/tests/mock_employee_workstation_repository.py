# heijunka/domain/repositories/tests/mock_employee_workstation_repository.py
from typing import List, Optional, Dict
from datetime import date

from domain.contexts.assignment.value_objects.workstation_assignment import WorkstationAssignment
from domain.repositories.interfaces.employee_workstation_repository import EmployeeWorkstationRepositoryInterface


class MockEmployeeWorkstationRepository(EmployeeWorkstationRepositoryInterface):
    """
    Mock implementation of EmployeeWorkstationRepositoryInterface for testing.
    
    This class provides an in-memory implementation of the EmployeeWorkstationRepositoryInterface
    that can be used in unit tests without requiring a database connection.
    """
    
    def __init__(self):
        """Initialize with an empty list of workstation assignments."""
        self._assignments: List[WorkstationAssignment] = []
        self._last_worked_dates: Dict[tuple, date] = {}  # (employee_id, workstation_id) -> last_worked_date
    
    def add(self, assignment: WorkstationAssignment) -> WorkstationAssignment:
        """
        Add a new workstation assignment.
        
        Args:
            assignment: The workstation assignment to add
            
        Returns:
            The added workstation assignment
        """
        # Check if assignment already exists
        for existing in self._assignments:
            if (existing.employee_id == assignment.employee_id and
                existing.workstation_id == assignment.workstation_id):
                # Assignment already exists, replace it
                self._assignments.remove(existing)
                break
        
        # Add the new assignment
        self._assignments.append(assignment)
        return assignment
    
    def get_by_employee_and_workstation(self, employee_id: int, workstation_id: int) -> Optional[WorkstationAssignment]:
        """
        Get a workstation assignment for a specific employee and workstation.
        
        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            
        Returns:
            The workstation assignment if found, None otherwise
        """
        for assignment in self._assignments:
            if (assignment.employee_id == employee_id and
                assignment.workstation_id == workstation_id):
                return assignment
        return None
    
    def get_by_employee(self, employee_id: int) -> List[WorkstationAssignment]:
        """
        Get all workstation assignments for a specific employee.
        
        Args:
            employee_id: The ID of the employee
            
        Returns:
            A list of workstation assignments
        """
        return [
            assignment for assignment in self._assignments
            if assignment.employee_id == employee_id
        ]
    
    def get_by_workstation(self, workstation_id: int) -> List[WorkstationAssignment]:
        """
        Get all workstation assignments for a specific workstation.
        
        Args:
            workstation_id: The ID of the workstation
            
        Returns:
            A list of workstation assignments
        """
        return [
            assignment for assignment in self._assignments
            if assignment.workstation_id == workstation_id
        ]
    
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
        """
        assignment = self.get_by_employee_and_workstation(employee_id, workstation_id)
        if not assignment:
            return None
        
        # Store the last worked date in the dictionary
        key = (employee_id, workstation_id)
        if last_worked_date is None:
            if key in self._last_worked_dates:
                del self._last_worked_dates[key]
        else:
            self._last_worked_dates[key] = last_worked_date
        
        return assignment
    
    def delete(self, employee_id: int, workstation_id: int) -> bool:
        """
        Delete a workstation assignment.
        
        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            
        Returns:
            True if deleted, False if not found
        """
        assignment = self.get_by_employee_and_workstation(employee_id, workstation_id)
        if not assignment:
            return False
        
        self._assignments.remove(assignment)
        
        # Remove the last worked date if it exists
        key = (employee_id, workstation_id)
        if key in self._last_worked_dates:
            del self._last_worked_dates[key]
        
        return True
    
    def get(self, id: int) -> Optional[WorkstationAssignment]:
        """
        Get an entity by ID.
        
        This method is required by the BaseRepository interface but is not applicable
        for WorkstationAssignment since it doesn't have a single ID field.
        
        Args:
            id: The ID of the entity to retrieve
            
        Returns:
            None (not applicable for WorkstationAssignment)
        """
        return None
    
    def get_all_entities(self) -> List[WorkstationAssignment]:
        """
        Get all entities.
        
        Returns:
            A list of all workstation assignments
        """
        return self._assignments.copy()
    
    def clear(self) -> None:
        """
        Clear all assignments from the repository.
        
        This method is useful for testing to reset the repository state.
        """
        self._assignments.clear()
        self._last_worked_dates.clear()