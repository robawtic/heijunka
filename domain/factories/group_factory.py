# domain/factories/group_factory.py
from typing import Optional, Any

from domain.entities.group import Group
from domain.models.GroupModel import GroupModel


class GroupFactory:
    """
    Factory class for creating Group domain entities.
    """

    @staticmethod
    def create_group(
        id: Optional[int] = None,
        name: str = "",
        department_id: Optional[int] = None
    ) -> Group:
        """
        Create a new Group entity with basic properties.

        Args:
            id: Optional group ID (None for new groups)
            name: Group name
            department_id: Optional department ID

        Returns:
            A new Group entity

        Raises:
            ValueError: If validation fails (e.g., empty name)
        """
        # Create a basic group
        group = Group(
            id=id or 0,
            name=name,
            department_id=department_id
        )

        # Validate the group
        group.validate()

        return group

    @staticmethod
    def create_from_model(model: GroupModel) -> Group:
        """
        Create a Group entity from a database model.

        Args:
            model: The database model to convert

        Returns:
            A new Group entity populated with data from the model

        Raises:
            ValueError: If validation fails
        """
        # Create the group
        group = Group(
            id=model.id,
            name=model.name,
            department_id=model.department_id
        )

        # Validate the group to ensure domain rules are enforced
        # even for entities loaded from the database
        group.validate()

        return group

    @staticmethod
    def to_model(entity: Group) -> GroupModel:
        """
        Convert a Group domain entity to a GroupModel.

        Args:
            entity: The domain entity to convert

        Returns:
            A new GroupModel populated with data from the entity
        """
        model = GroupModel(
            name=entity.name,
            department_id=entity.department_id
        )

        if entity.id is not None and entity.id > 0:
            model.id = entity.id

        return model

    @staticmethod
    def update_model(model: GroupModel, entity: Group) -> None:
        """
        Update a GroupModel with values from a Group domain entity.

        Args:
            model: The SQLAlchemy model to update
            entity: The domain entity with updated values
        """
        model.name = entity.name
        model.department_id = entity.department_id
