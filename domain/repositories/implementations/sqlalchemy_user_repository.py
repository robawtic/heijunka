from contextlib import contextmanager
from typing import Optional, List, Dict, Generator, Any, Type
from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
import logging

from domain.entities.user import User
from domain.models.UserModel import UserModel
from domain.models.RoleModel import RoleModel
from domain.repositories.interfaces.user_repository import UserRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import redact_log_message, sanitize_exception, log_audit_event


class SqlAlchemyUserRepository(BaseSqlAlchemyRepository[User, UserModel], UserRepositoryInterface):
    """
    SQLAlchemy implementation of the user repository interface.
    """

    def __init__(self, session: Session):
        """Initialize with SQLAlchemy session."""
        super().__init__(session, UserModel, User)
        self.logger = logging.getLogger("heijunka.repositories.user")

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
            self.logger.error(f"Database operation failed: {error_msg}")
            raise RepositoryError(f"Database error: {error_msg}")
        except Exception as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(f"Unexpected error in user repository: {error_msg}")
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
            # Log with redaction since username is sensitive
            result = redact_log_message(
                f"Retrieving user by username: {username}",
                custom_data={"username": [username]}
            )
            self.logger.info(result.message)

            model = self._session.query(UserModel).filter(UserModel.username == username).first()
            if model is None:
                self.logger.info("No user found with the provided username")
                return None

            self.logger.info(f"Found user with ID: {model.id}")
            return self._to_domain(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(f"Error retrieving user by username: {error_msg}")
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
            # Log with redaction since email is sensitive
            result = redact_log_message(
                f"Retrieving user by email: {email}",
                custom_data={"email": [email]}
            )
            self.logger.info(result.message)

            model = self._session.query(UserModel).filter(UserModel.email == email).first()
            if model is None:
                self.logger.info("No user found with the provided email")
                return None

            self.logger.info(f"Found user with ID: {model.id}")
            return self._to_domain(model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(f"Error retrieving user by email: {error_msg}")
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
            # Log with redaction since username is sensitive
            result = redact_log_message(
                f"Checking if username exists: {username}",
                custom_data={"username": [username]}
            )
            self.logger.info(result.message)

            exists = self._session.query(UserModel).filter(UserModel.username == username).first() is not None
            self.logger.info(f"Username exists: {exists}")
            return exists
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(f"Error checking if username exists: {error_msg}")
            # Return False on error to be safe
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
            # Log with redaction since email is sensitive
            result = redact_log_message(
                f"Checking if email exists: {email}",
                custom_data={"email": [email]}
            )
            self.logger.info(result.message)

            exists = self._session.query(UserModel).filter(UserModel.email == email).first() is not None
            self.logger.info(f"Email exists: {exists}")
            return exists
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(f"Error checking if email exists: {error_msg}")
            # Return False on error to be safe
            return False

    def update_last_login(self, user_id: int) -> bool:
        """
        Update the last login timestamp for a user.

        Args:
            user_id: The ID of the user to update.

        Returns:
            True if the update was successful, False otherwise.
        """
        self.logger.info(f"Updating last login timestamp for user ID: {user_id}")
        try:
            with self.session_scope() as session:
                user = session.query(UserModel).get(user_id)
                if user is None:
                    self.logger.warning(f"Failed to update last login - user not found with ID: {user_id}")
                    return False

                # Log with redaction since username is sensitive
                result = redact_log_message(
                    f"Updating last login for user {user.username} (ID: {user_id})",
                    custom_data={"username": [user.username]}
                )
                self.logger.info(result.message)

                user.last_login = datetime.utcnow()
                self.logger.info(f"Successfully updated last login timestamp for user ID: {user_id}")
                return True
        except RepositoryError as e:
            self.logger.error(f"Error updating last login for user ID {user_id}: {sanitize_exception(e)}")
            return False

    def add_role(self, user_id: int, role_name: str) -> bool:
        """
        Add a role to a user.

        Args:
            user_id: The ID of the user.
            role_name: The name of the role to add.

        Returns:
            True if the role was added successfully, False otherwise.
        """
        self.logger.info(f"Adding role '{role_name}' to user ID: {user_id}")
        try:
            with self.session_scope() as session:
                user = session.query(UserModel).get(user_id)
                if user is None:
                    self.logger.warning(f"Failed to add role - user not found with ID: {user_id}")
                    return False

                # Log with redaction since username is sensitive
                result = redact_log_message(
                    f"Adding role '{role_name}' to user {user.username} (ID: {user_id})",
                    custom_data={"username": [user.username]}
                )
                self.logger.info(result.message)

                role = session.query(RoleModel).filter(RoleModel.name == role_name).first()
                if role is None:
                    # Create the role if it doesn't exist
                    self.logger.info(f"Role '{role_name}' not found, creating new role")
                    role = RoleModel(name=role_name)
                    session.add(role)
                    session.flush()

                if role not in user.roles:
                    user.roles.append(role)

                    # Log audit event for this security-relevant operation
                    log_audit_event(
                        event_type="role_assignment",
                        message=f"Role assigned to user",
                        user_id=str(user_id),
                        custom_data={"role": role_name, "username": user.username}
                    )

                    self.logger.info(f"Successfully added role '{role_name}' to user ID: {user_id}")
                else:
                    self.logger.info(f"User ID {user_id} already has role '{role_name}'")

                return True
        except RepositoryError as e:
            self.logger.error(f"Error adding role '{role_name}' to user ID {user_id}: {sanitize_exception(e)}")
            return False

    def remove_role(self, user_id: int, role_name: str) -> bool:
        """
        Remove a role from a user.

        Args:
            user_id: The ID of the user.
            role_name: The name of the role to remove.

        Returns:
            True if the role was removed successfully, False otherwise.
        """
        self.logger.info(f"Removing role '{role_name}' from user ID: {user_id}")
        try:
            with self.session_scope() as session:
                user = session.query(UserModel).get(user_id)
                if user is None:
                    self.logger.warning(f"Failed to remove role - user not found with ID: {user_id}")
                    return False

                # Log with redaction since username is sensitive
                result = redact_log_message(
                    f"Removing role '{role_name}' from user {user.username} (ID: {user_id})",
                    custom_data={"username": [user.username]}
                )
                self.logger.info(result.message)

                role = session.query(RoleModel).filter(RoleModel.name == role_name).first()
                if role is None or role not in user.roles:
                    self.logger.info(f"Role '{role_name}' not found for user ID: {user_id}")
                    return False

                user.roles.remove(role)

                # Log audit event for this security-relevant operation
                log_audit_event(
                    event_type="role_removal",
                    message=f"Role removed from user",
                    user_id=str(user_id),
                    custom_data={"role": role_name, "username": user.username}
                )

                self.logger.info(f"Successfully removed role '{role_name}' from user ID: {user_id}")
                return True
        except RepositoryError as e:
            self.logger.error(f"Error removing role '{role_name}' from user ID {user_id}: {sanitize_exception(e)}")
            return False

    def get_users_by_role(self, role_name: str) -> List[User]:
        """
        Get all users with a specific role.

        Args:
            role_name: The name of the role to filter by.

        Returns:
            A list of users with the specified role.
        """
        self.logger.info(f"Retrieving users with role: {role_name}")
        try:
            role = self._session.query(RoleModel).filter(RoleModel.name == role_name).first()
            if role is None:
                self.logger.info(f"Role '{role_name}' not found")
                return []

            users = self._session.query(UserModel).filter(UserModel.roles.contains(role)).all()
            user_count = len(users)

            # Don't log usernames directly, just the count
            self.logger.info(f"Found {user_count} users with role '{role_name}'")

            return [self._to_domain(user) for user in users]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(f"Error retrieving users by role '{role_name}': {error_msg}")
            return []

    def activate_user(self, user_id: int) -> bool:
        """
        Activate a user account.

        Args:
            user_id: The ID of the user to activate.

        Returns:
            True if the activation was successful, False otherwise.
        """
        self.logger.info(f"Activating user account with ID: {user_id}")
        try:
            with self.session_scope() as session:
                user = session.query(UserModel).get(user_id)
                if user is None:
                    self.logger.warning(f"Failed to activate user - user not found with ID: {user_id}")
                    return False

                # Log with redaction since username is sensitive
                result = redact_log_message(
                    f"Activating account for user {user.username} (ID: {user_id})",
                    custom_data={"username": [user.username]}
                )
                self.logger.info(result.message)

                # Only activate if not already active
                if user.is_active:
                    self.logger.info(f"User account with ID {user_id} is already active")
                    return True

                user.is_active = True

                # Log audit event for this security-relevant operation
                log_audit_event(
                    event_type="account_activation",
                    message=f"User account activated",
                    user_id=str(user_id),
                    custom_data={"username": user.username}
                )

                self.logger.info(f"Successfully activated user account with ID: {user_id}")
                return True
        except RepositoryError as e:
            self.logger.error(f"Error activating user account with ID {user_id}: {sanitize_exception(e)}")
            return False

    def deactivate_user(self, user_id: int) -> bool:
        """
        Deactivate a user account.

        Args:
            user_id: The ID of the user to deactivate.

        Returns:
            True if the deactivation was successful, False otherwise.
        """
        self.logger.info(f"Deactivating user account with ID: {user_id}")
        try:
            with self.session_scope() as session:
                user = session.query(UserModel).get(user_id)
                if user is None:
                    self.logger.warning(f"Failed to deactivate user - user not found with ID: {user_id}")
                    return False

                # Log with redaction since username is sensitive
                result = redact_log_message(
                    f"Deactivating account for user {user.username} (ID: {user_id})",
                    custom_data={"username": [user.username]}
                )
                self.logger.info(result.message)

                # Only deactivate if not already inactive
                if not user.is_active:
                    self.logger.info(f"User account with ID {user_id} is already inactive")
                    return True

                user.is_active = False

                # Log audit event for this security-relevant operation
                log_audit_event(
                    event_type="account_deactivation",
                    message=f"User account deactivated",
                    user_id=str(user_id),
                    custom_data={"username": user.username}
                )

                self.logger.info(f"Successfully deactivated user account with ID: {user_id}")
                return True
        except RepositoryError as e:
            self.logger.error(f"Error deactivating user account with ID {user_id}: {sanitize_exception(e)}")
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
            # Log with minimal information to avoid exposing sensitive data
            self.logger.debug(f"Converting user model to domain entity, ID: {model.id}")

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
            for role in model.roles:
                user._roles.append(role.name)
                role_names.append(role.name)

            # Log roles without exposing username or other sensitive data
            if role_names:
                self.logger.debug(f"User ID {model.id} has roles: {', '.join(role_names)}")

            return user
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(f"Error converting user model to domain entity: {error_msg}")
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
            # Log with minimal information to avoid exposing sensitive data
            user_id = entity.id if entity.id is not None else "new user"
            self.logger.debug(f"Converting user domain entity to model, ID: {user_id}")

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

            # Log roles without exposing username or other sensitive data
            if entity.roles:
                self.logger.debug(f"User has roles: {', '.join(entity.roles)}")

            return model
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(f"Error converting user domain entity to model: {error_msg}")
            raise

    def _update_model(self, model: UserModel, entity: User) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            # Log with minimal information to avoid exposing sensitive data
            self.logger.debug(f"Updating user model from domain entity, ID: {model.id}")

            # Check if username is changing
            if model.username != entity.username:
                result = redact_log_message(
                    f"Changing username from {model.username} to {entity.username} for user ID: {model.id}",
                    custom_data={"username": [model.username, entity.username]}
                )
                self.logger.info(result.message)

            # Check if email is changing
            if model.email != entity.email:
                result = redact_log_message(
                    f"Changing email from {model.email} to {entity.email} for user ID: {model.id}",
                    custom_data={"email": [model.email, entity.email]}
                )
                self.logger.info(result.message)

            # Check if active status is changing
            if model.is_active != entity.is_active:
                new_status = "active" if entity.is_active else "inactive"
                self.logger.info(f"Changing user status to {new_status} for user ID: {model.id}")

            # Update the model
            model.username = entity.username
            model.email = entity.email
            model.password_hash = entity._password_hash
            model.is_active = entity.is_active
            model.updated_at = datetime.utcnow()
            model.last_login = entity.last_login

            # Get current roles for comparison
            current_roles = [role.name for role in model.roles]
            new_roles = entity.roles

            # Log role changes
            added_roles = [role for role in new_roles if role not in current_roles]
            removed_roles = [role for role in current_roles if role not in new_roles]

            if added_roles:
                self.logger.info(f"Adding roles to user ID {model.id}: {', '.join(added_roles)}")

            if removed_roles:
                self.logger.info(f"Removing roles from user ID {model.id}: {', '.join(removed_roles)}")

            # Update roles
            model.roles = []
            for role_name in entity.roles:
                role = self._session.query(RoleModel).filter(RoleModel.name == role_name).first()
                if role is None:
                    self.logger.info(f"Creating new role: {role_name}")
                    role = RoleModel(name=role_name)
                    self._session.add(role)
                    self._session.flush()

                model.roles.append(role)

            self.logger.debug(f"Successfully updated user model for ID: {model.id}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(f"Error updating user model: {error_msg}")
            raise
