from dataclasses import dataclass
from typing import Optional, Any
from .base import DomainEvent

@dataclass
class GroupCreated(DomainEvent):
    """Event raised when a new group is created"""
    group_id: int
    name: str
    department_id: Optional[int]

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.group_id, int) or self.group_id <= 0:
            raise ValueError("group_id must be a positive integer")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")
        if self.department_id is not None and (not isinstance(self.department_id, int) or self.department_id <= 0):
            raise ValueError("department_id must be a positive integer or None")

@dataclass
class GroupUpdated(DomainEvent):
    """Event raised when a group is updated"""
    group_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.group_id, int) or self.group_id <= 0:
            raise ValueError("group_id must be a positive integer")

@dataclass
class GroupPropertyChanged(DomainEvent):
    """Event raised when a group property is changed"""
    group_id: int
    property_name: str
    old_value: Any
    new_value: Any

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.group_id, int) or self.group_id <= 0:
            raise ValueError("group_id must be a positive integer")
        if not isinstance(self.property_name, str) or not self.property_name:
            raise ValueError("property_name must be a non-empty string")

@dataclass
class GroupDepartmentChanged(DomainEvent):
    """Event raised when a group's department is changed"""
    group_id: int
    old_department_id: Optional[int]
    new_department_id: Optional[int]

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.group_id, int) or self.group_id <= 0:
            raise ValueError("group_id must be a positive integer")
        if self.old_department_id is not None and (not isinstance(self.old_department_id, int) or self.old_department_id <= 0):
            raise ValueError("old_department_id must be a positive integer or None")
        if self.new_department_id is not None and (not isinstance(self.new_department_id, int) or self.new_department_id <= 0):
            raise ValueError("new_department_id must be a positive integer or None")