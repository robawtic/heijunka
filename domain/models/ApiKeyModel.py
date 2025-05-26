from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Optional
import json

from domain.models.Base import Base
from domain.models.UserModel import UserModel

class ApiKeyModel(Base):
    """
    SQLAlchemy ORM model for ApiKey entity.

    This model represents the database structure for API keys and handles the persistence
    of ApiKey entities. It should not contain domain logic, only persistence-related code.
    """
    __tablename__ = 'api_keys'

    id = Column(Integer, primary_key=True)
    key_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID for the key
    key_value = Column(String(64), unique=True, nullable=False, index=True)  # The actual API key value
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # A name for the API key (e.g., "Mobile App")
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_used_at = Column(DateTime, nullable=True)

    # Store lists as JSON for database compatibility
    # Using JSON instead of ARRAY for better compatibility across different database backends
    scopes = Column(JSON, nullable=True, default=lambda: json.dumps([]))
    allowed_ips = Column(JSON, nullable=True, default=lambda: json.dumps([]))
    allowed_user_agents = Column(JSON, nullable=True, default=lambda: json.dumps([]))

    # Relationships
    user = relationship('UserModel', backref='api_keys')

    def __repr__(self):
        return f"<ApiKeyModel(id={self.id}, key_id={self.key_id}, name={self.name}, user_id={self.user_id})>"
