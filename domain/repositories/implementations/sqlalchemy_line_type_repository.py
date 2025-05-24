# heijunka/domain/repositories/implementations/sqlalchemy_line_type_repository.py
from typing import List, Optional
from sqlalchemy.orm import Session
from domain.value_objects.line_type import LineType
from domain.models.LineTypeModel import LineTypeModel
from domain.repositories.interfaces.line_type_repository import LineTypeRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository


class SqlAlchemyLineTypeRepository(BaseSqlAlchemyRepository, LineTypeRepositoryInterface):
    """
    SQLAlchemy implementation of the LineTypeRepository interface.

    This class provides the actual implementation for accessing and manipulating
    LineType entities in the database using SQLAlchemy.
    """

    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session: The SQLAlchemy session to use
        """
        super().__init__(session)

    def add(self, line_type: LineType) -> LineType:
        """
        Add a new line type to the repository.

        Args:
            line_type: The line type to add

        Returns:
            The added line type with updated ID
        """
        model = LineTypeModel.from_value_object(line_type)
        self._session.add(model)
        self._session.flush()
        return model.to_value_object()

    def get_by_id(self, line_type_id: int) -> Optional[LineType]:
        """
        Get a line type by its ID.

        Args:
            line_type_id: The ID of the line type to retrieve

        Returns:
            The line type if found, None otherwise
        """
        model = self._session.query(LineTypeModel).filter(LineTypeModel.id == line_type_id).first()
        return model.to_value_object() if model else None

    def get_by_name(self, name: str) -> Optional[LineType]:
        """
        Get a line type by its name.

        Args:
            name: The name of the line type to retrieve

        Returns:
            The line type if found, None otherwise
        """
        model = self._session.query(LineTypeModel).filter(LineTypeModel.name == name).first()
        return model.to_value_object() if model else None

    def get_all(self) -> List[LineType]:
        """
        Get all line types.

        Returns:
            A list of all line types
        """
        models = self._session.query(LineTypeModel).all()
        return [model.to_value_object() for model in models]

    def update(self, line_type_id: int, line_type: LineType) -> LineType:
        """
        Update an existing line type.

        Args:
            line_type_id: The ID of the line type to update
            line_type: The new line type value object

        Returns:
            The updated line type
        """
        model = self._session.query(LineTypeModel).filter(LineTypeModel.id == line_type_id).first()
        if not model:
            raise ValueError(f"Line type with ID {line_type_id} not found")

        model.name = line_type.name
        model.description = line_type.description

        self._session.flush()
        return model.to_value_object()

    def delete(self, line_type_id: int) -> bool:
        """
        Delete a line type by its ID.

        Args:
            line_type_id: The ID of the line type to delete

        Returns:
            True if deleted, False if not found
        """
        model = self._session.query(LineTypeModel).filter(LineTypeModel.id == line_type_id).first()
        if not model:
            return False

        self._session.delete(model)
        self._session.flush()
        return True
