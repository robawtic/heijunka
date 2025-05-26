from sqlalchemy import Column, Integer, String, Boolean, Table, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import List, Optional
import bcrypt
from datetime import datetime

from domain.models.Base import Base
from domain.models.RoleModel import RoleModel

# Association table for many-to-many relationship between users and roles
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)

class UserModel(Base):
    """
    SQLAlchemy ORM model for User entity.
    
    This model represents the database structure for users and handles the persistence
    of User entities. It should not contain domain logic, only persistence-related code.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)
    password_hash = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)

    # Relationships
    roles = relationship('RoleModel', secondary=user_roles, backref='users')

    def __repr__(self):
        return f"<UserModel(id={self.id}, username={self.username})>"