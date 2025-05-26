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
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError


class SqlAlchemyUserRepository(BaseSqlAlchemyRepository[User, UserModel], UserRepositoryInterface):
    """
    SQLAlchemy implementation of the user repository interface.
    """
    
    def __init__(self, session: Session):
        """Initialize with SQLAlchemy session."""
        super().__init__(session, UserModel, User)
    
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
            raise RepositoryError(f"Database error: {str(e)}")
        except Exception as e:
            self._session.rollback()
            raise RepositoryError(f"Repository error: {str(e)}")
    
    def get_by_username(self, username: str) -> Optional[User]:
        """
        Retrieve a user by their username.
        
        Args:
            username: The username of the user to retrieve.
            
        Returns:
            The user if found, None otherwise.
        """
        model = self._session.query(UserModel).filter(UserModel.username == username).first()
        if model is None:
            return None
        return self._to_domain(model)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by their email address.
        
        Args:
            email: The email address of the user to retrieve.
            
        Returns:
            The user if found, None otherwise.
        """
        model = self._session.query(UserModel).filter(UserModel.email == email).first()
        if model is None:
            return None
        return self._to_domain(model)
    
    def username_exists(self, username: str) -> bool:
        """
        Check if a username already exists.
        
        Args:
            username: The username to check.
            
        Returns:
            True if the username exists, False otherwise.
        """
        return self._session.query(UserModel).filter(UserModel.username == username).first() is not None
    
    def email_exists(self, email: str) -> bool:
        """
        Check if an email address already exists.
        
        Args:
            email: The email address to check.
            
        Returns:
            True if the email exists, False otherwise.
        """
        return self._session.query(UserModel).filter(UserModel.email == email).first() is not None
    
    def update_last_login(self, user_id: int) -> bool:
        """
        Update the last login timestamp for a user.
        
        Args:
            user_id: The ID of the user to update.
            
        Returns:
            True if the update was successful, False otherwise.
        """
        try:
            with self.session_scope() as session:
                user = session.query(UserModel).get(user_id)
                if user is None:
                    return False
                
                user.last_login = datetime.utcnow()
                return True
        except RepositoryError:
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
        try:
            with self.session_scope() as session:
                user = session.query(UserModel).get(user_id)
                if user is None:
                    return False
                
                role = session.query(RoleModel).filter(RoleModel.name == role_name).first()
                if role is None:
                    # Create the role if it doesn't exist
                    role = RoleModel(name=role_name)
                    session.add(role)
                    session.flush()
                
                if role not in user.roles:
                    user.roles.append(role)
                
                return True
        except RepositoryError:
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
        try:
            with self.session_scope() as session:
                user = session.query(UserModel).get(user_id)
                if user is None:
                    return False
                
                role = session.query(RoleModel).filter(RoleModel.name == role_name).first()
                if role is None or role not in user.roles:
                    return False
                
                user.roles.remove(role)
                return True
        except RepositoryError:
            return False
    
    def get_users_by_role(self, role_name: str) -> List[User]:
        """
        Get all users with a specific role.
        
        Args:
            role_name: The name of the role to filter by.
            
        Returns:
            A list of users with the specified role.
        """
        try:
            role = self._session.query(RoleModel).filter(RoleModel.name == role_name).first()
            if role is None:
                return []
            
            users = self._session.query(UserModel).filter(UserModel.roles.contains(role)).all()
            return [self._to_domain(user) for user in users]
        except SQLAlchemyError:
            return []
    
    def activate_user(self, user_id: int) -> bool:
        """
        Activate a user account.
        
        Args:
            user_id: The ID of the user to activate.
            
        Returns:
            True if the activation was successful, False otherwise.
        """
        try:
            with self.session_scope() as session:
                user = session.query(UserModel).get(user_id)
                if user is None:
                    return False
                
                user.is_active = True
                return True
        except RepositoryError:
            return False
    
    def deactivate_user(self, user_id: int) -> bool:
        """
        Deactivate a user account.
        
        Args:
            user_id: The ID of the user to deactivate.
            
        Returns:
            True if the deactivation was successful, False otherwise.
        """
        try:
            with self.session_scope() as session:
                user = session.query(UserModel).get(user_id)
                if user is None:
                    return False
                
                user.is_active = False
                return True
        except RepositoryError:
            return False
    
    def _to_domain(self, model: UserModel) -> User:
        """
        Convert a SQLAlchemy model to a domain entity.
        
        Args:
            model: The SQLAlchemy model to convert.
            
        Returns:
            The domain entity.
        """
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
        for role in model.roles:
            user._roles.append(role.name)
        
        return user
    
    def _to_model(self, entity: User) -> UserModel:
        """
        Convert a domain entity to a SQLAlchemy model.
        
        Args:
            entity: The domain entity to convert.
            
        Returns:
            The SQLAlchemy model.
        """
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
        
        return model
    
    def _update_model(self, model: UserModel, entity: User) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.
        
        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        model.username = entity.username
        model.email = entity.email
        model.password_hash = entity._password_hash
        model.is_active = entity.is_active
        model.updated_at = datetime.utcnow()
        model.last_login = entity.last_login
        
        # Update roles
        model.roles = []
        for role_name in entity.roles:
            role = self._session.query(RoleModel).filter(RoleModel.name == role_name).first()
            if role is None:
                role = RoleModel(name=role_name)
                self._session.add(role)
                self._session.flush()
            
            model.roles.append(role)