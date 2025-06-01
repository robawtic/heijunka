from contextlib import contextmanager
from typing import Optional, List, Generator
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.entities.user import User
from domain.models.UserModel import UserModel
from domain.models.RoleModel import RoleModel
from domain.repositories.interfaces.user_repository import UserRepositoryInterface
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import redact_log_message, sanitize_exception, log_audit_event
from utilities.logging_factory import get_logger


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

            return False

    def email_exists(self, email: str) -> bool:
        """
        Check if an email address already exists.

        Args:
            email: The email address to check.

        Returns:
            True if the email exists, False otherwise.
        """
        try:

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

            return False

    def update_last_login(self, user_id: int, ip_address: str = None, user_agent: str = None) -> bool:
        """
        Update the last login timestamp for a user.

        Args:
            user_id: The ID of the user to update.
            ip_address: Optional IP address of the client
            user_agent: Optional user agent string

        Returns:
            True if the update was successful, False otherwise.
        """
        self.logger.info(
            "Updating last login timestamp",
            extra={
                "event_type": "user_login_update",
                "user_id": user_id,
                "operation": "update_last_login"
            }
        )

        try:
            with self.session_scope() as session:
                user = session.query(UserModel).get(user_id)
                if user is None:
                    self.logger.warning(
                        "Failed to update last login - user not found",
                        extra={
                            "event_type": "user_login_update_failed",
                            "user_id": user_id,
                            "reason": "user_not_found"
                        }
                    )
                    return False


                result = redact_log_message(
                    f"Updating last login for user {user.username} (ID: {user_id})",
                    custom_data={"username": [user.username]}
                )
                self.logger.info(
                    result.message,
                    extra={
                        "event_type": "user_login_update_processing",
                        "user_id": user_id,
                        "redacted": True,
                        "redacted_fields": result.redacted_fields
                    }
                )

                user.last_login = datetime.utcnow()

                # Add IP and user agent if provided
                context_data = {
                    "event_type": "user_login_updated", 
                    "user_id": user_id
                }
                if ip_address:
                    context_data["ip_address"] = ip_address
                if user_agent:
                    context_data["user_agent"] = user_agent

                self.logger.info(
                    "Successfully updated last login timestamp",
                    extra=context_data
                )
                return True
        except RepositoryError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating last login: {error_msg}",
                extra={
                    "event_type": "user_login_update_error",
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
            True if the role was added successfully, False otherwise.
        """
        self.logger.info(
            f"Adding role to user",
            extra={
                "event_type": "role_assignment_request",
                "user_id": user_id,
                "role": role_name
            }
        )
        try:
            with self.session_scope() as session:
                user = session.query(UserModel).get(user_id)
                if user is None:
                    self.logger.warning(
                        "Failed to add role - user not found",
                        extra={
                            "event_type": "role_assignment_failed",
                            "user_id": user_id,
                            "role": role_name,
                            "reason": "user_not_found"
                        }
                    )
                    return False


                result = redact_log_message(
                    f"Adding role '{role_name}' to user {user.username} (ID: {user_id})",
                    custom_data={"username": [user.username]}
                )
                self.logger.info(
                    result.message,
                    extra={
                        "event_type": "role_assignment_processing",
                        "user_id": user_id,
                        "role": role_name,
                        "redacted": True,
                        "redacted_fields": result.redacted_fields
                    }
                )

                role = session.query(RoleModel).filter(RoleModel.name == role_name).first()
                if role is None:
                    # Create the role if it doesn't exist
                    self.logger.info(
                        f"Role not found, creating new role",
                        extra={
                            "event_type": "role_creation",
                            "role": role_name
                        }
                    )
                    role = RoleModel(name=role_name)
                    session.add(role)
                    session.flush()

                if role not in user.roles:
                    user.roles.append(role)


                    audit_data = {"role": role_name, "username": user.username}
                    if source_ip:
                        audit_data["source_ip"] = source_ip
                    if user_agent:
                        audit_data["user_agent"] = user_agent


                    log_audit_event(
                        event_type="role_assignment",
                        message=f"Role assigned to user",
                        user_id=str(user_id),
                        custom_data=audit_data
                    )

                    self.logger.info(
                        "Successfully added role to user",
                        extra={
                            "event_type": "role_assignment_success",
                            "user_id": user_id,
                            "role": role_name
                        }
                    )
                else:
                    self.logger.info(
                        "User already has role",
                        extra={
                            "event_type": "role_assignment_skipped",
                            "user_id": user_id,
                            "role": role_name,
                            "reason": "already_assigned"
                        }
                    )

                return True
        except RepositoryError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error adding role to user: {error_msg}",
                extra={
                    "event_type": "role_assignment_error",
                    "user_id": user_id,
                    "role": role_name,
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
            True if the role was removed successfully, False otherwise.
        """
        self.logger.info(
            "Removing role from user",
            extra={
                "event_type": "role_removal_request",
                "user_id": user_id,
                "role": role_name
            }
        )
        try:
            with self.session_scope() as session:
                user = session.query(UserModel).get(user_id)
                if user is None:
                    self.logger.warning(
                        "Failed to remove role - user not found",
                        extra={
                            "event_type": "role_removal_failed",
                            "user_id": user_id,
                            "role": role_name,
                            "reason": "user_not_found"
                        }
                    )
                    return False


                result = redact_log_message(
                    f"Removing role '{role_name}' from user {user.username} (ID: {user_id})",
                    custom_data={"username": [user.username]}
                )
                self.logger.info(
                    result.message,
                    extra={
                        "event_type": "role_removal_processing",
                        "user_id": user_id,
                        "role": role_name,
                        "redacted": True,
                        "redacted_fields": result.redacted_fields
                    }
                )

                role = session.query(RoleModel).filter(RoleModel.name == role_name).first()
                if role is None or role not in user.roles:
                    self.logger.info(
                        "Role not found for user",
                        extra={
                            "event_type": "role_removal_failed",
                            "user_id": user_id,
                            "role": role_name,
                            "reason": "role_not_assigned"
                        }
                    )
                    return False

                user.roles.remove(role)


                audit_data = {"role": role_name, "username": user.username}
                if source_ip:
                    audit_data["source_ip"] = source_ip
                if user_agent:
                    audit_data["user_agent"] = user_agent


                log_audit_event(
                    event_type="role_removal",
                    message=f"Role removed from user",
                    user_id=str(user_id),
                    custom_data=audit_data
                )

                self.logger.info(
                    "Successfully removed role from user",
                    extra={
                        "event_type": "role_removal_success",
                        "user_id": user_id,
                        "role": role_name
                    }
                )
                return True
        except RepositoryError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error removing role from user: {error_msg}",
                extra={
                    "event_type": "role_removal_error",
                    "user_id": user_id,
                    "role": role_name,
                    "error_type": type(e).__name__
                }
            )
            return False

    def get_users_by_role(self, role_name: str) -> List[User]:
        """
        Get all users with a specific role.

        Args:
            role_name: The name of the role to filter by.

        Returns:
            A list of users with the specified role.
        """
        self.logger.info(
            "Retrieving users with role",
            extra={
                "event_type": "users_by_role_lookup",
                "role": role_name
            }
        )
        try:
            role = self._session.query(RoleModel).filter(RoleModel.name == role_name).first()
            if role is None:
                self.logger.info(
                    "Role not found",
                    extra={
                        "event_type": "users_by_role_lookup_failed",
                        "role": role_name,
                        "reason": "role_not_found"
                    }
                )
                return []

            users = self._session.query(UserModel).filter(UserModel.roles.contains(role)).all()
            user_count = len(users)

            # Don't log usernames directly, just the count
            self.logger.info(
                f"Found users with role",
                extra={
                    "event_type": "users_by_role_lookup_success",
                    "role": role_name,
                    "user_count": user_count
                }
            )

            return [self._to_domain(user) for user in users]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving users by role: {error_msg}",
                extra={
                    "event_type": "users_by_role_lookup_error",
                    "role": role_name,
                    "error_type": type(e).__name__
                }
            )
            return []

    def activate_user(self, user_id: int, source_ip: str = None, user_agent: str = None) -> bool:
        """
        Activate a user account.

        Args:
            user_id: The ID of the user to activate.
            source_ip: Optional IP address of the client making the request
            user_agent: Optional user agent of the client making the request

        Returns:
            True if the activation was successful, False otherwise.
        """
        self.logger.info(
            "Activating user account",
            extra={
                "event_type": "account_activation_request",
                "user_id": user_id
            }
        )
        try:
            with self.session_scope() as session:
                user = session.query(UserModel).get(user_id)
                if user is None:
                    self.logger.warning(
                        "Failed to activate user - user not found",
                        extra={
                            "event_type": "account_activation_failed",
                            "user_id": user_id,
                            "reason": "user_not_found"
                        }
                    )
                    return False


                result = redact_log_message(
                    f"Activating account for user {user.username} (ID: {user_id})",
                    custom_data={"username": [user.username]}
                )
                self.logger.info(
                    result.message,
                    extra={
                        "event_type": "account_activation_processing",
                        "user_id": user_id,
                        "redacted": True,
                        "redacted_fields": result.redacted_fields
                    }
                )

                # Only activate if not already active
                if user.is_active:
                    self.logger.info(
                        "User account is already active",
                        extra={
                            "event_type": "account_activation_skipped",
                            "user_id": user_id,
                            "reason": "already_active"
                        }
                    )
                    return True

                user.is_active = True


                audit_data = {"username": user.username}
                if source_ip:
                    audit_data["source_ip"] = source_ip
                if user_agent:
                    audit_data["user_agent"] = user_agent


                log_audit_event(
                    event_type="account_activation",
                    message=f"User account activated",
                    user_id=str(user_id),
                    custom_data=audit_data
                )

                self.logger.info(
                    "Successfully activated user account",
                    extra={
                        "event_type": "account_activation_success",
                        "user_id": user_id
                    }
                )
                return True
        except RepositoryError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error activating user account: {error_msg}",
                extra={
                    "event_type": "account_activation_error",
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
            True if the deactivation was successful, False otherwise.
        """
        self.logger.info(
            "Deactivating user account",
            extra={
                "event_type": "account_deactivation_request",
                "user_id": user_id
            }
        )
        try:
            with self.session_scope() as session:
                user = session.query(UserModel).get(user_id)
                if user is None:
                    self.logger.warning(
                        "Failed to deactivate user - user not found",
                        extra={
                            "event_type": "account_deactivation_failed",
                            "user_id": user_id,
                            "reason": "user_not_found"
                        }
                    )
                    return False


                result = redact_log_message(
                    f"Deactivating account for user {user.username} (ID: {user_id})",
                    custom_data={"username": [user.username]}
                )
                self.logger.info(
                    result.message,
                    extra={
                        "event_type": "account_deactivation_processing",
                        "user_id": user_id,
                        "redacted": True,
                        "redacted_fields": result.redacted_fields
                    }
                )

                # Only deactivate if not already inactive
                if not user.is_active:
                    self.logger.info(
                        "User account is already inactive",
                        extra={
                            "event_type": "account_deactivation_skipped",
                            "user_id": user_id,
                            "reason": "already_inactive"
                        }
                    )
                    return True

                user.is_active = False


                audit_data = {"username": user.username}
                if source_ip:
                    audit_data["source_ip"] = source_ip
                if user_agent:
                    audit_data["user_agent"] = user_agent


                log_audit_event(
                    event_type="account_deactivation",
                    message=f"User account deactivated",
                    user_id=str(user_id),
                    custom_data=audit_data
                )

                self.logger.info(
                    "Successfully deactivated user account",
                    extra={
                        "event_type": "account_deactivation_success",
                        "user_id": user_id
                    }
                )
                return True
        except RepositoryError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error deactivating user account: {error_msg}",
                extra={
                    "event_type": "account_deactivation_error",
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

            user = User(
                id=model.id,
                username=model.username,
                email=model.email,
                is_active=model.is_active,
                created_at=model.created_at,
                updated_at=model.updated_at,
                last_login=model.last_login
            )

            # Set password hash directly to avoid hashing again
            user._password_hash = model.password_hash

            # Add roles
            role_names = []
            for role_model in model.roles:
                role = role_model.to_domain()
                user._roles.append(role)
                role_names.append(role.name)


            if role_names:
                self.logger.debug(
                    "User roles loaded",
                    extra={
                        "event_type": "user_roles_loaded",
                        "user_id": model.id,
                        "role_count": len(role_names),
                        "roles": role_names
                    }
                )

            return user
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
                password_hash=entity._password_hash,
                is_active=entity.is_active,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
                last_login=entity.last_login
            )

            if entity.id is not None:
                model.id = entity.id


            if entity.roles:
                self.logger.debug(
                    "User roles included in model",
                    extra={
                        "event_type": "user_roles_included",
                        "user_id": user_id,
                        "role_count": len(entity.roles),
                        "roles": entity.roles
                    }
                )

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


            if model.username != entity.username:
                result = redact_log_message(
                    f"Changing username from {model.username} to {entity.username} for user ID: {model.id}",
                    custom_data={"username": [model.username, entity.username]}
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


            if model.email != entity.email:
                result = redact_log_message(
                    f"Changing email from {model.email} to {entity.email} for user ID: {model.id}",
                    custom_data={"email": [model.email, entity.email]}
                )
                self.logger.info(
                    result.message,
                    extra={
                        "event_type": "email_change",
                        "user_id": model.id,
                        "redacted": True,
                        "redacted_fields": result.redacted_fields
                    }
                )


            if model.password_hash != entity._password_hash:
                self.logger.info(
                    "Password hash changed",
                    extra={
                        "event_type": "password_change",
                        "user_id": model.id
                    }
                )


            if model.is_active != entity.is_active:
                new_status = "active" if entity.is_active else "inactive"
                self.logger.info(
                    "Changing user status",
                    extra={
                        "event_type": "status_change",
                        "user_id": model.id,
                        "new_status": new_status
                    }
                )


            model.username = entity.username
            model.email = entity.email
            model.password_hash = entity._password_hash
            model.is_active = entity.is_active
            model.updated_at = datetime.utcnow()
            model.last_login = entity.last_login


            current_role_names = [role.name for role in model.roles]
            new_role_names = [role.name for role in entity.roles]

            # Log role changes
            added_roles = [role_name for role_name in new_role_names if role_name not in current_role_names]
            removed_roles = [role_name for role_name in current_role_names if role_name not in new_role_names]

            if added_roles:
                self.logger.info(
                    "Adding roles to user",
                    extra={
                        "event_type": "roles_added",
                        "user_id": model.id,
                        "roles": added_roles
                    }
                )

            if removed_roles:
                self.logger.info(
                    "Removing roles from user",
                    extra={
                        "event_type": "roles_removed",
                        "user_id": model.id,
                        "roles": removed_roles
                    }
                )


            model.roles = []
            for role_entity in entity.roles:
                role = self._session.query(RoleModel).filter(RoleModel.name == role_entity.name).first()
                if role is None:
                    self.logger.info(
                        "Creating new role",
                        extra={
                            "event_type": "role_creation",
                            "role": role_name
                        }
                    )
                    role = RoleModel(name=role_name)
                    self._session.add(role)
                    self._session.flush()
                model.roles.append(role)

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
