from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Optional

from domain.models.Base import Base
from domain.models.UserModel import UserModel

class RefreshTokenModel(Base):
    """
    SQLAlchemy ORM model for RefreshToken entity.
    
    This model represents the database structure for refresh tokens and handles the persistence
    of RefreshToken entities. It should not contain domain logic, only persistence-related code.
    """
    __tablename__ = 'refresh_tokens'

    id = Column(Integer, primary_key=True)
    token_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID for the token
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    device_info = Column(Text, nullable=True)  # User agent or device identifier
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6 address
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship('UserModel', backref='refresh_tokens')

    def __repr__(self):
        return f"<RefreshTokenModel(id={self.id}, token_id={self.token_id}, user_id={self.user_id}, expires_at={self.expires_at}, is_revoked={self.is_revoked})>"