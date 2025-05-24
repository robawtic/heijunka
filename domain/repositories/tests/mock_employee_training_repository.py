# heijunka/domain/repositories/tests/mock_employee_training_repository.py
from typing import List, Optional, Dict
from datetime import date

from domain.value_objects.employee_training import EmployeeTraining
from domain.repositories.interfaces.employee_training_repository import EmployeeTrainingRepositoryInterface


class MockEmployeeTrainingRepository(EmployeeTrainingRepositoryInterface):
    """
    Mock implementation of EmployeeTrainingRepositoryInterface for testing.
    
    This class provides an in-memory implementation of the EmployeeTrainingRepositoryInterface
    that can be used in unit tests without requiring a database connection.
    """
    
    def __init__(self):
        """Initialize with an empty list of training records."""
        self._trainings: List[EmployeeTraining] = []
    
    def add(self, training: EmployeeTraining) -> EmployeeTraining:
        """
        Add a new training record.
        
        Args:
            training: The training record to add
            
        Returns:
            The added training record
        """
        # Check if record already exists
        for existing in self._trainings:
            if (existing.employee_id == training.employee_id and
                existing.workstation_id == training.workstation_id):
                # Record already exists, replace it
                self._trainings.remove(existing)
                break
        
        # Add the new record
        self._trainings.append(training)
        return training
    
    def get_by_employee_and_workstation(self, employee_id: int, workstation_id: int) -> Optional[EmployeeTraining]:
        """
        Get a training record for a specific employee and workstation.
        
        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            
        Returns:
            The training record if found, None otherwise
        """
        for training in self._trainings:
            if (training.employee_id == employee_id and
                training.workstation_id == workstation_id):
                return training
        return None
    
    def get_by_employee(self, employee_id: int) -> List[EmployeeTraining]:
        """
        Get all training records for a specific employee.
        
        Args:
            employee_id: The ID of the employee
            
        Returns:
            A list of training records
        """
        return [
            training for training in self._trainings
            if training.employee_id == employee_id
        ]
    
    def get_by_workstation(self, workstation_id: int) -> List[EmployeeTraining]:
        """
        Get all training records for a specific workstation.
        
        Args:
            workstation_id: The ID of the workstation
            
        Returns:
            A list of training records
        """
        return [
            training for training in self._trainings
            if training.workstation_id == workstation_id
        ]
    
    def get_completed_trainings(self, employee_id: int) -> List[EmployeeTraining]:
        """
        Get all completed training records for a specific employee.
        
        Args:
            employee_id: The ID of the employee
            
        Returns:
            A list of completed training records
        """
        return [
            training for training in self._trainings
            if training.employee_id == employee_id and training.date_completed is not None
        ]
    
    def get_required_trainings(self, employee_id: int) -> List[EmployeeTraining]:
        """
        Get all required training records for a specific employee.
        
        Args:
            employee_id: The ID of the employee
            
        Returns:
            A list of required training records
        """
        return [
            training for training in self._trainings
            if training.employee_id == employee_id and training.required_training
        ]
    
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
        training = self.get_by_employee_and_workstation(employee_id, workstation_id)
        if not training:
            return None
        
        # Since EmployeeTraining is immutable (frozen), we need to create a new instance
        updated_training = EmployeeTraining(
            employee_id=employee_id,
            workstation_id=workstation_id,
            required_training=required,
            date_completed=date_completed
        )
        
        # Replace the old record with the updated one
        self._trainings.remove(training)
        self._trainings.append(updated_training)
        
        return updated_training
    
    def delete(self, employee_id: int, workstation_id: int) -> bool:
        """
        Delete a training record.
        
        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            
        Returns:
            True if deleted, False if not found
        """
        training = self.get_by_employee_and_workstation(employee_id, workstation_id)
        if not training:
            return False
        
        self._trainings.remove(training)
        return True
    
    def get(self, id: int) -> Optional[EmployeeTraining]:
        """
        Get an entity by ID.
        
        This method is required by the BaseRepository interface but is not applicable
        for EmployeeTraining since it doesn't have a single ID field.
        
        Args:
            id: The ID of the entity to retrieve
            
        Returns:
            None (not applicable for EmployeeTraining)
        """
        return None
    
    def get_all_entities(self) -> List[EmployeeTraining]:
        """
        Get all entities.
        
        Returns:
            A list of all training records
        """
        return self._trainings.copy()
    
    def clear(self) -> None:
        """
        Clear all records from the repository.
        
        This method is useful for testing to reset the repository state.
        """
        self._trainings.clear()