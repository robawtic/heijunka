# heijunka/domain/contexts/user_management/entities/refresh_token.py
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

from domain.events import DomainEvent

@dataclass
class RefreshToken:
    """
    RefreshToken entity representing a refresh token for authentication.
    
    This entity stores information about refresh tokens, including the token ID,
    user ID, expiration time, device information, and revocation status.
    """
    id: Optional[int] = None
    token_id: str = ""  # UUID for the token
    user_id: int = 0
    expires_at: datetime = field(default_factory=datetime.utcnow)
    is_revoked: bool = False
    device_info: Optional[str] = None  # User agent or device identifier
    ip_address: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Initialize collections and timestamps if they are None."""
        if self._domain_events is None:
            self._domain_events = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

    @property
    def domain_events(self) -> List[DomainEvent]:
        """Get a copy of the domain events list."""
        return self._domain_events.copy()

    def clear_domain_events(self) -> None:
        """Clear all domain events after they've been processed."""
        self._domain_events.clear()

    def register_domain_event(self, event: DomainEvent) -> None:
        """Register a domain event."""
        self._domain_events.append(event)

    def revoke(self) -> None:
        """Revoke the refresh token."""
        self.is_revoked = True
        self.updated_at = datetime.utcnow()
        # Could register a domain event here if needed
        # self.register_domain_event(RefreshTokenRevoked(self.token_id))

    def is_expired(self) -> bool:
        """Check if the refresh token is expired."""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if the refresh token is valid (not revoked and not expired)."""
        return not self.is_revoked and not self.is_expired()

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, token_id={self.token_id}, user_id={self.user_id}, expires_at={self.expires_at}, is_revoked={self.is_revoked})>"