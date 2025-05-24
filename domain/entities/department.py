# heijunka/domain/entities/department.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import date

from domain.events import (
    DomainEvent, DepartmentCreated, DepartmentUpdated, 
    DepartmentPropertyChanged, GroupAddedToDepartment, GroupRemovedFromDepartment
)

if TYPE_CHECKING:
    from domain.entities.group import Group
else:
    # Import at runtime to avoid circular imports
    import sys
    if 'domain.entities.group' in sys.modules:
        # If already imported, use it
        Group = sys.modules['domain.entities.group'].Group
    else:
        # Placeholder for runtime type checking
        Group = None


@dataclass
class Department:
    """
    Department aggregate root entity.

    Represents a department in the organization structure.
    """
    id: int
    name: str
    description: Optional[str] = None
    _groups: List["Group"] = field(default_factory=list, repr=False)
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Initialize collections if they are None."""
        if self._groups is None:
            self._groups = []
        if self._domain_events is None:
            self._domain_events = []

        # Register creation event
        if self.id > 0:  # Only register if this is a real entity (not a placeholder)
            self.register_domain_event(DepartmentCreated(
                department_id=self.id,
                name=self.name,
                description=self.description
            ))

    @property
    def groups(self) -> List["Group"]:
        """Get a copy of the groups list to prevent direct modification."""
        return self._groups.copy()

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

    def add_group(self, group: "Group") -> bool:
        """
        Add a group to the department.

        Args:
            group: The group to add.

        Returns:
            True if the group was added, False if it was already in the department.

        Raises:
            ValueError: If the group is invalid.
        """
        if not isinstance(group, Group):
            raise ValueError("group must be a Group instance")

        # Check if the group is already in the department
        for existing_group in self._groups:
            if existing_group.id == group.id:
                return False

        # Add the group to the department
        self._groups.append(group)

        # Update the group's department_id
        group.department_id = self.id

        # Register the domain event
        self.register_domain_event(GroupAddedToDepartment(
            department_id=self.id,
            group_id=group.id
        ))

        return True

    def remove_group(self, group_id: int) -> bool:
        """
        Remove a group from the department.

        Args:
            group_id: The ID of the group to remove.

        Returns:
            True if the group was removed, False if it wasn't in the department.
        """
        # Find the group in the department
        for i, group in enumerate(self._groups):
            if group.id == group_id:
                # Remove the group from the department
                removed_group = self._groups.pop(i)

                # Update the group's department_id
                removed_group.department_id = None

                # Register the domain event
                self.register_domain_event(GroupRemovedFromDepartment(
                    department_id=self.id,
                    group_id=group_id
                ))

                return True

        return False

    def get_group_by_id(self, group_id: int) -> Optional["Group"]:
        """
        Get a group by its ID.

        Args:
            group_id: The ID of the group to find.

        Returns:
            The group if found, None otherwise.
        """
        for group in self._groups:
            if group.id == group_id:
                return group
        return None

    def get_group_by_name(self, name: str) -> Optional["Group"]:
        """
        Get a group by its name.

        Args:
            name: The name of the group to find.

        Returns:
            The group if found, None otherwise.
        """
        for group in self._groups:
            if group.name == name:
                return group
        return None

    def set_name(self, new_name: str) -> bool:
        """
        Set the name of the department.

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

        self.register_domain_event(DepartmentPropertyChanged(
            department_id=self.id,
            property_name="name",
            old_value=old_name,
            new_value=new_name
        ))

        return True

    def set_description(self, new_description: Optional[str]) -> bool:
        """
        Set the description of the department.

        Args:
            new_description: The new description, or None to clear it.

        Returns:
            True if the description was changed, False if it's the same.

        Raises:
            ValueError: If the new description is invalid.
        """
        if new_description is not None and not isinstance(new_description, str):
            raise ValueError("Description must be a string or None")

        if self.description == new_description:
            return False

        old_description = self.description
        self.description = new_description

        self.register_domain_event(DepartmentPropertyChanged(
            department_id=self.id,
            property_name="description",
            old_value=old_description,
            new_value=new_description
        ))

        return True

    def update(self, name: Optional[str] = None, description: Optional[str] = None) -> None:
        """
        Update multiple properties of the department at once.

        Args:
            name: The new name (if provided).
            description: The new description (if provided).

        Raises:
            ValueError: If any of the provided values are invalid.
        """
        updated = False

        if name is not None:
            updated = self.set_name(name) or updated

        if description is not None:
            updated = self.set_description(description) or updated

        if updated:
            self.register_domain_event(DepartmentUpdated(department_id=self.id))

    def validate(self) -> None:
        """
        Validates the department entity.
        Raises ValueError if validation fails.
        """
        if not self.name:
            raise ValueError("Department name cannot be empty")
        if len(self.name) > 100:  # Example validation rule
            raise ValueError("Department name cannot be longer than 100 characters")
