# heijunka/domain/repositories/implementations/sqlalchemy_employee_workstation_repository.py
from typing import List, Optional
from datetime import date
from sqlalchemy import and_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from domain.value_objects.workstation_assignment import WorkstationAssignment
from domain.models.EmployeeWorkstationModel import EmployeeWorkstationModel
from domain.models.WorkstationModel import WorkstationModel
from domain.repositories.interfaces.employee_workstation_repository import EmployeeWorkstationRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError


class SqlAlchemyEmployeeWorkstationRepository(BaseSqlAlchemyRepository, EmployeeWorkstationRepositoryInterface):
    """
    SQLAlchemy implementation of the EmployeeWorkstationRepository interface.
    
    This class provides the actual implementation for accessing and manipulating
    employee workstation assignments in the database using SQLAlchemy.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.
        
        Args:
            session: The SQLAlchemy session to use
        """
        super().__init__(session)
    
    def add(self, assignment: WorkstationAssignment) -> WorkstationAssignment:
        """
        Add a new workstation assignment.
        
        Args:
            assignment: The workstation assignment to add
            
        Returns:
            The added workstation assignment
        """
        try:
            model = EmployeeWorkstationModel(
                employee_id=assignment.employee_id,
                station_id=assignment.workstation_id,
                last_worked_date=None  # Initialize with no last worked date
            )
            self._session.add(model)
            self._session.flush()
            
            # Fetch the workstation name for the return value
            workstation = self._session.query(WorkstationModel).get(assignment.workstation_id)
            workstation_name = workstation.name if workstation else "Unknown"
            
            return WorkstationAssignment(
                employee_id=model.employee_id,
                workstation_id=model.station_id,
                workstation_name=workstation_name
            )
        except SQLAlchemyError as e:
            self._session.rollback()
            raise RepositoryError(f"Failed to add workstation assignment: {str(e)}")
    
    def get_by_employee_and_workstation(self, employee_id: int, workstation_id: int) -> Optional[WorkstationAssignment]:
        """
        Get a workstation assignment for a specific employee and workstation.
        
        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            
        Returns:
            The workstation assignment if found, None otherwise
        """
        try:
            model = self._session.query(EmployeeWorkstationModel).filter(
                and_(
                    EmployeeWorkstationModel.employee_id == employee_id,
                    EmployeeWorkstationModel.station_id == workstation_id
                )
            ).first()
            
            if not model:
                return None
            
            # Fetch the workstation name
            workstation = self._session.query(WorkstationModel).get(workstation_id)
            workstation_name = workstation.name if workstation else "Unknown"
            
            return WorkstationAssignment(
                employee_id=model.employee_id,
                workstation_id=model.station_id,
                workstation_name=workstation_name
            )
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get workstation assignment: {str(e)}")
    
    def get_by_employee(self, employee_id: int) -> List[WorkstationAssignment]:
        """
        Get all workstation assignments for a specific employee.
        
        Args:
            employee_id: The ID of the employee
            
        Returns:
            A list of workstation assignments
        """
        try:
            models = self._session.query(EmployeeWorkstationModel).filter(
                EmployeeWorkstationModel.employee_id == employee_id
            ).all()
            
            result = []
            for model in models:
                # Fetch the workstation name
                workstation = self._session.query(WorkstationModel).get(model.station_id)
                workstation_name = workstation.name if workstation else "Unknown"
                
                result.append(WorkstationAssignment(
                    employee_id=model.employee_id,
                    workstation_id=model.station_id,
                    workstation_name=workstation_name
                ))
            
            return result
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get workstation assignments by employee: {str(e)}")
    
    def get_by_workstation(self, workstation_id: int) -> List[WorkstationAssignment]:
        """
        Get all workstation assignments for a specific workstation.
        
        Args:
            workstation_id: The ID of the workstation
            
        Returns:
            A list of workstation assignments
        """
        try:
            models = self._session.query(EmployeeWorkstationModel).filter(
                EmployeeWorkstationModel.station_id == workstation_id
            ).all()
            
            # Fetch the workstation name once
            workstation = self._session.query(WorkstationModel).get(workstation_id)
            workstation_name = workstation.name if workstation else "Unknown"
            
            return [
                WorkstationAssignment(
                    employee_id=model.employee_id,
                    workstation_id=model.station_id,
                    workstation_name=workstation_name
                )
                for model in models
            ]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get workstation assignments by workstation: {str(e)}")
    
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
        try:
            model = self._session.query(EmployeeWorkstationModel).filter(
                and_(
                    EmployeeWorkstationModel.employee_id == employee_id,
                    EmployeeWorkstationModel.station_id == workstation_id
                )
            ).first()
            
            if not model:
                return None
            
            model.last_worked_date = last_worked_date
            self._session.flush()
            
            # Fetch the workstation name
            workstation = self._session.query(WorkstationModel).get(workstation_id)
            workstation_name = workstation.name if workstation else "Unknown"
            
            return WorkstationAssignment(
                employee_id=model.employee_id,
                workstation_id=model.station_id,
                workstation_name=workstation_name
            )
        except SQLAlchemyError as e:
            self._session.rollback()
            raise RepositoryError(f"Failed to update last worked date: {str(e)}")
    
    def delete(self, employee_id: int, workstation_id: int) -> bool:
        """
        Delete a workstation assignment.
        
        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            
        Returns:
            True if deleted, False if not found
        """
        try:
            model = self._session.query(EmployeeWorkstationModel).filter(
                and_(
                    EmployeeWorkstationModel.employee_id == employee_id,
                    EmployeeWorkstationModel.station_id == workstation_id
                )
            ).first()
            
            if not model:
                return False
            
            self._session.delete(model)
            self._session.flush()
            return True
        except SQLAlchemyError as e:
            self._session.rollback()
            raise RepositoryError(f"Failed to delete workstation assignment: {str(e)}")
    
    def get(self, id: int) -> Optional[WorkstationAssignment]:
        """
        Get an entity by ID.
        
        This method is required by the BaseRepository interface but is not directly applicable
        for WorkstationAssignment since it's identified by a composite key.
        
        Args:
            id: The ID of the entity to retrieve
            
        Returns:
            None (not directly applicable for WorkstationAssignment)
        """
        return None
    
    def get_all_entities(self) -> List[WorkstationAssignment]:
        """
        Get all entities.
        
        Returns:
            A list of all workstation assignments
        """
        try:
            models = self._session.query(EmployeeWorkstationModel).all()
            
            result = []
            for model in models:
                # Fetch the workstation name
                workstation = self._session.query(WorkstationModel).get(model.station_id)
                workstation_name = workstation.name if workstation else "Unknown"
                
                result.append(WorkstationAssignment(
                    employee_id=model.employee_id,
                    workstation_id=model.station_id,
                    workstation_name=workstation_name
                ))
            
            return result
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get all workstation assignments: {str(e)}")