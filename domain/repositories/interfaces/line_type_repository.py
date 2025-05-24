# heijunka/domain/repositories/interfaces/line_type_repository.py
from abc import abstractmethod
from typing import List, Optional
from domain.value_objects.line_type import LineType
from domain.repositories.interfaces.base_repository import BaseRepository


class LineTypeRepositoryInterface(BaseRepository[LineType]):
    """
    Repository interface for LineType entities.

    This interface defines the contract for accessing and manipulating
    LineType entities in the persistence layer.
    """

    @abstractmethod
    def add(self, line_type: LineType) -> LineType:
        """
        Add a new line type to the repository.

        Args:
            line_type: The line type to add

        Returns:
            The added line type with updated ID
        """
        pass

    @abstractmethod
    def get_by_id(self, line_type_id: int) -> Optional[LineType]:
        """
        Get a line type by its ID.

        Args:
            line_type_id: The ID of the line type to retrieve

        Returns:
            The line type if found, None otherwise
        """
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[LineType]:
        """
        Get a line type by its name.

        Args:
            name: The name of the line type to retrieve

        Returns:
            The line type if found, None otherwise
        """
        pass

    @abstractmethod
    def get_all(self) -> List[LineType]:
        """
        Get all line types.

        Returns:
            A list of all line types
        """
        pass

    @abstractmethod
    def update(self, line_type_id: int, line_type: LineType) -> LineType:
        """
        Update an existing line type.

        Args:
            line_type_id: The ID of the line type to update
            line_type: The new line type value object

        Returns:
            The updated line type
        """
        pass

    @abstractmethod
    def delete(self, line_type_id: int) -> bool:
        """
        Delete a line type by its ID.

        Args:
            line_type_id: The ID of the line type to delete

        Returns:
            True if deleted, False if not found
        """
        pass
