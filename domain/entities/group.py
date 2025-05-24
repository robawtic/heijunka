# heijunka/domain/entities/group.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import date

from domain.events import (
    DomainEvent, GroupCreated, GroupUpdated, 
    GroupPropertyChanged, GroupDepartmentChanged
)

if TYPE_CHECKING:
    from domain.entities.department import Department


@dataclass
class Group:
    """
    Group aggregate root entity.

    Represents a group in the organization structure.
    """
    id: int
    name: str
    department_id: Optional[int] = None
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Initialize collections if they are None."""
        if self._domain_events is None:
            self._domain_events = []

        # Register creation event
        if self.id > 0:  # Only register if this is a real entity (not a placeholder)
            self.register_domain_event(GroupCreated(
                group_id=self.id,
                name=self.name,
                department_id=self.department_id
            ))

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

    def set_name(self, new_name: str) -> bool:
        """
        Set the name of the group.

        Args:
            new_name: The new name.

        Returns:
            True if the name was changed, False if it's the same.

        Raises:
            ValueError: If the new name is invalid.
        """
        if not isinstance(new_name, str) or not new_name:
            raise ValueError("Name must be a non-empty string")

        if self.name == new_name:
            return False

        old_name = self.name
        self.name = new_name

        self.register_domain_event(GroupPropertyChanged(
            group_id=self.id,
            property_name="name",
            old_value=old_name,
            new_value=new_name
        ))

        return True

    def set_department(self, new_department_id: Optional[int]) -> bool:
        """
        Set the department of the group.

        Args:
            new_department_id: The ID of the new department, or None to unassign.

        Returns:
            True if the department was changed, False if it's the same.

        Raises:
            ValueError: If the new department ID is invalid.
        """
        if new_department_id is not None and (not isinstance(new_department_id, int) or new_department_id <= 0):
            raise ValueError("Department ID must be a positive integer or None")

        if self.department_id == new_department_id:
            return False

        old_department_id = self.department_id
        self.department_id = new_department_id

        self.register_domain_event(GroupDepartmentChanged(
            group_id=self.id,
            old_department_id=old_department_id,
            new_department_id=new_department_id
        ))

        return True

    def update(self, name: Optional[str] = None, department_id: Optional[int] = None) -> None:
        """
        Update multiple properties of the group at once.

        Args:
            name: The new name (if provided).
            department_id: The new department ID (if provided).

        Raises:
            ValueError: If any of the provided values are invalid.
        """
        updated = False

        if name is not None:
            updated = self.set_name(name) or updated

        if department_id is not None:
            updated = self.set_department(department_id) or updated

        if updated:
            self.register_domain_event(GroupUpdated(group_id=self.id))

    def validate(self) -> None:
        """
        Validates the group entity.
        Raises ValueError if validation fails.
        """
        if not self.name:
            raise ValueError("Group name cannot be empty")
        if len(self.name) > 100:  # Example validation rule
            raise ValueError("Group name cannot be longer than 100 characters")
        if self.department_id is not None and (not isinstance(self.department_id, int) or self.department_id <= 0):
            raise ValueError("Department ID must be a positive integer or None")
