from typing import Optional, List
from datetime import datetime
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
import json

from domain.entities.api_key import ApiKey
from domain.models.ApiKeyModel import ApiKeyModel
from domain.repositories.interfaces.api_key_repository import ApiKeyRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository

class SqlAlchemyApiKeyRepository(BaseSqlAlchemyRepository[ApiKey, ApiKeyModel], ApiKeyRepositoryInterface):
    """
    SQLAlchemy implementation of the ApiKeyRepository interface.
    """

    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session: The SQLAlchemy session to use for database operations.
        """
        super().__init__(session, ApiKeyModel, ApiKey)

    def get_by_key_id(self, key_id: str) -> Optional[ApiKey]:
        """
        Retrieve an API key by its key ID.

        Args:
            key_id: The key ID of the API key to retrieve.

        Returns:
            The API key if found, None otherwise.
        """
        model = self._session.query(ApiKeyModel).filter(ApiKeyModel.key_id == key_id).first()
        if model is None:
            return None
        return self._to_domain(model)

    def get_by_key_value(self, key_value: str) -> Optional[ApiKey]:
        """
        Retrieve an API key by its key value.

        Args:
            key_value: The key value of the API key to retrieve.

        Returns:
            The API key if found, None otherwise.
        """
        model = self._session.query(ApiKeyModel).filter(ApiKeyModel.key_value == key_value).first()
        if model is None:
            return None
        return self._to_domain(model)

    def get_active_keys_for_user(self, user_id: int) -> List[ApiKey]:
        """
        Retrieve all active API keys for a user.

        Args:
            user_id: The ID of the user.

        Returns:
            A list of active API keys for the user.
        """
        now = datetime.utcnow()
        models = self._session.query(ApiKeyModel).filter(
            and_(
                ApiKeyModel.user_id == user_id,
                ApiKeyModel.is_active == True,
                or_(
                    ApiKeyModel.expires_at.is_(None),
                    ApiKeyModel.expires_at > now
                )
            )
        ).all()
        return [self._to_domain(model) for model in models]

    def deactivate_key(self, key_id: str) -> bool:
        """
        Deactivate an API key.

        Args:
            key_id: The key ID of the API key to deactivate.

        Returns:
            True if the key was deactivated, False otherwise.
        """
        model = self._session.query(ApiKeyModel).filter(ApiKeyModel.key_id == key_id).first()
        if model is None:
            return False

        model.is_active = False
        model.updated_at = datetime.utcnow()
        self._session.commit()
        return True

    def deactivate_all_keys_for_user(self, user_id: int) -> int:
        """
        Deactivate all API keys for a user.

        Args:
            user_id: The ID of the user.

        Returns:
            The number of keys deactivated.
        """
        result = self._session.query(ApiKeyModel).filter(
            and_(
                ApiKeyModel.user_id == user_id,
                ApiKeyModel.is_active == True
            )
        ).update(
            {"is_active": False, "updated_at": datetime.utcnow()},
            synchronize_session=False
        )
        self._session.commit()
        return result

    def key_exists(self, key_value: str) -> bool:
        """
        Check if a key value already exists.

        Args:
            key_value: The key value to check.

        Returns:
            True if the key value exists, False otherwise.
        """
        return self._session.query(ApiKeyModel).filter(ApiKeyModel.key_value == key_value).first() is not None

    def _to_domain(self, model: ApiKeyModel) -> ApiKey:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        # Parse JSON fields
        scopes = json.loads(model.scopes) if model.scopes else []
        allowed_ips = json.loads(model.allowed_ips) if model.allowed_ips else []
        allowed_user_agents = json.loads(model.allowed_user_agents) if model.allowed_user_agents else []

        return ApiKey(
            id=model.id,
            key_id=model.key_id,
            key_value=model.key_value,
            user_id=model.user_id,
            name=model.name,
            expires_at=model.expires_at,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_used_at=model.last_used_at,
            scopes=scopes,
            allowed_ips=allowed_ips,
            allowed_user_agents=allowed_user_agents
        )

    def _to_model(self, entity: ApiKey) -> ApiKeyModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        # Convert lists to JSON strings
        scopes_json = json.dumps(entity.scopes) if entity.scopes else json.dumps([])
        allowed_ips_json = json.dumps(entity.allowed_ips) if entity.allowed_ips else json.dumps([])
        allowed_user_agents_json = json.dumps(entity.allowed_user_agents) if entity.allowed_user_agents else json.dumps([])

        model = ApiKeyModel(
            key_id=entity.key_id,
            key_value=entity.key_value,
            user_id=entity.user_id,
            name=entity.name,
            expires_at=entity.expires_at,
            is_active=entity.is_active,
            last_used_at=entity.last_used_at,
            scopes=scopes_json,
            allowed_ips=allowed_ips_json,
            allowed_user_agents=allowed_user_agents_json
        )
        if entity.id is not None:
            model.id = entity.id
        if entity.created_at is not None:
            model.created_at = entity.created_at
        if entity.updated_at is not None:
            model.updated_at = entity.updated_at
        return model

    def _update_model(self, model: ApiKeyModel, entity: ApiKey) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        # Convert lists to JSON strings
        scopes_json = json.dumps(entity.scopes) if entity.scopes else json.dumps([])
        allowed_ips_json = json.dumps(entity.allowed_ips) if entity.allowed_ips else json.dumps([])
        allowed_user_agents_json = json.dumps(entity.allowed_user_agents) if entity.allowed_user_agents else json.dumps([])

        model.key_id = entity.key_id
        model.key_value = entity.key_value
        model.user_id = entity.user_id
        model.name = entity.name
        model.expires_at = entity.expires_at
        model.is_active = entity.is_active
        model.last_used_at = entity.last_used_at
        model.scopes = scopes_json
        model.allowed_ips = allowed_ips_json
        model.allowed_user_agents = allowed_user_agents_json
        model.updated_at = datetime.utcnow()
