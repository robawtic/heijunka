from abc import abstractmethod
from typing import Optional, List
from datetime import datetime

from domain.contexts.user_management.entities.api_key import ApiKey
from domain.repositories.interfaces.base_repository import BaseRepository

class ApiKeyRepositoryInterface(BaseRepository[ApiKey]):
    """
    Interface for API key repository operations.
    """
    
    @abstractmethod
    def get_by_key_id(self, key_id: str) -> Optional[ApiKey]:
        """
        Retrieve an API key by its key ID.
        
        Args:
            key_id: The key ID of the API key to retrieve.
            
        Returns:
            The API key if found, None otherwise.
        """
        pass
    
    @abstractmethod
    def get_by_key_value(self, key_value: str) -> Optional[ApiKey]:
        """
        Retrieve an API key by its key value.
        
        Args:
            key_value: The key value of the API key to retrieve.
            
        Returns:
            The API key if found, None otherwise.
        """
        pass
    
    @abstractmethod
    def get_active_keys_for_user(self, user_id: int) -> List[ApiKey]:
        """
        Retrieve all active API keys for a user.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            A list of active API keys for the user.
        """
        pass
    
    @abstractmethod
    def deactivate_key(self, key_id: str) -> bool:
        """
        Deactivate an API key.
        
        Args:
            key_id: The key ID of the API key to deactivate.
            
        Returns:
            True if the key was deactivated, False otherwise.
        """
        pass
    
    @abstractmethod
    def deactivate_all_keys_for_user(self, user_id: int) -> int:
        """
        Deactivate all API keys for a user.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            The number of keys deactivated.
        """
        pass
    
    @abstractmethod
    def key_exists(self, key_value: str) -> bool:
        """
        Check if a key value already exists.
        
        Args:
            key_value: The key value to check.
            
        Returns:
            True if the key value exists, False otherwise.
        """
        pass