# domain/factories/work_assignment_factory.py
from typing import Optional, List, Dict, Any
from datetime import date
from sqlalchemy.orm import Session

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment
from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel
from domain.models.EmployeeModel import EmployeeModel
from domain.models.WorkstationModel import WorkstationModel
from utilities.logging_factory import get_logger

class WorkAssignmentFactory:
    """
    Factory for creating WorkAssignment domain entities from database models and vice versa.
    This factory handles the mapping between domain entities and database models,
    ensuring proper separation of concerns and DDD purity.
    """
    
    @staticmethod
    def create_from_model(
        model: EmployeeWorkHistoryModel, 
        session: Session,
        logger=None
    ) -> Optional[WorkAssignment]:
        """
        Convert a SQLAlchemy model to a domain entity.
        
        Args:
            model: The SQLAlchemy model to convert
            session: The SQLAlchemy session to use for fetching related entities
            logger: Optional logger for logging conversion events
            
        Returns:
            A WorkAssignment domain entity, or None if conversion fails
            
        Raises:
            ValueError: If the model is invalid or related entities cannot be found
        """
        if logger is None:
            logger = get_logger("heijunka.factories.work_assignment")
            
        try:
            logger.debug(
                "Converting work history model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "employee_id": model.employee_id,
                    "station_id": model.station_id
                }
            )

            # Fetch the related employee and workstation
            employee_model = session.query(EmployeeModel).get(model.employee_id)
            workstation_model = session.query(WorkstationModel).get(model.station_id)

            if not employee_model or not workstation_model:
                error_msg = f"Related entity not found for work history entry {model.id}"
                logger.error(
                    error_msg,
                    extra={
                        "event_type": "model_to_domain_conversion_error",
                        "entity_id": model.id,
                        "employee_id": model.employee_id,
                        "station_id": model.station_id,
                        "reason": "related_entity_not_found"
                    }
                )
                return None

            # Convert to domain entities
            employee = employee_model.to_domain()
            workstation = workstation_model.to_domain()

            # Create schedule period
            period = SchedulePeriod(date=model.worked_date, period=model.work_period)

            # Create work assignment
            assignment = WorkAssignment(
                employee=employee,
                workstation=workstation,
                period=period
            )

            # Store metadata as attributes in a dictionary
            metadata = {
                'id': model.id,
                'schedule_id': model.schedule_id,
                'is_temporary': model.is_temporary,
                'is_generated': model.is_generated,
                'end_flag': model.end_flag
            }
            
            # Attach metadata to the assignment without modifying its structure
            setattr(assignment, '_metadata', metadata)

            logger.debug(
                "Successfully converted work history model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion_success",
                    "entity_id": model.id
                }
            )

            return assignment
        except Exception as e:
            if logger:
                logger.error(
                    f"Error converting work history model to domain entity: {str(e)}",
                    extra={
                        "event_type": "model_to_domain_conversion_error",
                        "entity_id": model.id if model else None,
                        "error_type": type(e).__name__
                    }
                )
            raise
    
    @staticmethod
    def create_model_from_entity(
        entity: WorkAssignment,
        schedule_id: Optional[int] = None,
        is_temporary: bool = False,
        is_generated: bool = True,
        end_flag: bool = False,
        logger=None
    ) -> EmployeeWorkHistoryModel:
        """
        Convert a domain entity to a SQLAlchemy model.
        
        Args:
            entity: The domain entity to convert
            schedule_id: Optional ID of the schedule this assignment belongs to
            is_temporary: Whether this is a temporary assignment
            is_generated: Whether this assignment was generated by the scheduler
            end_flag: Whether this is an end-of-day assignment
            logger: Optional logger for logging conversion events
            
        Returns:
            An EmployeeWorkHistoryModel
            
        Raises:
            ValueError: If the entity is invalid
        """
        if logger is None:
            logger = get_logger("heijunka.factories.work_assignment")
            
        try:
            logger.debug(
                "Converting work assignment domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "employee_id": entity.employee.id,
                    "workstation_id": entity.workstation.id,
                    "date": entity.period.date.isoformat() if hasattr(entity.period.date, 'isoformat') else str(entity.period.date),
                    "period": entity.period.period
                }
            )

            # Check if the entity has metadata from a previous conversion
            metadata = getattr(entity, '_metadata', {})
            
            # Use metadata values if available, otherwise use provided values
            model_id = metadata.get('id', None)  # None for new entities
            model_schedule_id = metadata.get('schedule_id', schedule_id)
            model_is_temporary = metadata.get('is_temporary', is_temporary)
            model_is_generated = metadata.get('is_generated', is_generated)
            model_end_flag = metadata.get('end_flag', end_flag)

            model = EmployeeWorkHistoryModel(
                id=model_id,
                employee_id=entity.employee.id,
                station_id=entity.workstation.id,
                schedule_id=model_schedule_id,
                worked_date=entity.period.date,
                work_period=entity.period.period,
                end_flag=model_end_flag,
                is_generated=model_is_generated,
                is_temporary=model_is_temporary
            )

            logger.debug(
                "Successfully converted work assignment domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion_success",
                    "employee_id": entity.employee.id,
                    "workstation_id": entity.workstation.id
                }
            )

            return model
        except Exception as e:
            if logger:
                logger.error(
                    f"Error converting work assignment domain entity to model: {str(e)}",
                    extra={
                        "event_type": "domain_to_model_conversion_error",
                        "employee_id": entity.employee.id if entity and hasattr(entity, 'employee') else None,
                        "workstation_id": entity.workstation.id if entity and hasattr(entity, 'workstation') else None,
                        "error_type": type(e).__name__
                    }
                )
            raise
    
    @staticmethod
    def update_model_from_entity(
        model: EmployeeWorkHistoryModel,
        entity: WorkAssignment,
        logger=None
    ) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.
        
        Args:
            model: The SQLAlchemy model to update
            entity: The domain entity with updated values
            logger: Optional logger for logging update events
            
        Raises:
            ValueError: If the model or entity is invalid
        """
        if logger is None:
            logger = get_logger("heijunka.factories.work_assignment")
            
        try:
            logger.debug(
                "Updating work history model from domain entity",
                extra={
                    "event_type": "model_update",
                    "entity_id": model.id,
                    "employee_id": entity.employee.id,
                    "workstation_id": entity.workstation.id
                }
            )

            # Update the model with values from the entity
            model.employee_id = entity.employee.id
            model.station_id = entity.workstation.id
            model.worked_date = entity.period.date
            model.work_period = entity.period.period
            
            # Update metadata if available
            metadata = getattr(entity, '_metadata', {})
            if 'schedule_id' in metadata and metadata['schedule_id'] is not None:
                model.schedule_id = metadata['schedule_id']
            if 'is_temporary' in metadata:
                model.is_temporary = metadata['is_temporary']
            if 'is_generated' in metadata:
                model.is_generated = metadata['is_generated']
            if 'end_flag' in metadata:
                model.end_flag = metadata['end_flag']

            logger.debug(
                "Successfully updated work history model",
                extra={
                    "event_type": "model_update_success",
                    "entity_id": model.id
                }
            )
        except Exception as e:
            if logger:
                logger.error(
                    f"Error updating work history model: {str(e)}",
                    extra={
                        "event_type": "model_update_error",
                        "entity_id": model.id if model else None,
                        "error_type": type(e).__name__
                    }
                )
            raise