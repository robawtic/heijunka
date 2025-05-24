# heijunka/domain/repositories/interfaces/employee_training_repository.py
from abc import abstractmethod
from typing import List, Optional
from datetime import date

from domain.value_objects.employee_training import EmployeeTraining
from domain.repositories.interfaces.base_repository import BaseRepository


class EmployeeTrainingRepositoryInterface(BaseRepository[EmployeeTraining]):
    """
    Repository interface for employee training operations.
    
    This interface defines the contract for accessing and manipulating
    employee training records in the persistence layer.
    """
    
    @abstractmethod
    def add(self, training: EmployeeTraining) -> EmployeeTraining:
        """
        Add a new training record.
        
        Args:
            training: The training record to add
            
        Returns:
            The added training record
        """
        pass
    
    @abstractmethod
    def get_by_employee_and_workstation(self, employee_id: int, workstation_id: int) -> Optional[EmployeeTraining]:
        """
        Get a training record for a specific employee and workstation.
        
        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            
        Returns:
            The training record if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_by_employee(self, employee_id: int) -> List[EmployeeTraining]:
        """
        Get all training records for a specific employee.
        
        Args:
            employee_id: The ID of the employee
            
        Returns:
            A list of training records
        """
        pass
    
    @abstractmethod
    def get_by_workstation(self, workstation_id: int) -> List[EmployeeTraining]:
        """
        Get all training records for a specific workstation.
        
        Args:
            workstation_id: The ID of the workstation
            
        Returns:
            A list of training records
        """
        pass
    
    @abstractmethod
    def get_completed_trainings(self, employee_id: int) -> List[EmployeeTraining]:
        """
        Get all completed training records for a specific employee.
        
        Args:
            employee_id: The ID of the employee
            
        Returns:
            A list of completed training records
        """
        pass
    
    @abstractmethod
    def get_required_trainings(self, employee_id: int) -> List[EmployeeTraining]:
        """
        Get all required training records for a specific employee.
        
        Args:
            employee_id: The ID of the employee
            
        Returns:
            A list of required training records
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def delete(self, employee_id: int, workstation_id: int) -> bool:
        """
        Delete a training record.
        
        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            
        Returns:
            True if deleted, False if not found
        """
        pass