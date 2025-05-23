# heijunka/domain/repositories/interfaces/employee_workstation_repository.py
from abc import abstractmethod
from typing import List, Optional
from datetime import date

from domain.value_objects.workstation_assignment import WorkstationAssignment
from domain.repositories.interfaces.base_repository import BaseRepository


class EmployeeWorkstationRepositoryInterface(BaseRepository[WorkstationAssignment]):
    """
    Repository interface for employee workstation operations.
    
    This interface defines the contract for accessing and manipulating
    employee workstation assignments in the persistence layer.
    """
    
    @abstractmethod
    def add(self, assignment: WorkstationAssignment) -> WorkstationAssignment:
        """
        Add a new workstation assignment.
        
        Args:
            assignment: The workstation assignment to add
            
        Returns:
            The added workstation assignment
        """
        pass
    
    @abstractmethod
    def get_by_employee_and_workstation(self, employee_id: int, workstation_id: int) -> Optional[WorkstationAssignment]:
        """
        Get a workstation assignment for a specific employee and workstation.
        
        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            
        Returns:
            The workstation assignment if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_by_employee(self, employee_id: int) -> List[WorkstationAssignment]:
        """
        Get all workstation assignments for a specific employee.
        
        Args:
            employee_id: The ID of the employee
            
        Returns:
            A list of workstation assignments
        """
        pass
    
    @abstractmethod
    def get_by_workstation(self, workstation_id: int) -> List[WorkstationAssignment]:
        """
        Get all workstation assignments for a specific workstation.
        
        Args:
            workstation_id: The ID of the workstation
            
        Returns:
            A list of workstation assignments
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def delete(self, employee_id: int, workstation_id: int) -> bool:
        """
        Delete a workstation assignment.
        
        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            
        Returns:
            True if deleted, False if not found
        """
        pass