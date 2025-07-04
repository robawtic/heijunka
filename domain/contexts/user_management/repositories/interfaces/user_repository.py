from abc import abstractmethod
from typing import Optional, List
from datetime import datetime

from domain.contexts.user_management.entities.user import User
from domain.repositories.interfaces.base_repository import BaseRepository


class UserRepositoryInterface(BaseRepository[User]):
    """
    Interface for user repository operations.
    """

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        """
        Retrieve a user by their username.

        Args:
            username: The username of the user to retrieve.

        Returns:
            The user if found, None otherwise.
        """
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by their email address.

        Args:
            email: The email address of the user to retrieve.

        Returns:
            The user if found, None otherwise.
        """
        pass

    @abstractmethod
    def username_exists(self, username: str) -> bool:
        """
        Check if a username already exists.

        Args:
            username: The username to check.

        Returns:
            True if the username exists, False otherwise.
        """
        pass

    @abstractmethod
    def email_exists(self, email: str) -> bool:
        """
        Check if an email address already exists.

        Args:
            email: The email address to check.

        Returns:
            True if the email exists, False otherwise.
        """
        pass

    @abstractmethod
    def update_last_login(self, user_id: int, ip_address: str = None, user_agent: str = None) -> bool:
        """
        Update the last login timestamp for a user.

        Args:
            user_id: The ID of the user to update.
            ip_address: Optional IP address of the client making the request
            user_agent: Optional user agent of the client making the request

        Returns:
            True if the update was successful, False otherwise.
        """
        pass

    @abstractmethod
    def add_role(self, user_id: int, role_name: str) -> bool:
        """
        Add a role to a user.

        Args:
            user_id: The ID of the user.
            role_name: The name of the role to add.

        Returns:
            True if the role was added successfully, False otherwise.
        """
        pass

    @abstractmethod
    def remove_role(self, user_id: int, role_name: str) -> bool:
        """
        Remove a role from a user.

        Args:
            user_id: The ID of the user.
            role_name: The name of the role to remove.

        Returns:
            True if the role was removed successfully, False otherwise.
        """
        pass

    @abstractmethod
    def get_users_by_role(self, role_name: str) -> List[User]:
        """
        Get all users with a specific role.

        Args:
            role_name: The name of the role to filter by.

        Returns:
            A list of users with the specified role.
        """
        pass

    @abstractmethod
    def activate_user(self, user_id: int) -> bool:
        """
        Activate a user account.

        Args:
            user_id: The ID of the user to activate.

        Returns:
            True if the activation was successful, False otherwise.
        """
        pass

    @abstractmethod
    def deactivate_user(self, user_id: int) -> bool:
        """
        Deactivate a user account.

        Args:
            user_id: The ID of the user to deactivate.

        Returns:
            True if the deactivation was successful, False otherwise.
        """
        pass