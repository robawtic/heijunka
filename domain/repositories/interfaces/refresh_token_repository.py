from abc import abstractmethod
from typing import Optional, List
from datetime import datetime

from domain.entities.refresh_token import RefreshToken
from domain.repositories.interfaces.base_repository import BaseRepository


class RefreshTokenRepositoryInterface(BaseRepository[RefreshToken]):
    """
    Interface for refresh token repository operations.
    """
    
    @abstractmethod
    def get_by_token_id(self, token_id: str) -> Optional[RefreshToken]:
        """
        Retrieve a refresh token by its token ID.
        
        Args:
            token_id: The token ID of the refresh token to retrieve.
            
        Returns:
            The refresh token if found, None otherwise.
        """
        pass
    
    @abstractmethod
    def get_active_tokens_for_user(self, user_id: int) -> List[RefreshToken]:
        """
        Retrieve all active (non-revoked, non-expired) refresh tokens for a user.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            A list of active refresh tokens for the user.
        """
        pass
    
    @abstractmethod
    def revoke_token(self, token_id: str) -> bool:
        """
        Revoke a refresh token.
        
        Args:
            token_id: The token ID of the refresh token to revoke.
            
        Returns:
            True if the token was revoked, False otherwise.
        """
        pass
    
    @abstractmethod
    def revoke_all_tokens_for_user(self, user_id: int) -> int:
        """
        Revoke all refresh tokens for a user.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            The number of tokens revoked.
        """
        pass
    
    @abstractmethod
    def delete_expired_tokens(self, before_date: Optional[datetime] = None) -> int:
        """
        Delete expired refresh tokens.
        
        Args:
            before_date: Optional date to delete tokens that expired before this date.
                         If not provided, deletes all expired tokens.
            
        Returns:
            The number of tokens deleted.
        """
        pass
    
    @abstractmethod
    def token_exists(self, token_id: str) -> bool:
        """
        Check if a token ID already exists.
        
        Args:
            token_id: The token ID to check.
            
        Returns:
            True if the token ID exists, False otherwise.
        """
        pass