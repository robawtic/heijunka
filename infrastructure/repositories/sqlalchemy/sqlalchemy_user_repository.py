from contextlib import contextmanager
from typing import Optional, List, Dict, Generator, Any, Type
from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.entities.user import User
from domain.models.UserModel import UserModel
from domain.models.RoleModel import RoleModel
from domain.repositories.interfaces.user_repository import UserRepositoryInterface
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import redact_log_message, sanitize_exception, log_audit_event
from infrastructure.logging.logging_factory import get_logger


class SqlAlchemyUserRepository(BaseSqlAlchemyRepository[User, UserModel], UserRepositoryInterface):
    """
    SQLAlchemy implementation of the user repository interface.
    """

    def __init__(self, session: Session):
        """Initialize with SQLAlchemy session."""
        super().__init__(session, UserModel, User)
        self.logger = get_logger("heijunka.repositories.user")
        self.rate_limited_logger = get_logger("heijunka.repositories.user", rate_limit=True)

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
                    "repository": "user"
                }
            )
            raise RepositoryError(f"Database error: {error_msg}")
        except Exception as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in user repository: {error_msg}",
                extra={
                    "event_type": "unexpected_error",
                    "error_type": type(e).__name__,
                    "repository": "user"
                }
            )
            raise RepositoryError(f"Repository error: {error_msg}")

    def get_by_username(self, username: str) -> Optional[User]:
        """
        Retrieve a user by their username.

        Args:
            username: The username of the user to retrieve.

        Returns:
            The user if found, None otherwise.
        """
        try:
            result = redact_log_message(
                f"Retrieving user by username: {username}",
                custom_data={"username": [username]}
            )
            self.logger.info(
                result.message,
                extra={
                    "event_type": "user_lookup",
                    "lookup_type": "username",
                    "redacted": True,
                    "redacted_fields": result.redacted_fields
                }
            )

            model = self._session.query(UserModel).filter(UserModel.username == username).first()
            if model is None:
                self.logger.info(
                    "No user found with the provided username",
                    extra={
                        "event_type": "user_lookup_failed",
                        "lookup_type": "username"
                    }
                )
                return None

            self.logger.info(
                f"Found user with ID: {model.id}",
                extra={
                    "event_type": "user_lookup_success",
                    "lookup_type": "username",
                    "user_id": model.id
                }
            )
            return self._to_domain(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving user by username: {error_msg}",
                extra={
                    "event_type": "user_lookup_error",
                    "lookup_type": "username",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving user by username: {error_msg}")

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by their email address.

        Args:
            email: The email address of the user to retrieve.

        Returns:
            The user if found, None otherwise.
        """
        try:
            result = redact_log_message(
                f"Retrieving user by email: {email}",
                custom_data={"email": [email]}
            )
            self.logger.info(
                result.message,
                extra={
                    "event_type": "user_lookup",
                    "lookup_type": "email",
                    "redacted": True,
                    "redacted_fields": result.redacted_fields
                }
            )

            model = self._session.query(UserModel).filter(UserModel.email == email).first()
            if model is None:
                self.logger.info(
                    "No user found with the provided email",
                    extra={
                        "event_type": "user_lookup_failed",
                        "lookup_type": "email"
                    }
                )
                return None

            self.logger.info(
                f"Found user with ID: {model.id}",
                extra={
                    "event_type": "user_lookup_success",
                    "lookup_type": "email",
                    "user_id": model.id
                }
            )
            return self._to_domain(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving user by email: {error_msg}",
                extra={
                    "event_type": "user_lookup_error",
                    "lookup_type": "email",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving user by email: {error_msg}")

    def username_exists(self, username: str) -> bool:
        """
        Check if a username already exists.

        Args:
            username: The username to check.

        Returns:
            True if the username exists, False otherwise.
        """
        try:
            # Use rate-limited logger for this high-frequency operation
            result = redact_log_message(
                f"Checking if username exists: {username}",
                custom_data={"username": [username]}
            )
            self.rate_limited_logger.info(
                result.message,
                event_type="username_check",
                identifier=username,
                extra={
                    "redacted": True,
                    "redacted_fields": result.redacted_fields
                }
            )

            exists = self._session.query(UserModel).filter(UserModel.username == username).first() is not None

            self.rate_limited_logger.info(
                f"Username exists: {exists}",
                event_type="username_check_result",
                identifier=username,
                extra={
                    "exists": exists
                }
            )
            return exists
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error checking if username exists: {error_msg}",
                extra={
                    "event_type": "username_check_error",
                    "error_type": type(e).__name__
                }
            )
            # Return False on error to be safe
            return False

    def email_exists(self, email: str) -> bool:
        """
        Check if an email already exists.

        Args:
            email: The email to check.

        Returns:
            True if the email exists, False otherwise.
        """
        try:
            # Use rate-limited logger for this high-frequency operation
            result = redact_log_message(
                f"Checking if email exists: {email}",
                custom_data={"email": [email]}
            )
            self.rate_limited_logger.info(
                result.message,
                event_type="email_check",
                identifier=email,
                extra={
                    "redacted": True,
                    "redacted_fields": result.redacted_fields
                }
            )

            exists = self._session.query(UserModel).filter(UserModel.email == email).first() is not None

            self.rate_limited_logger.info(
                f"Email exists: {exists}",
                event_type="email_check_result",
                identifier=email,
                extra={
                    "exists": exists
                }
            )
            return exists
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error checking if email exists: {error_msg}",
                extra={
                    "event_type": "email_check_error",
                    "error_type": type(e).__name__
                }
            )
            # Return False on error to be safe
            return False

    def update_last_login(self, user_id: int, ip_address: str = None, user_agent: str = None) -> bool:
        """
        Update the last login timestamp for a user.

        Args:
            user_id: The ID of the user.
            ip_address: Optional IP address of the client making the request
            user_agent: Optional user agent of the client making the request

        Returns:
            True if the update was successful, False otherwise.
        """
        try:
            self.logger.info(
                f"Updating last login for user ID: {user_id}",
                extra={
                    "event_type": "update_last_login",
                    "user_id": user_id
                }
            )

            with self.session_scope() as session:
                model = session.query(UserModel).get(user_id)
                if model is None:
                    self.logger.warning(
                        f"Failed to update last login - user not found with ID: {user_id}",
                        extra={
                            "event_type": "update_last_login_failed",
                            "user_id": user_id,
                            "reason": "user_not_found"
                        }
                    )
                    return False

                # Update the last login timestamp
                model.last_login_at = datetime.utcnow()
                model.updated_at = datetime.utcnow()

                # Prepare audit data with optional client information
                audit_data = {"user_id": user_id}
                if ip_address:
                    audit_data["ip_address"] = ip_address
                    model.last_login_ip = ip_address
                if user_agent:
                    audit_data["user_agent"] = user_agent

                # Log audit event for this security-relevant operation
                log_audit_event(
                    event_type="user_login",
                    message=f"User logged in",
                    user_id=str(user_id),
                    custom_data=audit_data
                )

                self.logger.info(
                    f"Successfully updated last login for user ID: {user_id}",
                    extra={
                        "event_type": "update_last_login_success",
                        "user_id": user_id
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating last login: {error_msg}",
                extra={
                    "event_type": "update_last_login_error",
                    "user_id": user_id,
                    "error_type": type(e).__name__
                }
            )
            return False

    def add_role(self, user_id: int, role_name: str, source_ip: str = None, user_agent: str = None) -> bool:
        """
        Add a role to a user.

        Args:
            user_id: The ID of the user.
            role_name: The name of the role to add.
            source_ip: Optional IP address of the client making the request
            user_agent: Optional user agent of the client making the request

        Returns:
            True if the role was added, False otherwise.
        """
        try:
            self.logger.info(
                f"Adding role '{role_name}' to user ID: {user_id}",
                extra={
                    "event_type": "add_role",
                    "user_id": user_id,
                    "role_name": role_name
                }
            )

            with self.session_scope() as session:
                # Get the user
                user = session.query(UserModel).get(user_id)
                if user is None:
                    self.logger.warning(
                        f"Failed to add role - user not found with ID: {user_id}",
                        extra={
                            "event_type": "add_role_failed",
                            "user_id": user_id,
                            "role_name": role_name,
                            "reason": "user_not_found"
                        }
                    )
                    return False

                # Get the role
                role = session.query(RoleModel).filter(RoleModel.name == role_name).first()
                if role is None:
                    self.logger.warning(
                        f"Failed to add role - role not found with name: {role_name}",
                        extra={
                            "event_type": "add_role_failed",
                            "user_id": user_id,
                            "role_name": role_name,
                            "reason": "role_not_found"
                        }
                    )
                    return False

                # Check if the user already has this role
                if role in user.roles:
                    self.logger.info(
                        f"User already has role '{role_name}'",
                        extra={
                            "event_type": "add_role_skipped",
                            "user_id": user_id,
                            "role_name": role_name,
                            "reason": "already_has_role"
                        }
                    )
                    return True

                # Add the role to the user
                user.roles.append(role)
                user.updated_at = datetime.utcnow()

                # Prepare audit data with optional client information
                audit_data = {"user_id": user_id, "role_name": role_name}
                if source_ip:
                    audit_data["source_ip"] = source_ip
                if user_agent:
                    audit_data["user_agent"] = user_agent

                # Log audit event for this security-relevant operation
                log_audit_event(
                    event_type="user_role_added",
                    message=f"Role '{role_name}' added to user",
                    user_id=str(user_id),
                    custom_data=audit_data
                )

                self.logger.info(
                    f"Successfully added role '{role_name}' to user ID: {user_id}",
                    extra={
                        "event_type": "add_role_success",
                        "user_id": user_id,
                        "role_name": role_name
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error adding role: {error_msg}",
                extra={
                    "event_type": "add_role_error",
                    "user_id": user_id,
                    "role_name": role_name,
                    "error_type": type(e).__name__
                }
            )
            return False

    def remove_role(self, user_id: int, role_name: str, source_ip: str = None, user_agent: str = None) -> bool:
        """
        Remove a role from a user.

        Args:
            user_id: The ID of the user.
            role_name: The name of the role to remove.
            source_ip: Optional IP address of the client making the request
            user_agent: Optional user agent of the client making the request

        Returns:
            True if the role was removed, False otherwise.
        """
        try:
            self.logger.info(
                f"Removing role '{role_name}' from user ID: {user_id}",
                extra={
                    "event_type": "remove_role",
                    "user_id": user_id,
                    "role_name": role_name
                }
            )

            with self.session_scope() as session:
                # Get the user
                user = session.query(UserModel).get(user_id)
                if user is None:
                    self.logger.warning(
                        f"Failed to remove role - user not found with ID: {user_id}",
                        extra={
                            "event_type": "remove_role_failed",
                            "user_id": user_id,
                            "role_name": role_name,
                            "reason": "user_not_found"
                        }
                    )
                    return False

                # Get the role
                role = session.query(RoleModel).filter(RoleModel.name == role_name).first()
                if role is None:
                    self.logger.warning(
                        f"Failed to remove role - role not found with name: {role_name}",
                        extra={
                            "event_type": "remove_role_failed",
                            "user_id": user_id,
                            "role_name": role_name,
                            "reason": "role_not_found"
                        }
                    )
                    return False

                # Check if the user has this role
                if role not in user.roles:
                    self.logger.info(
                        f"User does not have role '{role_name}'",
                        extra={
                            "event_type": "remove_role_skipped",
                            "user_id": user_id,
                            "role_name": role_name,
                            "reason": "does_not_have_role"
                        }
                    )
                    return True

                # Remove the role from the user
                user.roles.remove(role)
                user.updated_at = datetime.utcnow()

                # Prepare audit data with optional client information
                audit_data = {"user_id": user_id, "role_name": role_name}
                if source_ip:
                    audit_data["source_ip"] = source_ip
                if user_agent:
                    audit_data["user_agent"] = user_agent

                # Log audit event for this security-relevant operation
                log_audit_event(
                    event_type="user_role_removed",
                    message=f"Role '{role_name}' removed from user",
                    user_id=str(user_id),
                    custom_data=audit_data
                )

                self.logger.info(
                    f"Successfully removed role '{role_name}' from user ID: {user_id}",
                    extra={
                        "event_type": "remove_role_success",
                        "user_id": user_id,
                        "role_name": role_name
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error removing role: {error_msg}",
                extra={
                    "event_type": "remove_role_error",
                    "user_id": user_id,
                    "role_name": role_name,
                    "error_type": type(e).__name__
                }
            )
            return False

    def get_users_by_role(self, role_name: str) -> List[User]:
        """
        Get all users with a specific role.

        Args:
            role_name: The name of the role.

        Returns:
            A list of users with the specified role.
        """
        try:
            self.logger.info(
                f"Getting users with role: {role_name}",
                extra={
                    "event_type": "get_users_by_role",
                    "role_name": role_name
                }
            )

            # Get the role
            role = self._session.query(RoleModel).filter(RoleModel.name == role_name).first()
            if role is None:
                self.logger.warning(
                    f"Role not found with name: {role_name}",
                    extra={
                        "event_type": "get_users_by_role_failed",
                        "role_name": role_name,
                        "reason": "role_not_found"
                    }
                )
                return []

            # Get users with this role
            users = []
            for user_model in role.users:
                users.append(self._to_domain(user_model))

            self.logger.info(
                f"Found {len(users)} users with role: {role_name}",
                extra={
                    "event_type": "get_users_by_role_success",
                    "role_name": role_name,
                    "user_count": len(users)
                }
            )
            return users
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error getting users by role: {error_msg}",
                extra={
                    "event_type": "get_users_by_role_error",
                    "role_name": role_name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error getting users by role: {error_msg}")

    def activate_user(self, user_id: int, source_ip: str = None, user_agent: str = None) -> bool:
        """
        Activate a user account.

        Args:
            user_id: The ID of the user to activate.
            source_ip: Optional IP address of the client making the request
            user_agent: Optional user agent of the client making the request

        Returns:
            True if the user was activated, False otherwise.
        """
        try:
            self.logger.info(
                f"Activating user with ID: {user_id}",
                extra={
                    "event_type": "activate_user",
                    "user_id": user_id
                }
            )

            with self.session_scope() as session:
                model = session.query(UserModel).get(user_id)
                if model is None:
                    self.logger.warning(
                        f"Failed to activate user - user not found with ID: {user_id}",
                        extra={
                            "event_type": "activate_user_failed",
                            "user_id": user_id,
                            "reason": "user_not_found"
                        }
                    )
                    return False

                # Only activate if not already active
                if model.is_active:
                    self.logger.info(
                        f"User is already active",
                        extra={
                            "event_type": "activate_user_skipped",
                            "user_id": user_id,
                            "reason": "already_active"
                        }
                    )
                    return True

                model.is_active = True
                model.updated_at = datetime.utcnow()

                # Prepare audit data with optional client information
                audit_data = {"user_id": user_id}
                if source_ip:
                    audit_data["source_ip"] = source_ip
                if user_agent:
                    audit_data["user_agent"] = user_agent

                # Log audit event for this security-relevant operation
                log_audit_event(
                    event_type="user_activated",
                    message="User account activated",
                    user_id=str(user_id),
                    custom_data=audit_data
                )

                self.logger.info(
                    f"Successfully activated user with ID: {user_id}",
                    extra={
                        "event_type": "activate_user_success",
                        "user_id": user_id
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error activating user: {error_msg}",
                extra={
                    "event_type": "activate_user_error",
                    "user_id": user_id,
                    "error_type": type(e).__name__
                }
            )
            return False

    def deactivate_user(self, user_id: int, source_ip: str = None, user_agent: str = None) -> bool:
        """
        Deactivate a user account.

        Args:
            user_id: The ID of the user to deactivate.
            source_ip: Optional IP address of the client making the request
            user_agent: Optional user agent of the client making the request

        Returns:
            True if the user was deactivated, False otherwise.
        """
        try:
            self.logger.info(
                f"Deactivating user with ID: {user_id}",
                extra={
                    "event_type": "deactivate_user",
                    "user_id": user_id
                }
            )

            with self.session_scope() as session:
                model = session.query(UserModel).get(user_id)
                if model is None:
                    self.logger.warning(
                        f"Failed to deactivate user - user not found with ID: {user_id}",
                        extra={
                            "event_type": "deactivate_user_failed",
                            "user_id": user_id,
                            "reason": "user_not_found"
                        }
                    )
                    return False

                # Only deactivate if not already inactive
                if not model.is_active:
                    self.logger.info(
                        f"User is already inactive",
                        extra={
                            "event_type": "deactivate_user_skipped",
                            "user_id": user_id,
                            "reason": "already_inactive"
                        }
                    )
                    return True

                model.is_active = False
                model.updated_at = datetime.utcnow()

                # Prepare audit data with optional client information
                audit_data = {"user_id": user_id}
                if source_ip:
                    audit_data["source_ip"] = source_ip
                if user_agent:
                    audit_data["user_agent"] = user_agent

                # Log audit event for this security-relevant operation
                log_audit_event(
                    event_type="user_deactivated",
                    message="User account deactivated",
                    user_id=str(user_id),
                    custom_data=audit_data
                )

                self.logger.info(
                    f"Successfully deactivated user with ID: {user_id}",
                    extra={
                        "event_type": "deactivate_user_success",
                        "user_id": user_id
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error deactivating user: {error_msg}",
                extra={
                    "event_type": "deactivate_user_error",
                    "user_id": user_id,
                    "error_type": type(e).__name__
                }
            )
            return False

    def _to_domain(self, model: UserModel) -> User:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            self.logger.debug(
                "Converting user model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "user_id": model.id
                }
            )

            # Extract role names
            role_names = [role.name for role in model.roles] if model.roles else []

            return User(
                id=model.id,
                username=model.username,
                email=model.email,
                password_hash=model.password_hash,
                first_name=model.first_name,
                last_name=model.last_name,
                is_active=model.is_active,
                is_verified=model.is_verified,
                roles=role_names,
                created_at=model.created_at,
                updated_at=model.updated_at,
                last_login_at=model.last_login_at,
                last_login_ip=model.last_login_ip,
                verification_token=model.verification_token,
                verification_token_expires_at=model.verification_token_expires_at,
                password_reset_token=model.password_reset_token,
                password_reset_token_expires_at=model.password_reset_token_expires_at
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting user model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "user_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: User) -> UserModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            user_id = entity.id if entity.id is not None else "new user"
            self.logger.debug(
                "Converting user domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "user_id": user_id
                }
            )

            model = UserModel(
                username=entity.username,
                email=entity.email,
                password_hash=entity.password_hash,
                first_name=entity.first_name,
                last_name=entity.last_name,
                is_active=entity.is_active,
                is_verified=entity.is_verified,
                last_login_at=entity.last_login_at,
                last_login_ip=entity.last_login_ip,
                verification_token=entity.verification_token,
                verification_token_expires_at=entity.verification_token_expires_at,
                password_reset_token=entity.password_reset_token,
                password_reset_token_expires_at=entity.password_reset_token_expires_at
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
                f"Error converting user domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "user_id": entity.id if entity and hasattr(entity, 'id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: UserModel, entity: User) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            self.logger.debug(
                "Updating user model from domain entity",
                extra={
                    "event_type": "user_model_update",
                    "user_id": model.id
                }
            )

            # Check for significant changes and log them
            if model.is_active != entity.is_active:
                new_status = "active" if entity.is_active else "inactive"
                self.logger.info(
                    f"Changing user status to {new_status}",
                    extra={
                        "event_type": "user_status_change",
                        "user_id": model.id,
                        "new_status": new_status
                    }
                )

            if model.is_verified != entity.is_verified:
                new_status = "verified" if entity.is_verified else "unverified"
                self.logger.info(
                    f"Changing user verification status to {new_status}",
                    extra={
                        "event_type": "user_verification_status_change",
                        "user_id": model.id,
                        "new_status": new_status
                    }
                )

            if model.email != entity.email:
                result = redact_log_message(
                    f"Changing user email from {model.email} to {entity.email}",
                    custom_data={"old_email": [model.email], "new_email": [entity.email]}
                )
                self.logger.info(
                    result.message,
                    extra={
                        "event_type": "user_email_change",
                        "user_id": model.id,
                        "redacted": True,
                        "redacted_fields": result.redacted_fields
                    }
                )

            if model.username != entity.username:
                result = redact_log_message(
                    f"Changing username from {model.username} to {entity.username}",
                    custom_data={"old_username": [model.username], "new_username": [entity.username]}
                )
                self.logger.info(
                    result.message,
                    extra={
                        "event_type": "username_change",
                        "user_id": model.id,
                        "redacted": True,
                        "redacted_fields": result.redacted_fields
                    }
                )

            if model.password_hash != entity.password_hash:
                self.logger.info(
                    "User password has been changed",
                    extra={
                        "event_type": "password_change",
                        "user_id": model.id
                    }
                )

            # Update the model
            model.username = entity.username
            model.email = entity.email
            model.password_hash = entity.password_hash
            model.first_name = entity.first_name
            model.last_name = entity.last_name
            model.is_active = entity.is_active
            model.is_verified = entity.is_verified
            model.last_login_at = entity.last_login_at
            model.last_login_ip = entity.last_login_ip
            model.verification_token = entity.verification_token
            model.verification_token_expires_at = entity.verification_token_expires_at
            model.password_reset_token = entity.password_reset_token
            model.password_reset_token_expires_at = entity.password_reset_token_expires_at
            model.updated_at = datetime.utcnow()

            self.logger.debug(
                "Successfully updated user model",
                extra={
                    "event_type": "user_model_update_success",
                    "user_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating user model: {error_msg}",
                extra={
                    "event_type": "user_model_update_error",
                    "user_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise