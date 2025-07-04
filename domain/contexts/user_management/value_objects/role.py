# heijunka/domain/contexts/user_management/value_objects/role.py
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

from domain.events import DomainEvent

@dataclass
class Role:
    """
    Role value object representing a system role for authorization and business logic.
    
    Roles define what actions users can perform within the system and can also
    carry business logic significance beyond simple authorization.
    """
    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)
    
    def __post_init__(self):
        """Initialize collections if they are None."""
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
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"