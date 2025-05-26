from typing import List, Optional, Dict, Any
from datetime import datetime

from domain.entities.user import User
from domain.repositories.interfaces.user_repository import UserRepositoryInterface
from domain.events.publisher import DomainEventPublisher


class UserService:
    """
    Service for managing users.

    This service provides methods for creating, updating, and managing users,
    as well as authentication and authorization.
    """

    def __init__(
        self, 
        user_repository: UserRepositoryInterface,
        event_publisher: Optional[DomainEventPublisher] = None
    ):
        """
        Initialize the user service.

        Args:
            user_repository: Repository for user data access
            event_publisher: Optional publisher for domain events
        """
        self._user_repository = user_repository
        self._event_publisher = event_publisher

    def _normalize_username(self, username: str) -> str:
        """
        Normalize a username by converting to lowercase and stripping whitespace.

        Args:
            username: The username to normalize

        Returns:
            The normalized username
        """
        if username is None:
            return None
        return username.lower().strip()

    def create_user(
        self, 
        username: str, 
        password: str, 
        email: Optional[str] = None,
        roles: List[str] = None,
        is_active: bool = True
    ) -> User:
        """
        Create a new user.

        Args:
            username: The username for the new user
            password: The password for the new user
            email: Optional email address for the new user
            roles: Optional list of roles to assign to the user
            is_active: Whether the user should be active initially

        Returns:
            The created user entity

        Raises:
            ValueError: If the username already exists or the password is invalid
        """
        # Validate username
        if self._user_repository.username_exists(username):
            raise ValueError(f"Username '{username}' already exists")

        # Validate email if provided
        if email and self._user_repository.email_exists(email):
            raise ValueError(f"Email '{email}' already exists")

        # Create user entity
        user = User(
            username=username,
            email=email,
            is_active=is_active
        )

        # Set password
        user.set_password(password)

        # Add roles
        if roles:
            for role in roles:
                user.add_role(role)

        # Save to repository
        saved_user = self._user_repository.add(user)

        # Publish domain events if available
        if self._event_publisher and saved_user.domain_events:
            for event in saved_user.domain_events:
                self._event_publisher.publish(event)
            saved_user.clear_domain_events()

        return saved_user

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username and password.

        Args:
            username: The username to authenticate
            password: The password to verify

        Returns:
            The authenticated user if successful, None otherwise
        """
        normalized_username = self._normalize_username(username)
        user = self._user_repository.get_by_username(normalized_username)

        if not user or not user.is_active:
            return None

        if not user.verify_password(password):
            return None

        # Update last login time
        self._user_repository.update_last_login(user.id)

        return user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get a user by ID.

        Args:
            user_id: The ID of the user to retrieve

        Returns:
            The user if found, None otherwise
        """
        return self._user_repository.get_by_id(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by username.

        Args:
            username: The username of the user to retrieve

        Returns:
            The user if found, None otherwise
        """
        normalized_username = self._normalize_username(username)
        return self._user_repository.get_by_username(normalized_username)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email address.

        Args:
            email: The email address of the user to retrieve

        Returns:
            The user if found, None otherwise
        """
        return self._user_repository.get_by_email(email)

    def get_all_users(self) -> List[User]:
        """
        Get all users.

        Returns:
            A list of all users
        """
        return self._user_repository.list_all()

    def get_users_by_role(self, role_name: str) -> List[User]:
        """
        Get all users with a specific role.

        Args:
            role_name: The name of the role to filter by

        Returns:
            A list of users with the specified role
        """
        return self._user_repository.get_users_by_role(role_name)

    def update_user(self, user: User) -> User:
        """
        Update a user.

        Args:
            user: The user entity with updated values

        Returns:
            The updated user entity

        Raises:
            ValueError: If the user doesn't exist
        """
        # Check if user exists
        existing_user = self._user_repository.get_by_id(user.id)
        if not existing_user:
            raise ValueError(f"User with ID {user.id} not found")

        # Update user
        updated_user = self._user_repository.update(user)

        # Publish domain events if available
        if self._event_publisher and updated_user.domain_events:
            for event in updated_user.domain_events:
                self._event_publisher.publish(event)
            updated_user.clear_domain_events()

        return updated_user

    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """
        Change a user's password.

        Args:
            user_id: The ID of the user
            current_password: The current password for verification
            new_password: The new password to set

        Returns:
            True if the password was changed successfully, False otherwise

        Raises:
            ValueError: If the current password is incorrect or the new password is invalid
        """
        user = self._user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Verify current password
        if not user.verify_password(current_password):
            raise ValueError("Current password is incorrect")

        # Set new password
        user.set_password(new_password)

        # Update user
        self._user_repository.update(user)

        return True

    def add_role_to_user(self, user_id: int, role_name: str) -> bool:
        """
        Add a role to a user.

        Args:
            user_id: The ID of the user
            role_name: The name of the role to add

        Returns:
            True if the role was added successfully, False otherwise
        """
        return self._user_repository.add_role(user_id, role_name)

    def remove_role_from_user(self, user_id: int, role_name: str) -> bool:
        """
        Remove a role from a user.

        Args:
            user_id: The ID of the user
            role_name: The name of the role to remove

        Returns:
            True if the role was removed successfully, False otherwise
        """
        return self._user_repository.remove_role(user_id, role_name)

    def activate_user(self, user_id: int) -> bool:
        """
        Activate a user account.

        Args:
            user_id: The ID of the user to activate

        Returns:
            True if the activation was successful, False otherwise
        """
        return self._user_repository.activate_user(user_id)

    def deactivate_user(self, user_id: int) -> bool:
        """
        Deactivate a user account.

        Args:
            user_id: The ID of the user to deactivate

        Returns:
            True if the deactivation was successful, False otherwise
        """
        return self._user_repository.deactivate_user(user_id)

    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user.

        Args:
            user_id: The ID of the user to delete

        Returns:
            True if the user was deleted successfully, False otherwise
        """
        return self._user_repository.delete(user_id)
