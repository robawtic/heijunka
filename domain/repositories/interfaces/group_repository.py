from abc import abstractmethod
from typing import Optional

from domain.contexts.employee_management.entities.group import Group
from domain.repositories.interfaces.base_repository import BaseRepository


class GroupRepositoryInterface(BaseRepository[Group]):
    """
    Interface for group repository operations.
    """

    @abstractmethod
    def get_by_name(self, group_name: str) -> Optional[Group]:
        """
        Retrieve a group by its name.

        Args:
            group_name: The name of the group.

        Returns:
            The group if found, None otherwise.
        """
        pass
