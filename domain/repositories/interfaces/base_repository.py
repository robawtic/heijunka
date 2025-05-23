from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):
    """
    Base repository interface that defines common operations for all repositories.
    """
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[T]:
        """
        Retrieve an entity by its ID.
        
        Args:
            entity_id: The ID of the entity to retrieve.
            
        Returns:
            The entity if found, None otherwise.
        """
        pass
    
    @abstractmethod
    def list_all(self) -> List[T]:
        """
        Retrieve all entities.
        
        Returns:
            A list of all entities.
        """
        pass
    
    @abstractmethod
    def add(self, entity: T) -> T:
        """
        Add a new entity.
        
        Args:
            entity: The entity to add.
            
        Returns:
            The added entity.
        """
        pass
    
    @abstractmethod
    def update(self, entity: T) -> T:
        """
        Update an existing entity.
        
        Args:
            entity: The entity to update.
            
        Returns:
            The updated entity.
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete an entity by its ID.
        
        Args:
            entity_id: The ID of the entity to delete.
            
        Returns:
            True if the entity was deleted, False otherwise.
        """
        pass