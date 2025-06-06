# domain/factories/employee_training_factory.py
from typing import Optional
from domain.value_objects.employee_training import EmployeeTraining
from domain.models.EmployeeTrainingModel import EmployeeTrainingModel
from utilities.logging_factory import get_logger

logger = get_logger("heijunka.factories.employee_training")

class EmployeeTrainingFactory:
    """
    Factory for creating EmployeeTraining domain entities from EmployeeTrainingModel database models
    and vice versa.
    """

    @staticmethod
    def create_from_model(model: EmployeeTrainingModel) -> EmployeeTraining:
        """
        Create an EmployeeTraining domain entity from an EmployeeTrainingModel.

        Args:
            model: The database model to convert.

        Returns:
            An EmployeeTraining domain entity.
        """
        logger.debug(
            f"Converting EmployeeTrainingModel [id={model.id}] to domain EmployeeTraining",
            extra={
                "event_type": "model_to_domain_conversion",
                "entity_id": model.id,
                "employee_id": model.employee_id,
                "workstation_id": model.station_id
            }
        )

        return EmployeeTraining(
            employee_id=model.employee_id,
            workstation_id=model.station_id,
            required_training=model.required_training,
            date_completed=model.date_completed
        )

    @staticmethod
    def create_from_entity(entity: EmployeeTraining) -> EmployeeTrainingModel:
        """
        Create an EmployeeTrainingModel database model from an EmployeeTraining domain entity.

        Args:
            entity: The domain entity to convert.

        Returns:
            An EmployeeTrainingModel database model.
        """
        logger.debug(
            "Converting EmployeeTraining domain entity to model",
            extra={
                "event_type": "domain_to_model_conversion",
                "employee_id": entity.employee_id,
                "workstation_id": entity.workstation_id
            }
        )

        return EmployeeTrainingModel(
            employee_id=entity.employee_id,
            station_id=entity.workstation_id,
            required_training=entity.required_training,
            date_completed=entity.date_completed
        )

    @staticmethod
    def update_model_from_entity(model: EmployeeTrainingModel, entity: EmployeeTraining) -> None:
        """
        Update an EmployeeTrainingModel with values from an EmployeeTraining entity.

        Args:
            model: The database model to update.
            entity: The domain entity with updated values.
        """
        logger.debug(
            f"Updating EmployeeTrainingModel [id={model.id}] from domain entity",
            extra={
                "event_type": "model_update",
                "entity_id": model.id,
                "employee_id": entity.employee_id,
                "workstation_id": entity.workstation_id
            }
        )

        model.employee_id = entity.employee_id
        model.station_id = entity.workstation_id
        model.required_training = entity.required_training
        model.date_completed = entity.date_completed