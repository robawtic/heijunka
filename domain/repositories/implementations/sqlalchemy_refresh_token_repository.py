from typing import Optional, List
from datetime import datetime
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from domain.entities.refresh_token import RefreshToken
from domain.models.RefreshTokenModel import RefreshTokenModel
from domain.repositories.interfaces.refresh_token_repository import RefreshTokenRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository


class SqlAlchemyRefreshTokenRepository(BaseSqlAlchemyRepository[RefreshToken, RefreshTokenModel], RefreshTokenRepositoryInterface):
    """
    SQLAlchemy implementation of the RefreshTokenRepository interface.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.
        
        Args:
            session: The SQLAlchemy session to use for database operations.
        """
        super().__init__(session, RefreshTokenModel, RefreshToken)
    
    def get_by_token_id(self, token_id: str) -> Optional[RefreshToken]:
        """
        Retrieve a refresh token by its token ID.
        
        Args:
            token_id: The token ID of the refresh token to retrieve.
            
        Returns:
            The refresh token if found, None otherwise.
        """
        model = self._session.query(RefreshTokenModel).filter(RefreshTokenModel.token_id == token_id).first()
        if model is None:
            return None
        return self._to_domain(model)
    
    def get_active_tokens_for_user(self, user_id: int) -> List[RefreshToken]:
        """
        Retrieve all active (non-revoked, non-expired) refresh tokens for a user.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            A list of active refresh tokens for the user.
        """
        now = datetime.utcnow()
        models = self._session.query(RefreshTokenModel).filter(
            and_(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.is_revoked == False,
                RefreshTokenModel.expires_at > now
            )
        ).all()
        return [self._to_domain(model) for model in models]
    
    def revoke_token(self, token_id: str) -> bool:
        """
        Revoke a refresh token.
        
        Args:
            token_id: The token ID of the refresh token to revoke.
            
        Returns:
            True if the token was revoked, False otherwise.
        """
        model = self._session.query(RefreshTokenModel).filter(RefreshTokenModel.token_id == token_id).first()
        if model is None:
            return False
        
        model.is_revoked = True
        model.updated_at = datetime.utcnow()
        self._session.commit()
        return True
    
    def revoke_all_tokens_for_user(self, user_id: int) -> int:
        """
        Revoke all refresh tokens for a user.
        
        Args:
            user_id: The ID of the user.
            
        Returns:
            The number of tokens revoked.
        """
        result = self._session.query(RefreshTokenModel).filter(
            and_(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.is_revoked == False
            )
        ).update(
            {"is_revoked": True, "updated_at": datetime.utcnow()},
            synchronize_session=False
        )
        self._session.commit()
        return result
    
    def delete_expired_tokens(self, before_date: Optional[datetime] = None) -> int:
        """
        Delete expired refresh tokens.
        
        Args:
            before_date: Optional date to delete tokens that expired before this date.
                         If not provided, deletes all expired tokens.
            
        Returns:
            The number of tokens deleted.
        """
        query = self._session.query(RefreshTokenModel).filter(
            or_(
                RefreshTokenModel.expires_at < (before_date or datetime.utcnow()),
                RefreshTokenModel.is_revoked == True
            )
        )
        result = query.delete(synchronize_session=False)
        self._session.commit()
        return result
    
    def token_exists(self, token_id: str) -> bool:
        """
        Check if a token ID already exists.
        
        Args:
            token_id: The token ID to check.
            
        Returns:
            True if the token ID exists, False otherwise.
        """
        return self._session.query(RefreshTokenModel).filter(RefreshTokenModel.token_id == token_id).first() is not None
    
    def _to_domain(self, model: RefreshTokenModel) -> RefreshToken:
        """
        Convert a SQLAlchemy model to a domain entity.
        
        Args:
            model: The SQLAlchemy model to convert.
            
        Returns:
            The domain entity.
        """
        return RefreshToken(
            id=model.id,
            token_id=model.token_id,
            user_id=model.user_id,
            expires_at=model.expires_at,
            is_revoked=model.is_revoked,
            device_info=model.device_info,
            ip_address=model.ip_address,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    def _to_model(self, entity: RefreshToken) -> RefreshTokenModel:
        """
        Convert a domain entity to a SQLAlchemy model.
        
        Args:
            entity: The domain entity to convert.
            
        Returns:
            The SQLAlchemy model.
        """
        model = RefreshTokenModel(
            token_id=entity.token_id,
            user_id=entity.user_id,
            expires_at=entity.expires_at,
            is_revoked=entity.is_revoked,
            device_info=entity.device_info,
            ip_address=entity.ip_address
        )
        if entity.id is not None:
            model.id = entity.id
        if entity.created_at is not None:
            model.created_at = entity.created_at
        if entity.updated_at is not None:
            model.updated_at = entity.updated_at
        return model
    
    def _update_model(self, model: RefreshTokenModel, entity: RefreshToken) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.
        
        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        model.token_id = entity.token_id
        model.user_id = entity.user_id
        model.expires_at = entity.expires_at
        model.is_revoked = entity.is_revoked
        model.device_info = entity.device_info
        model.ip_address = entity.ip_address
        model.updated_at = datetime.utcnow()