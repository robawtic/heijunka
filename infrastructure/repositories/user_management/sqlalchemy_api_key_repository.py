from typing import Optional, List, Generator
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import json

from domain.contexts.user_management.entities.api_key import ApiKey
from domain.models.ApiKeyModel import ApiKeyModel
from domain.contexts.user_management.repositories.interfaces.api_key_repository import ApiKeyRepositoryInterface
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import redact_log_message, sanitize_exception, log_audit_event
from utilities.logging_factory import get_logger

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
        self.logger = get_logger("heijunka.repositories.api_key")
        self.rate_limited_logger = get_logger("heijunka.repositories.api_key", rate_limit=True)

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.

        Yields:
            The SQLAlchemy session.
        """
        try:
            yield self._session
            self._session.commit()
        except SQLAlchemyError as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Database operation failed: {error_msg}",
                extra={
                    "event_type": "database_error",
                    "error_type": type(e).__name__,
                    "repository": "api_key"
                }
            )
            raise RepositoryError(f"Database error: {error_msg}")
        except Exception as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in API key repository: {error_msg}",
                extra={
                    "event_type": "unexpected_error",
                    "error_type": type(e).__name__,
                    "repository": "api_key"
                }
            )
            raise RepositoryError(f"Repository error: {error_msg}")

    def get_by_key_id(self, key_id: str) -> Optional[ApiKey]:
        """
        Retrieve an API key by its key ID.

        Args:
            key_id: The key ID of the API key to retrieve.

        Returns:
            The API key if found, None otherwise.
        """
        try:
            # Log with redaction since key_id might be sensitive
            result = redact_log_message(
                f"Retrieving API key by key ID: {key_id}",
                custom_data={"key_id": [key_id]}
            )
            self.logger.info(
                result.message,
                extra={
                    "event_type": "api_key_lookup",
                    "lookup_type": "key_id",
                    "redacted": True,
                    "redacted_fields": result.redacted_fields
                }
            )

            model = self._session.query(ApiKeyModel).filter(ApiKeyModel.key_id == key_id).first()
            if model is None:
                self.logger.info(
                    "No API key found with the provided key ID",
                    extra={
                        "event_type": "api_key_lookup_failed",
                        "lookup_type": "key_id"
                    }
                )
                return None

            self.logger.info(
                f"Found API key with ID: {model.id}",
                extra={
                    "event_type": "api_key_lookup_success",
                    "lookup_type": "key_id",
                    "api_key_id": model.id,
                    "user_id": model.user_id
                }
            )
            return self._to_domain(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving API key by key ID: {error_msg}",
                extra={
                    "event_type": "api_key_lookup_error",
                    "lookup_type": "key_id",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving API key by key ID: {error_msg}")

    def get_by_key_value(self, key_value: str) -> Optional[ApiKey]:
        """
        Retrieve an API key by its key value.

        Args:
            key_value: The key value of the API key to retrieve.

        Returns:
            The API key if found, None otherwise.
        """
        try:
            # Log with complete redaction since key_value is highly sensitive
            self.logger.info(
                "Retrieving API key by key value (redacted)",
                extra={
                    "event_type": "api_key_lookup",
                    "lookup_type": "key_value",
                    "redacted": True
                }
            )

            model = self._session.query(ApiKeyModel).filter(ApiKeyModel.key_value == key_value).first()
            if model is None:
                self.logger.info(
                    "No API key found with the provided key value",
                    extra={
                        "event_type": "api_key_lookup_failed",
                        "lookup_type": "key_value"
                    }
                )
                return None

            self.logger.info(
                f"Found API key with ID: {model.id}",
                extra={
                    "event_type": "api_key_lookup_success",
                    "lookup_type": "key_value",
                    "api_key_id": model.id,
                    "user_id": model.user_id
                }
            )
            return self._to_domain(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving API key by key value: {error_msg}",
                extra={
                    "event_type": "api_key_lookup_error",
                    "lookup_type": "key_value",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving API key by key value: {error_msg}")

    def get_active_keys_for_user(self, user_id: int) -> List[ApiKey]:
        """
        Retrieve all active API keys for a user.

        Args:
            user_id: The ID of the user.

        Returns:
            A list of active API keys for the user.
        """
        try:
            self.logger.info(
                "Retrieving active API keys for user",
                extra={
                    "event_type": "api_keys_lookup",
                    "user_id": user_id
                }
            )

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

            key_count = len(models)
            self.logger.info(
                f"Found {key_count} active API keys for user",
                extra={
                    "event_type": "api_keys_lookup_success",
                    "user_id": user_id,
                    "key_count": key_count
                }
            )

            return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving active API keys for user: {error_msg}",
                extra={
                    "event_type": "api_keys_lookup_error",
                    "user_id": user_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving active API keys for user: {error_msg}")

    def deactivate_key(self, key_id: str, source_ip: str = None, user_agent: str = None) -> bool:
        """
        Deactivate an API key.

        Args:
            key_id: The key ID of the API key to deactivate.
            source_ip: Optional IP address of the client making the request
            user_agent: Optional user agent of the client making the request

        Returns:
            True if the key was deactivated, False otherwise.
        """
        try:
            # Log with redaction since key_id might be sensitive
            result = redact_log_message(
                f"Deactivating API key with ID: {key_id}",
                custom_data={"key_id": [key_id]}
            )
            self.logger.info(
                result.message,
                extra={
                    "event_type": "api_key_deactivation_request",
                    "redacted": True,
                    "redacted_fields": result.redacted_fields
                }
            )

            with self.session_scope() as session:
                model = session.query(ApiKeyModel).filter(ApiKeyModel.key_id == key_id).first()
                if model is None:
                    self.logger.warning(
                        "Failed to deactivate API key - key not found",
                        extra={
                            "event_type": "api_key_deactivation_failed",
                            "reason": "key_not_found"
                        }
                    )
                    return False

                # Only deactivate if not already inactive
                if not model.is_active:
                    self.logger.info(
                        "API key is already inactive",
                        extra={
                            "event_type": "api_key_deactivation_skipped",
                            "api_key_id": model.id,
                            "user_id": model.user_id,
                            "reason": "already_inactive"
                        }
                    )
                    return True

                model.is_active = False
                model.updated_at = datetime.utcnow()

                # Prepare audit data with optional client information
                audit_data = {"key_id": key_id, "user_id": model.user_id}
                if source_ip:
                    audit_data["source_ip"] = source_ip
                if user_agent:
                    audit_data["user_agent"] = user_agent

                # Log audit event for this security-relevant operation
                log_audit_event(
                    event_type="api_key_deactivation",
                    message="API key deactivated",
                    user_id=str(model.user_id),
                    custom_data=audit_data
                )

                self.logger.info(
                    "Successfully deactivated API key",
                    extra={
                        "event_type": "api_key_deactivation_success",
                        "api_key_id": model.id,
                        "user_id": model.user_id
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error deactivating API key: {error_msg}",
                extra={
                    "event_type": "api_key_deactivation_error",
                    "error_type": type(e).__name__
                }
            )
            return False

    def deactivate_all_keys_for_user(self, user_id: int, source_ip: str = None, user_agent: str = None) -> int:
        """
        Deactivate all API keys for a user.

        Args:
            user_id: The ID of the user.
            source_ip: Optional IP address of the client making the request
            user_agent: Optional user agent of the client making the request

        Returns:
            The number of keys deactivated.
        """
        try:
            self.logger.info(
                "Deactivating all API keys for user",
                extra={
                    "event_type": "api_keys_deactivation_request",
                    "user_id": user_id
                }
            )

            with self.session_scope() as session:
                # First, get the count of active keys for logging
                active_keys_count = session.query(ApiKeyModel).filter(
                    and_(
                        ApiKeyModel.user_id == user_id,
                        ApiKeyModel.is_active == True
                    )
                ).count()

                if active_keys_count == 0:
                    self.logger.info(
                        "No active API keys found for user",
                        extra={
                            "event_type": "api_keys_deactivation_skipped",
                            "user_id": user_id,
                            "reason": "no_active_keys"
                        }
                    )
                    return 0

                # Perform the update
                result = session.query(ApiKeyModel).filter(
                    and_(
                        ApiKeyModel.user_id == user_id,
                        ApiKeyModel.is_active == True
                    )
                ).update(
                    {"is_active": False, "updated_at": datetime.utcnow()},
                    synchronize_session=False
                )

                # Prepare audit data with optional client information
                audit_data = {"user_id": user_id, "keys_deactivated": result}
                if source_ip:
                    audit_data["source_ip"] = source_ip
                if user_agent:
                    audit_data["user_agent"] = user_agent

                # Log audit event for this security-relevant operation
                log_audit_event(
                    event_type="api_keys_bulk_deactivation",
                    message=f"All API keys deactivated for user",
                    user_id=str(user_id),
                    custom_data=audit_data
                )

                self.logger.info(
                    f"Successfully deactivated {result} API keys for user",
                    extra={
                        "event_type": "api_keys_deactivation_success",
                        "user_id": user_id,
                        "keys_deactivated": result
                    }
                )
                return result
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error deactivating all API keys for user: {error_msg}",
                extra={
                    "event_type": "api_keys_deactivation_error",
                    "user_id": user_id,
                    "error_type": type(e).__name__
                }
            )
            return 0

    def key_exists(self, key_value: str) -> bool:
        """
        Check if a key value already exists.

        Args:
            key_value: The key value to check.

        Returns:
            True if the key value exists, False otherwise.
        """
        try:
            # Use rate-limited logger for this high-frequency operation
            # Don't log the key_value at all as it's highly sensitive
            self.rate_limited_logger.info(
                "Checking if API key exists (redacted)",
                event_type="api_key_check",
                identifier=key_value,  # This will be hashed internally
                extra={
                    "redacted": True
                }
            )

            exists = self._session.query(ApiKeyModel).filter(ApiKeyModel.key_value == key_value).first() is not None

            self.rate_limited_logger.info(
                f"API key exists: {exists}",
                event_type="api_key_check_result",
                identifier=key_value,  # This will be hashed internally
                extra={
                    "exists": exists
                }
            )
            return exists
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error checking if API key exists: {error_msg}",
                extra={
                    "event_type": "api_key_check_error",
                    "error_type": type(e).__name__
                }
            )
            # Return False on error to be safe
            return False

    def _to_domain(self, model: ApiKeyModel) -> ApiKey:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            # Log with minimal information to avoid exposing sensitive data
            self.logger.debug(
                "Converting API key model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "api_key_id": model.id,
                    "user_id": model.user_id
                }
            )

            # Parse JSON fields
            try:
                scopes = json.loads(model.scopes) if model.scopes else []
            except json.JSONDecodeError as e:
                self.logger.warning(
                    f"Error parsing scopes JSON: {e}",
                    extra={
                        "event_type": "json_parse_error",
                        "field": "scopes",
                        "api_key_id": model.id
                    }
                )
                scopes = []

            try:
                allowed_ips = json.loads(model.allowed_ips) if model.allowed_ips else []
            except json.JSONDecodeError as e:
                self.logger.warning(
                    f"Error parsing allowed_ips JSON: {e}",
                    extra={
                        "event_type": "json_parse_error",
                        "field": "allowed_ips",
                        "api_key_id": model.id
                    }
                )
                allowed_ips = []

            try:
                allowed_user_agents = json.loads(model.allowed_user_agents) if model.allowed_user_agents else []
            except json.JSONDecodeError as e:
                self.logger.warning(
                    f"Error parsing allowed_user_agents JSON: {e}",
                    extra={
                        "event_type": "json_parse_error",
                        "field": "allowed_user_agents",
                        "api_key_id": model.id
                    }
                )
                allowed_user_agents = []

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
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting API key model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "api_key_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: ApiKey) -> ApiKeyModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            # Log with minimal information to avoid exposing sensitive data
            api_key_id = entity.id if entity.id is not None else "new key"
            self.logger.debug(
                "Converting API key domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "api_key_id": api_key_id,
                    "user_id": entity.user_id
                }
            )

            # Convert lists to JSON strings
            try:
                scopes_json = json.dumps(entity.scopes) if entity.scopes else json.dumps([])
            except Exception as e:
                self.logger.warning(
                    f"Error converting scopes to JSON: {sanitize_exception(e)}",
                    extra={
                        "event_type": "json_conversion_error",
                        "field": "scopes",
                        "api_key_id": api_key_id
                    }
                )
                scopes_json = json.dumps([])

            try:
                allowed_ips_json = json.dumps(entity.allowed_ips) if entity.allowed_ips else json.dumps([])
            except Exception as e:
                self.logger.warning(
                    f"Error converting allowed_ips to JSON: {sanitize_exception(e)}",
                    extra={
                        "event_type": "json_conversion_error",
                        "field": "allowed_ips",
                        "api_key_id": api_key_id
                    }
                )
                allowed_ips_json = json.dumps([])

            try:
                allowed_user_agents_json = json.dumps(entity.allowed_user_agents) if entity.allowed_user_agents else json.dumps([])
            except Exception as e:
                self.logger.warning(
                    f"Error converting allowed_user_agents to JSON: {sanitize_exception(e)}",
                    extra={
                        "event_type": "json_conversion_error",
                        "field": "allowed_user_agents",
                        "api_key_id": api_key_id
                    }
                )
                allowed_user_agents_json = json.dumps([])

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
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting API key domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "api_key_id": entity.id if entity and hasattr(entity, 'id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: ApiKeyModel, entity: ApiKey) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            # Log with minimal information to avoid exposing sensitive data
            self.logger.debug(
                "Updating API key model from domain entity",
                extra={
                    "event_type": "api_key_model_update",
                    "api_key_id": model.id,
                    "user_id": model.user_id
                }
            )

            # Check if active status is changing
            if model.is_active != entity.is_active:
                new_status = "active" if entity.is_active else "inactive"
                self.logger.info(
                    "Changing API key status",
                    extra={
                        "event_type": "api_key_status_change",
                        "api_key_id": model.id,
                        "user_id": model.user_id,
                        "new_status": new_status
                    }
                )

            # Check if expiration is changing
            if model.expires_at != entity.expires_at:
                self.logger.info(
                    "Changing API key expiration",
                    extra={
                        "event_type": "api_key_expiration_change",
                        "api_key_id": model.id,
                        "user_id": model.user_id,
                        "new_expiration": entity.expires_at.isoformat() if entity.expires_at else None
                    }
                )

            # Convert lists to JSON strings
            try:
                scopes_json = json.dumps(entity.scopes) if entity.scopes else json.dumps([])
            except Exception as e:
                self.logger.warning(
                    f"Error converting scopes to JSON: {sanitize_exception(e)}",
                    extra={
                        "event_type": "json_conversion_error",
                        "field": "scopes",
                        "api_key_id": model.id
                    }
                )
                scopes_json = json.dumps([])

            try:
                allowed_ips_json = json.dumps(entity.allowed_ips) if entity.allowed_ips else json.dumps([])
            except Exception as e:
                self.logger.warning(
                    f"Error converting allowed_ips to JSON: {sanitize_exception(e)}",
                    extra={
                        "event_type": "json_conversion_error",
                        "field": "allowed_ips",
                        "api_key_id": model.id
                    }
                )
                allowed_ips_json = json.dumps([])

            try:
                allowed_user_agents_json = json.dumps(entity.allowed_user_agents) if entity.allowed_user_agents else json.dumps([])
            except Exception as e:
                self.logger.warning(
                    f"Error converting allowed_user_agents to JSON: {sanitize_exception(e)}",
                    extra={
                        "event_type": "json_conversion_error",
                        "field": "allowed_user_agents",
                        "api_key_id": model.id
                    }
                )
                allowed_user_agents_json = json.dumps([])

            # Update the model
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

            self.logger.debug(
                "Successfully updated API key model",
                extra={
                    "event_type": "api_key_model_update_success",
                    "api_key_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating API key model: {error_msg}",
                extra={
                    "event_type": "api_key_model_update_error",
                    "api_key_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise
