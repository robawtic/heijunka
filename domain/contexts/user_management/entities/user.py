# heijunka/domain/contexts/user_management/entities/user.py
from dataclasses import dataclass, field
from typing import List, Optional, Set, Sequence
from datetime import datetime, timezone
import bcrypt

from domain.events import DomainEvent
from domain.contexts.user_management.value_objects.role import Role

@dataclass
class User:
    """
    User entity representing a system user with authentication capabilities.

    This entity is separate from Employee and represents users who can log into the system.
    Users have roles that determine their permissions in the system.
    """
    id: Optional[int] = None
    username: str = ""
    email: Optional[str] = None
    _password_hash: Optional[str] = field(default=None, repr=False)
    is_active: bool = True
    _roles: List[Role] = field(default_factory=list, repr=False)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_verified: bool = False
    last_login_ip: Optional[str] = None
    verification_token: Optional[str] = None
    verification_token_expires_at: Optional[datetime] = None
    password_reset_token: Optional[str] = None
    password_reset_token_expires_at: Optional[datetime] = None
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Initialize collections if they are None."""
        if self._roles is None:
            self._roles = []
        if self._domain_events is None:
            self._domain_events = []
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)

    @property
    def roles(self) -> List[Role]:
        """Get a copy of the roles list to prevent direct modification."""
        return self._roles.copy()

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

    def set_password(self, plain_password: str) -> None:
        """
        Set the user's password by hashing it with bcrypt.

        Args:
            plain_password: The plain text password to hash
        """
        if not plain_password:
            raise ValueError("Password cannot be empty")

        password_bytes = plain_password.encode('utf-8')
        salt = bcrypt.gensalt()
        self._password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        self.updated_at = datetime.now(timezone.utc)

    def verify_password(self, plain_password: str) -> bool:
        """
        Verify a password against the stored hash.

        Args:
            plain_password: The plain text password to verify

        Returns:
            True if the password matches, False otherwise
        """
        if not plain_password or not self._password_hash:
            return False

        password_bytes = plain_password.encode('utf-8')
        hash_bytes = self._password_hash.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)

    def has_role(self, role_name: str) -> bool:
        """
        Check if the user has a specific role.

        Args:
            role_name: The name of the role to check

        Returns:
            True if the user has the role, False otherwise
        """
        return any(role.name == role_name for role in self._roles)

    def change_roles(self, new_role_names: Sequence[str]) -> None:
        """
        Replace this user’s roles VO with a fresh set built from the given names.
        """
        # 1) Build or reuse Role instances
        existing = {r.name: r for r in self._roles}
        new_roles = []
        for name in new_role_names:
            if name in existing:
                new_roles.append(existing[name])
            else:
                new_roles.append(Role(name=name))
        # 2) Atomically swap in the new list
        self._roles = new_roles
        # 3) Update timestamp
        self.updated_at = datetime.now(timezone.utc)
        # 4) (Optional) Register a domain event to signal the change
        # self.register_domain_event(RolesChanged(self.id, new_role_names))

    def update_last_login(self) -> None:
        """Update the last login timestamp to the current time."""
        self.last_login_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def deactivate(self) -> None:
        """Deactivate the user account."""
        if self.is_active:
            self.is_active = False
            self.updated_at = datetime.now(timezone.utc)
            # Could register a domain event here if needed
            # self.register_domain_event(UserDeactivated(self.id))

    def activate(self) -> None:
        """Activate the user account."""
        if not self.is_active:
            self.is_active = True
            self.updated_at = datetime.now(timezone.utc)
            # Could register a domain event here if needed
            # self.register_domain_event(UserActivated(self.id))

    def update_email(self, new_email: str) -> None:
        """
        Update the user's email address.

        Args:
            new_email: The new email address
        """
        if not new_email:
            raise ValueError("Email cannot be empty")

        self.email = new_email
        self.updated_at = datetime.now(timezone.utc)
        # Could register a domain event here if needed
        # self.register_domain_event(EmailUpdated(self.id, new_email))

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, roles={self._roles})>"
