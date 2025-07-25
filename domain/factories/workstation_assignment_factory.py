# domain/factories/workstation_assignment_factory.py
from typing import Optional
from domain.contexts.assignment.value_objects.workstation_assignment import WorkstationAssignment
from domain.models.EmployeeWorkstationModel import EmployeeWorkstationModel
from domain.models.WorkstationModel import WorkstationModel
from utilities.logging_factory import get_logger

logger = get_logger("heijunka.factories.workstation_assignment")

class WorkstationAssignmentFactory:
    """
    Factory for creating WorkstationAssignment domain entities from EmployeeWorkstationModel database models
    and vice versa.
    """

    @staticmethod
    def create_from_model(model: EmployeeWorkstationModel, workstation_name: str = "Unknown") -> WorkstationAssignment:
        """
        Create a WorkstationAssignment domain entity from an EmployeeWorkstationModel.

        Args:
            model: The database model to convert.
            workstation_name: The name of the workstation. If not provided, "Unknown" will be used.

        Returns:
            A WorkstationAssignment domain entity.
        """
        logger.debug(
            f"Converting EmployeeWorkstationModel [id={model.id}] to domain WorkstationAssignment",
            extra={
                "event_type": "model_to_domain_conversion",
                "entity_id": model.id,
                "employee_id": model.employee_id,
                "workstation_id": model.station_id
            }
        )

        return WorkstationAssignment(
            employee_id=model.employee_id,
            workstation_id=model.station_id,
            workstation_name=workstation_name
        )

    @staticmethod
    def create_from_model_with_session(model: EmployeeWorkstationModel, session) -> WorkstationAssignment:
        """
        Create a WorkstationAssignment domain entity from an EmployeeWorkstationModel,
        fetching the workstation name from the database.

        Args:
            model: The database model to convert.
            session: The SQLAlchemy session to use for fetching the workstation name.

        Returns:
            A WorkstationAssignment domain entity.
        """
        logger.debug(
            f"Converting EmployeeWorkstationModel [id={model.id}] to domain WorkstationAssignment with session",
            extra={
                "event_type": "model_to_domain_conversion",
                "entity_id": model.id,
                "employee_id": model.employee_id,
                "workstation_id": model.station_id
            }
        )

        # Fetch the workstation name
        workstation = session.query(WorkstationModel).get(model.station_id)
        workstation_name = workstation.name if workstation else "Unknown"

        return WorkstationAssignment(
            employee_id=model.employee_id,
            workstation_id=model.station_id,
            workstation_name=workstation_name
        )

    @staticmethod
    def create_from_entity(entity: WorkstationAssignment) -> EmployeeWorkstationModel:
        """
        Create an EmployeeWorkstationModel database model from a WorkstationAssignment domain entity.

        Args:
            entity: The domain entity to convert.

        Returns:
            An EmployeeWorkstationModel database model.
        """
        logger.debug(
            "Converting WorkstationAssignment domain entity to model",
            extra={
                "event_type": "domain_to_model_conversion",
                "employee_id": entity.employee_id,
                "workstation_id": entity.workstation_id
            }
        )

        return EmployeeWorkstationModel(
            employee_id=entity.employee_id,
            station_id=entity.workstation_id,
            last_worked_date=None  # Initialize with no last worked date
        )

    @staticmethod
    def update_model_from_entity(model: EmployeeWorkstationModel, entity: WorkstationAssignment) -> None:
        """
        Update an EmployeeWorkstationModel with values from a WorkstationAssignment entity.

        Args:
            model: The database model to update.
            entity: The domain entity with updated values.
        """
        logger.debug(
            f"Updating EmployeeWorkstationModel [id={model.id}] from domain entity",
            extra={
                "event_type": "model_update",
                "entity_id": model.id,
                "employee_id": entity.employee_id,
                "workstation_id": entity.workstation_id
            }
        )

        # Check for significant changes and log them
        if model.employee_id != entity.employee_id:
            logger.info(
                "Changing workstation assignment employee",
                extra={
                    "event_type": "workstation_assignment_field_change",
                    "entity_id": model.id,
                    "field": "employee_id",
                    "old_value": model.employee_id,
                    "new_value": entity.employee_id
                }
            )

        if model.station_id != entity.workstation_id:
            logger.info(
                "Changing workstation assignment workstation",
                extra={
                    "event_type": "workstation_assignment_field_change",
                    "entity_id": model.id,
                    "field": "station_id",
                    "old_value": model.station_id,
                    "new_value": entity.workstation_id
                }
            )

        # Update the model
        model.employee_id = entity.employee_id
        model.station_id = entity.workstation_id