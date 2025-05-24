# heijunka/domain/repositories/tests/mock_line_type_repository.py
from typing import Dict, List, Optional
from domain.value_objects.line_type import LineType
from domain.repositories.interfaces.line_type_repository import LineTypeRepositoryInterface


class MockLineTypeRepository(LineTypeRepositoryInterface):
    """
    Mock implementation of LineTypeRepositoryInterface for testing.

    This class provides an in-memory implementation of the LineTypeRepositoryInterface
    that can be used in unit tests without requiring a database connection.
    """

    def __init__(self):
        """Initialize with an empty dictionary of line types."""
        self._line_types: Dict[int, LineType] = {}
        self._next_id = 1

    def add(self, line_type: LineType) -> LineType:
        """
        Add a new line type to the repository.

        Args:
            line_type: The line type value object to add

        Returns:
            The added line type value object
        """
        # Assign a new ID
        new_id = self._next_id
        self._next_id += 1

        # Store the value object
        self._line_types[new_id] = line_type

        return line_type

    def get_by_id(self, line_type_id: int) -> Optional[LineType]:
        """
        Get a line type by its ID.

        Args:
            line_type_id: The ID of the line type to retrieve

        Returns:
            The line type if found, None otherwise
        """
        return self._line_types.get(line_type_id)

    def get_by_name(self, name: str) -> Optional[LineType]:
        """
        Get a line type by its name.

        Args:
            name: The name of the line type to retrieve

        Returns:
            The line type if found, None otherwise
        """
        for line_type in self._line_types.values():
            if line_type.name == name:
                return line_type
        return None

    def get_all(self) -> List[LineType]:
        """
        Get all line types.

        Returns:
            A list of all line types
        """
        return list(self._line_types.values())

    def update(self, line_type_id: int, line_type: LineType) -> LineType:
        """
        Update an existing line type.

        Args:
            line_type_id: The ID of the line type to update
            line_type: The new line type value object

        Returns:
            The updated line type value object
        """
        if line_type_id not in self._line_types:
            raise ValueError(f"Line type with ID {line_type_id} not found")

        # Store the value object
        self._line_types[line_type_id] = line_type

        return line_type

    def delete(self, line_type_id: int) -> bool:
        """
        Delete a line type by its ID.

        Args:
            line_type_id: The ID of the line type to delete

        Returns:
            True if deleted, False if not found
        """
        if line_type_id not in self._line_types:
            return False

        del self._line_types[line_type_id]
        return True

    def get(self, id: int) -> Optional[LineType]:
        """
        Get an entity by ID.

        Args:
            id: The ID of the entity to retrieve

        Returns:
            The entity if found, None otherwise
        """
        return self.get_by_id(id)

    def get_all_entities(self) -> List[LineType]:
        """
        Get all entities.

        Returns:
            A list of all entities
        """
        return self.get_all()
