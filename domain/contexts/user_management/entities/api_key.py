# heijunka/domain/contexts/user_management/entities/api_key.py
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
import uuid
import secrets
import ipaddress

from domain.events import DomainEvent

@dataclass
class ApiKey:
    """
    ApiKey entity representing an API key for authentication.

    This entity stores information about API keys, including the key ID,
    user ID, name, and expiration time.
    """
    id: Optional[int] = None
    key_id: str = ""  # UUID for the key
    key_value: str = ""  # The actual API key value
    user_id: int = 0
    name: str = ""  # A name for the API key (e.g., "Mobile App")
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    scopes: List[str] = field(default_factory=list)  # Permissions for this key
    allowed_ips: List[str] = field(default_factory=list)  # List of allowed IP addresses
    allowed_user_agents: List[str] = field(default_factory=list)  # List of allowed user agents
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Initialize collections and timestamps if they are None."""
        if self._domain_events is None:
            self._domain_events = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        if not self.key_id:
            self.key_id = str(uuid.uuid4())
        if not self.key_value:
            self.key_value = self._generate_key()

    @staticmethod
    def _generate_key():
        """Generate a secure API key."""
        return secrets.token_urlsafe(32)

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

    def deactivate(self) -> None:
        """Deactivate the API key."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate the API key."""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def is_expired(self) -> bool:
        """Check if the API key is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if the API key is valid (active and not expired)."""
        return self.is_active and not self.is_expired()

    def validate_ip(self, ip_address: str) -> bool:
        """
        Check if the given IP address is allowed for this API key.

        Args:
            ip_address: The IP address to check

        Returns:
            bool: True if the IP address is allowed, False otherwise
        """
        # If no IP restrictions, allow all
        if not self.allowed_ips:
            return True

        # Check if the IP is in the allowed list
        return ip_address in self.allowed_ips

    def validate_user_agent(self, user_agent: str) -> bool:
        """
        Check if the given user agent is allowed for this API key.

        Args:
            user_agent: The user agent to check

        Returns:
            bool: True if the user agent is allowed, False otherwise
        """
        # If no user agent restrictions, allow all
        if not self.allowed_user_agents:
            return True

        # Check if any allowed user agent is a substring of the given user agent
        for allowed_agent in self.allowed_user_agents:
            if allowed_agent in user_agent:
                return True

        return False

    def has_scope(self, scope: str) -> bool:
        """
        Check if the API key has the given scope.

        Args:
            scope: The scope to check

        Returns:
            bool: True if the API key has the scope, False otherwise
        """
        # If no scopes defined, allow all
        if not self.scopes:
            return True

        return scope in self.scopes

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, key_id={self.key_id}, name={self.name}, user_id={self.user_id})>"