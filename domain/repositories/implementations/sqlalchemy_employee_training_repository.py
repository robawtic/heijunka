# heijunka/domain/repositories/implementations/sqlalchemy_employee_training_repository.py
from typing import List, Optional
from datetime import date
from sqlalchemy import and_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from domain.value_objects.employee_training import EmployeeTraining
from domain.models.EmployeeTrainingModel import EmployeeTrainingModel
from domain.repositories.interfaces.employee_training_repository import EmployeeTrainingRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError


class SqlAlchemyEmployeeTrainingRepository(BaseSqlAlchemyRepository, EmployeeTrainingRepositoryInterface):
    """
    SQLAlchemy implementation of the EmployeeTrainingRepository interface.
    
    This class provides the actual implementation for accessing and manipulating
    employee training records in the database using SQLAlchemy.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.
        
        Args:
            session: The SQLAlchemy session to use
        """
        super().__init__(session)
    
    def add(self, training: EmployeeTraining) -> EmployeeTraining:
        """
        Add a new training record.
        
        Args:
            training: The training record to add
            
        Returns:
            The added training record
        """
        try:
            model = EmployeeTrainingModel(
                employee_id=training.employee_id,
                station_id=training.workstation_id,
                required_training=training.required_training,
                date_completed=training.date_completed
            )
            self._session.add(model)
            self._session.flush()
            return training
        except SQLAlchemyError as e:
            self._session.rollback()
            raise RepositoryError(f"Failed to add training record: {str(e)}")
    
    def get_by_employee_and_workstation(self, employee_id: int, workstation_id: int) -> Optional[EmployeeTraining]:
        """
        Get a training record for a specific employee and workstation.
        
        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            
        Returns:
            The training record if found, None otherwise
        """
        try:
            model = self._session.query(EmployeeTrainingModel).filter(
                and_(
                    EmployeeTrainingModel.employee_id == employee_id,
                    EmployeeTrainingModel.station_id == workstation_id
                )
            ).first()
            
            if not model:
                return None
            
            return EmployeeTraining(
                employee_id=model.employee_id,
                workstation_id=model.station_id,
                required_training=model.required_training,
                date_completed=model.date_completed
            )
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get training record: {str(e)}")
    
    def get_by_employee(self, employee_id: int) -> List[EmployeeTraining]:
        """
        Get all training records for a specific employee.
        
        Args:
            employee_id: The ID of the employee
            
        Returns:
            A list of training records
        """
        try:
            models = self._session.query(EmployeeTrainingModel).filter(
                EmployeeTrainingModel.employee_id == employee_id
            ).all()
            
            return [
                EmployeeTraining(
                    employee_id=model.employee_id,
                    workstation_id=model.station_id,
                    required_training=model.required_training,
                    date_completed=model.date_completed
                )
                for model in models
            ]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get training records by employee: {str(e)}")
    
    def get_by_workstation(self, workstation_id: int) -> List[EmployeeTraining]:
        """
        Get all training records for a specific workstation.
        
        Args:
            workstation_id: The ID of the workstation
            
        Returns:
            A list of training records
        """
        try:
            models = self._session.query(EmployeeTrainingModel).filter(
                EmployeeTrainingModel.station_id == workstation_id
            ).all()
            
            return [
                EmployeeTraining(
                    employee_id=model.employee_id,
                    workstation_id=model.station_id,
                    required_training=model.required_training,
                    date_completed=model.date_completed
                )
                for model in models
            ]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get training records by workstation: {str(e)}")
    
    def get_completed_trainings(self, employee_id: int) -> List[EmployeeTraining]:
        """
        Get all completed training records for a specific employee.
        
        Args:
            employee_id: The ID of the employee
            
        Returns:
            A list of completed training records
        """
        try:
            models = self._session.query(EmployeeTrainingModel).filter(
                and_(
                    EmployeeTrainingModel.employee_id == employee_id,
                    EmployeeTrainingModel.date_completed != None
                )
            ).all()
            
            return [
                EmployeeTraining(
                    employee_id=model.employee_id,
                    workstation_id=model.station_id,
                    required_training=model.required_training,
                    date_completed=model.date_completed
                )
                for model in models
            ]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get completed training records: {str(e)}")
    
    def get_required_trainings(self, employee_id: int) -> List[EmployeeTraining]:
        """
        Get all required training records for a specific employee.
        
        Args:
            employee_id: The ID of the employee
            
        Returns:
            A list of required training records
        """
        try:
            models = self._session.query(EmployeeTrainingModel).filter(
                and_(
                    EmployeeTrainingModel.employee_id == employee_id,
                    EmployeeTrainingModel.required_training == True
                )
            ).all()
            
            return [
                EmployeeTraining(
                    employee_id=model.employee_id,
                    workstation_id=model.station_id,
                    required_training=model.required_training,
                    date_completed=model.date_completed
                )
                for model in models
            ]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get required training records: {str(e)}")
    
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
        try:
            model = self._session.query(EmployeeTrainingModel).filter(
                and_(
                    EmployeeTrainingModel.employee_id == employee_id,
                    EmployeeTrainingModel.station_id == workstation_id
                )
            ).first()
            
            if not model:
                return None
            
            model.required_training = required
            model.date_completed = date_completed
            
            self._session.flush()
            
            return EmployeeTraining(
                employee_id=model.employee_id,
                workstation_id=model.station_id,
                required_training=model.required_training,
                date_completed=model.date_completed
            )
        except SQLAlchemyError as e:
            self._session.rollback()
            raise RepositoryError(f"Failed to update training status: {str(e)}")
    
    def delete(self, employee_id: int, workstation_id: int) -> bool:
        """
        Delete a training record.
        
        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            
        Returns:
            True if deleted, False if not found
        """
        try:
            model = self._session.query(EmployeeTrainingModel).filter(
                and_(
                    EmployeeTrainingModel.employee_id == employee_id,
                    EmployeeTrainingModel.station_id == workstation_id
                )
            ).first()
            
            if not model:
                return False
            
            self._session.delete(model)
            self._session.flush()
            return True
        except SQLAlchemyError as e:
            self._session.rollback()
            raise RepositoryError(f"Failed to delete training record: {str(e)}")
    
    def get(self, id: int) -> Optional[EmployeeTraining]:
        """
        Get an entity by ID.
        
        This method is required by the BaseRepository interface but is not directly applicable
        for EmployeeTraining since it's identified by a composite key.
        
        Args:
            id: The ID of the entity to retrieve
            
        Returns:
            None (not directly applicable for EmployeeTraining)
        """
        return None
    
    def get_all_entities(self) -> List[EmployeeTraining]:
        """
        Get all entities.
        
        Returns:
            A list of all training records
        """
        try:
            models = self._session.query(EmployeeTrainingModel).all()
            
            return [
                EmployeeTraining(
                    employee_id=model.employee_id,
                    workstation_id=model.station_id,
                    required_training=model.required_training,
                    date_completed=model.date_completed
                )
                for model in models
            ]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get all training records: {str(e)}")