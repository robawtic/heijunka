from typing import Optional, List

from domain.entities.group import Group
from domain.repositories.interfaces.group_repository import GroupRepositoryInterface


class MockGroupRepository(GroupRepositoryInterface):
    """
    Mock implementation of the group repository for testing.
    """
    
    def __init__(self):
        self.groups = {}  # Dictionary of groups by ID
        
    def get_by_id(self, entity_id: int) -> Optional[Group]:
        """Retrieve a group by ID."""
        return self.groups.get(entity_id)
    
    def list_all(self) -> List[Group]:
        """Retrieve all groups."""
        return list(self.groups.values())
    
    def add(self, entity: Group) -> Group:
        """Add a new group."""
        self.groups[entity.id] = entity
        return entity
    
    def update(self, entity: Group) -> Group:
        """Update an existing group."""
        self.groups[entity.id] = entity
        return entity
    
    def delete(self, entity_id: int) -> bool:
        """Delete a group by ID."""
        if entity_id in self.groups:
            del self.groups[entity_id]
            return True
        return False
    
    def get_by_name(self, group_name: str) -> Optional[Group]:
        """Retrieve a group by its name."""
        for group in self.groups.values():
            if group.name == group_name:
                return group
        return None