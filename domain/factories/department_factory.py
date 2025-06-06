# domain/factories/department_factory.py
from typing import List, Optional, Any

from domain.entities.department import Department
from domain.entities.group import Group
from domain.models.DepartmentModel import DepartmentModel
from domain.models.GroupModel import GroupModel

class DepartmentFactory:
    """
    Factory for creating Department domain entities from database models and vice versa.
    This factory encapsulates the logic for mapping between domain entities and database models,
    maintaining DDD purity by keeping this responsibility out of the repository.
    """
    
    @staticmethod
    def create_department(
        id: Optional[int] = None,
        name: str = "",
        description: Optional[str] = None,
        groups: Optional[List[Group]] = None
    ) -> Department:
        """
        Create a new Department entity with basic properties.

        Args:
            id: Optional department ID (None for new departments)
            name: Department name
            description: Department description
            groups: Optional list of Group entities

        Returns:
            A new Department entity

        Raises:
            ValueError: If validation fails (e.g., empty name)
        """
        # Create a basic department without groups
        department = Department(
            id=id or 0,
            name=name,
            description=description
        )

        # Add groups if provided
        if groups:
            for group in groups:
                department.add_group(group)

        # Validate the department
        department.validate()

        return department

    @staticmethod
    def create_from_model(model: DepartmentModel) -> Department:
        """
        Create a Department entity from a database model.

        Args:
            model: The database model to convert

        Returns:
            A new Department entity populated with data from the model

        Raises:
            ValueError: If validation fails
        """
        # Create the department
        department = Department(
            id=model.id,
            name=model.name,
            description=model.description
        )

        # Add groups if they exist
        if hasattr(model, 'groups') and model.groups:
            from domain.factories.group_factory import GroupFactory
            for group_model in model.groups:
                group = GroupFactory.create_from_model(group_model)
                department.add_group(group)

        return department

    @staticmethod
    def to_model(entity: Department) -> DepartmentModel:
        """
        Convert a Department domain entity to a DepartmentModel.

        Args:
            entity: The domain entity to convert

        Returns:
            The SQLAlchemy model
        """
        model = DepartmentModel(
            name=entity.name,
            description=entity.description
        )

        if entity.id is not None:
            model.id = entity.id

        return model

    @staticmethod
    def update_model(model: DepartmentModel, entity: Department) -> None:
        """
        Update a DepartmentModel with values from a Department domain entity.

        Args:
            model: The SQLAlchemy model to update
            entity: The domain entity with updated values
        """
        model.name = entity.name
        model.description = entity.description