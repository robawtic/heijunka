from typing import Optional, List, Generator
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from domain.entities.refresh_token import RefreshToken
from domain.models.RefreshTokenModel import RefreshTokenModel
from domain.repositories.interfaces.refresh_token_repository import RefreshTokenRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import redact_log_message, sanitize_exception, log_audit_event
from utilities.logging_factory import get_logger


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
        self.logger = get_logger("heijunka.repositories.refresh_token")
        self.rate_limited_logger = get_logger("heijunka.repositories.refresh_token", rate_limit=True)

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
                    "repository": "refresh_token"
                }
            )
            raise RepositoryError(f"Database error: {error_msg}")
        except Exception as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in refresh token repository: {error_msg}",
                extra={
                    "event_type": "unexpected_error",
                    "error_type": type(e).__name__,
                    "repository": "refresh_token"
                }
            )
            raise RepositoryError(f"Repository error: {error_msg}")

    def get_by_token_id(self, token_id: str) -> Optional[RefreshToken]:
        """
        Retrieve a refresh token by its token ID.

        Args:
            token_id: The token ID of the refresh token to retrieve.

        Returns:
            The refresh token if found, None otherwise.
        """
        try:
            # Log with redaction since token_id might be sensitive
            result = redact_log_message(
                f"Retrieving refresh token by token ID: {token_id}",
                custom_data={"token_id": [token_id]}
            )
            self.logger.info(
                result.message,
                extra={
                    "event_type": "refresh_token_lookup",
                    "lookup_type": "token_id",
                    "redacted": True,
                    "redacted_fields": result.redacted_fields
                }
            )

            model = self._session.query(RefreshTokenModel).filter(RefreshTokenModel.token_id == token_id).first()
            if model is None:
                self.logger.info(
                    "No refresh token found with the provided token ID",
                    extra={
                        "event_type": "refresh_token_lookup_failed",
                        "lookup_type": "token_id"
                    }
                )
                return None

            self.logger.info(
                f"Found refresh token with ID: {model.id}",
                extra={
                    "event_type": "refresh_token_lookup_success",
                    "lookup_type": "token_id",
                    "refresh_token_id": model.id,
                    "user_id": model.user_id
                }
            )
            return self._to_domain(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving refresh token by token ID: {error_msg}",
                extra={
                    "event_type": "refresh_token_lookup_error",
                    "lookup_type": "token_id",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving refresh token by token ID: {error_msg}")

    def get_active_tokens_for_user(self, user_id: int) -> List[RefreshToken]:
        """
        Retrieve all active (non-revoked, non-expired) refresh tokens for a user.

        Args:
            user_id: The ID of the user.

        Returns:
            A list of active refresh tokens for the user.
        """
        try:
            self.logger.info(
                "Retrieving active refresh tokens for user",
                extra={
                    "event_type": "refresh_tokens_lookup",
                    "user_id": user_id
                }
            )

            now = datetime.utcnow()
            models = self._session.query(RefreshTokenModel).filter(
                and_(
                    RefreshTokenModel.user_id == user_id,
                    RefreshTokenModel.is_revoked == False,
                    RefreshTokenModel.expires_at > now
                )
            ).all()

            token_count = len(models)
            self.logger.info(
                f"Found {token_count} active refresh tokens for user",
                extra={
                    "event_type": "refresh_tokens_lookup_success",
                    "user_id": user_id,
                    "token_count": token_count
                }
            )

            return [self._to_domain(model) for model in models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving active refresh tokens for user: {error_msg}",
                extra={
                    "event_type": "refresh_tokens_lookup_error",
                    "user_id": user_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving active refresh tokens for user: {error_msg}")

    def revoke_token(self, token_id: str, source_ip: str = None, user_agent: str = None) -> bool:
        """
        Revoke a refresh token.

        Args:
            token_id: The token ID of the refresh token to revoke.
            source_ip: Optional IP address of the client making the request
            user_agent: Optional user agent of the client making the request

        Returns:
            True if the token was revoked, False otherwise.
        """
        try:
            # Log with redaction since token_id might be sensitive
            result = redact_log_message(
                f"Revoking refresh token with ID: {token_id}",
                custom_data={"token_id": [token_id]}
            )
            self.logger.info(
                result.message,
                extra={
                    "event_type": "refresh_token_revocation_request",
                    "redacted": True,
                    "redacted_fields": result.redacted_fields
                }
            )

            with self.session_scope() as session:
                model = session.query(RefreshTokenModel).filter(RefreshTokenModel.token_id == token_id).first()
                if model is None:
                    self.logger.warning(
                        "Failed to revoke refresh token - token not found",
                        extra={
                            "event_type": "refresh_token_revocation_failed",
                            "reason": "token_not_found"
                        }
                    )
                    return False

                # Only revoke if not already revoked
                if model.is_revoked:
                    self.logger.info(
                        "Refresh token is already revoked",
                        extra={
                            "event_type": "refresh_token_revocation_skipped",
                            "refresh_token_id": model.id,
                            "user_id": model.user_id,
                            "reason": "already_revoked"
                        }
                    )
                    return True

                model.is_revoked = True
                model.updated_at = datetime.utcnow()

                # Prepare audit data with optional client information
                audit_data = {"token_id": token_id, "user_id": model.user_id}
                if source_ip:
                    audit_data["source_ip"] = source_ip
                if user_agent:
                    audit_data["user_agent"] = user_agent

                # Log audit event for this security-relevant operation
                log_audit_event(
                    event_type="refresh_token_revocation",
                    message="Refresh token revoked",
                    user_id=str(model.user_id),
                    custom_data=audit_data
                )

                self.logger.info(
                    "Successfully revoked refresh token",
                    extra={
                        "event_type": "refresh_token_revocation_success",
                        "refresh_token_id": model.id,
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
                f"Error revoking refresh token: {error_msg}",
                extra={
                    "event_type": "refresh_token_revocation_error",
                    "error_type": type(e).__name__
                }
            )
            return False

    def revoke_all_tokens_for_user(self, user_id: int, source_ip: str = None, user_agent: str = None) -> int:
        """
        Revoke all refresh tokens for a user.

        Args:
            user_id: The ID of the user.
            source_ip: Optional IP address of the client making the request
            user_agent: Optional user agent of the client making the request

        Returns:
            The number of tokens revoked.
        """
        try:
            self.logger.info(
                "Revoking all refresh tokens for user",
                extra={
                    "event_type": "refresh_tokens_revocation_request",
                    "user_id": user_id
                }
            )

            with self.session_scope() as session:
                # First, get the count of active tokens for logging
                active_tokens_count = session.query(RefreshTokenModel).filter(
                    and_(
                        RefreshTokenModel.user_id == user_id,
                        RefreshTokenModel.is_revoked == False
                    )
                ).count()

                if active_tokens_count == 0:
                    self.logger.info(
                        "No active refresh tokens found for user",
                        extra={
                            "event_type": "refresh_tokens_revocation_skipped",
                            "user_id": user_id,
                            "reason": "no_active_tokens"
                        }
                    )
                    return 0

                # Perform the update
                result = session.query(RefreshTokenModel).filter(
                    and_(
                        RefreshTokenModel.user_id == user_id,
                        RefreshTokenModel.is_revoked == False
                    )
                ).update(
                    {"is_revoked": True, "updated_at": datetime.utcnow()},
                    synchronize_session=False
                )

                # Prepare audit data with optional client information
                audit_data = {"user_id": user_id, "tokens_revoked": result}
                if source_ip:
                    audit_data["source_ip"] = source_ip
                if user_agent:
                    audit_data["user_agent"] = user_agent

                # Log audit event for this security-relevant operation
                log_audit_event(
                    event_type="refresh_tokens_bulk_revocation",
                    message=f"All refresh tokens revoked for user",
                    user_id=str(user_id),
                    custom_data=audit_data
                )

                self.logger.info(
                    f"Successfully revoked {result} refresh tokens for user",
                    extra={
                        "event_type": "refresh_tokens_revocation_success",
                        "user_id": user_id,
                        "tokens_revoked": result
                    }
                )
                return result
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error revoking all refresh tokens for user: {error_msg}",
                extra={
                    "event_type": "refresh_tokens_revocation_error",
                    "user_id": user_id,
                    "error_type": type(e).__name__
                }
            )
            return 0

    def delete_expired_tokens(self, before_date: Optional[datetime] = None) -> int:
        """
        Delete expired refresh tokens.

        Args:
            before_date: Optional date to delete tokens that expired before this date.
                         If not provided, deletes all expired tokens.

        Returns:
            The number of tokens deleted.
        """
        try:
            cutoff_date = before_date or datetime.utcnow()
            self.logger.info(
                f"Deleting expired refresh tokens",
                extra={
                    "event_type": "expired_tokens_deletion_request",
                    "cutoff_date": cutoff_date.isoformat() if cutoff_date else None
                }
            )

            with self.session_scope() as session:
                # First, count how many tokens will be deleted for logging
                count = session.query(RefreshTokenModel).filter(
                    or_(
                        RefreshTokenModel.expires_at < cutoff_date,
                        RefreshTokenModel.is_revoked == True
                    )
                ).count()

                if count == 0:
                    self.logger.info(
                        "No expired or revoked tokens found to delete",
                        extra={
                            "event_type": "expired_tokens_deletion_skipped",
                            "reason": "no_tokens_found"
                        }
                    )
                    return 0

                # Perform the deletion
                query = session.query(RefreshTokenModel).filter(
                    or_(
                        RefreshTokenModel.expires_at < cutoff_date,
                        RefreshTokenModel.is_revoked == True
                    )
                )
                result = query.delete(synchronize_session=False)

                self.logger.info(
                    f"Successfully deleted {result} expired or revoked refresh tokens",
                    extra={
                        "event_type": "expired_tokens_deletion_success",
                        "tokens_deleted": result
                    }
                )
                return result
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error deleting expired refresh tokens: {error_msg}",
                extra={
                    "event_type": "expired_tokens_deletion_error",
                    "error_type": type(e).__name__
                }
            )
            return 0

    def token_exists(self, token_id: str) -> bool:
        """
        Check if a token ID already exists.

        Args:
            token_id: The token ID to check.

        Returns:
            True if the token ID exists, False otherwise.
        """
        try:
            # Use rate-limited logger for this high-frequency operation
            # Redact token_id as it might be sensitive
            result = redact_log_message(
                f"Checking if refresh token exists: {token_id}",
                custom_data={"token_id": [token_id]}
            )

            self.rate_limited_logger.info(
                result.message,
                event_type="refresh_token_check",
                identifier=token_id,  # This will be hashed internally
                extra={
                    "redacted": True,
                    "redacted_fields": result.redacted_fields
                }
            )

            exists = self._session.query(RefreshTokenModel).filter(RefreshTokenModel.token_id == token_id).first() is not None

            self.rate_limited_logger.info(
                f"Refresh token exists: {exists}",
                event_type="refresh_token_check_result",
                identifier=token_id,  # This will be hashed internally
                extra={
                    "exists": exists
                }
            )
            return exists
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error checking if refresh token exists: {error_msg}",
                extra={
                    "event_type": "refresh_token_check_error",
                    "error_type": type(e).__name__
                }
            )
            # Return False on error to be safe
            return False

    def _to_domain(self, model: RefreshTokenModel) -> RefreshToken:
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
                "Converting refresh token model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "refresh_token_id": model.id,
                    "user_id": model.user_id
                }
            )

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
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting refresh token model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "refresh_token_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: RefreshToken) -> RefreshTokenModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            # Log with minimal information to avoid exposing sensitive data
            refresh_token_id = entity.id if entity.id is not None else "new token"
            self.logger.debug(
                "Converting refresh token domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "refresh_token_id": refresh_token_id,
                    "user_id": entity.user_id
                }
            )

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
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting refresh token domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "refresh_token_id": entity.id if entity and hasattr(entity, 'id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: RefreshTokenModel, entity: RefreshToken) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            # Log with minimal information to avoid exposing sensitive data
            self.logger.debug(
                "Updating refresh token model from domain entity",
                extra={
                    "event_type": "refresh_token_model_update",
                    "refresh_token_id": model.id,
                    "user_id": model.user_id
                }
            )

            # Check if revocation status is changing
            if model.is_revoked != entity.is_revoked:
                new_status = "revoked" if entity.is_revoked else "active"
                self.logger.info(
                    "Changing refresh token revocation status",
                    extra={
                        "event_type": "refresh_token_status_change",
                        "refresh_token_id": model.id,
                        "user_id": model.user_id,
                        "new_status": new_status
                    }
                )

            # Check if expiration is changing
            if model.expires_at != entity.expires_at:
                self.logger.info(
                    "Changing refresh token expiration",
                    extra={
                        "event_type": "refresh_token_expiration_change",
                        "refresh_token_id": model.id,
                        "user_id": model.user_id,
                        "new_expiration": entity.expires_at.isoformat() if entity.expires_at else None
                    }
                )

            # Update the model
            model.token_id = entity.token_id
            model.user_id = entity.user_id
            model.expires_at = entity.expires_at
            model.is_revoked = entity.is_revoked
            model.device_info = entity.device_info
            model.ip_address = entity.ip_address
            model.updated_at = datetime.utcnow()

            self.logger.debug(
                "Successfully updated refresh token model",
                extra={
                    "event_type": "refresh_token_model_update_success",
                    "refresh_token_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating refresh token model: {error_msg}",
                extra={
                    "event_type": "refresh_token_model_update_error",
                    "refresh_token_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise
