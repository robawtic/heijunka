from dataclasses import dataclass
from typing import Optional, Any
from .base import DomainEvent

@dataclass
class DepartmentCreated(DomainEvent):
    """Event raised when a new department is created"""
    department_id: int
    name: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.department_id, int) or self.department_id <= 0:
            raise ValueError("department_id must be a positive integer")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")

@dataclass
class DepartmentUpdated(DomainEvent):
    """Event raised when a department is updated"""
    department_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.department_id, int) or self.department_id <= 0:
            raise ValueError("department_id must be a positive integer")

@dataclass
class DepartmentPropertyChanged(DomainEvent):
    """Event raised when a department property is changed"""
    department_id: int
    property_name: str
    old_value: Any
    new_value: Any

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.department_id, int) or self.department_id <= 0:
            raise ValueError("department_id must be a positive integer")
        if not isinstance(self.property_name, str) or not self.property_name:
            raise ValueError("property_name must be a non-empty string")

@dataclass
class GroupAddedToDepartment(DomainEvent):
    """Event raised when a group is added to a department"""
    department_id: int
    group_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.department_id, int) or self.department_id <= 0:
            raise ValueError("department_id must be a positive integer")
        if not isinstance(self.group_id, int) or self.group_id <= 0:
            raise ValueError("group_id must be a positive integer")

@dataclass
class GroupRemovedFromDepartment(DomainEvent):
    """Event raised when a group is removed from a department"""
    department_id: int
    group_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.department_id, int) or self.department_id <= 0:
            raise ValueError("department_id must be a positive integer")
        if not isinstance(self.group_id, int) or self.group_id <= 0:
            raise ValueError("group_id must be a positive integer")