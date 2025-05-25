from dataclasses import dataclass
from typing import Optional, Any
from .base import DomainEvent

@dataclass
class WorkstationCreated(DomainEvent):
    """Event raised when a new workstation is created"""
    workstation_id: int
    name: str
    line_type: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")
        if not isinstance(self.line_type, str):
            raise ValueError("line_type must be a string")

@dataclass
class WorkstationUpdated(DomainEvent):
    """Event raised when a workstation is updated"""
    workstation_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")

@dataclass
class WorkstationPropertyChanged(DomainEvent):
    """Event raised when a workstation property is changed"""
    workstation_id: int
    property_name: str
    old_value: Any
    new_value: Any

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.property_name, str) or not self.property_name:
            raise ValueError("property_name must be a non-empty string")

@dataclass
class WorkstationLineTypeChanged(DomainEvent):
    """Event raised when a workstation's line type is changed"""
    workstation_id: int
    old_line_type: str
    new_line_type: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.old_line_type, str):
            raise ValueError("old_line_type must be a string")
        if not isinstance(self.new_line_type, str) or not self.new_line_type:
            raise ValueError("new_line_type must be a non-empty string")

@dataclass
class WorkstationTeamChanged(DomainEvent):
    """Event raised when a workstation's team is changed"""
    workstation_id: int
    old_team_id: Optional[int]
    new_team_id: Optional[int]

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if self.old_team_id is not None and (not isinstance(self.old_team_id, int) or self.old_team_id <= 0):
            raise ValueError("old_team_id must be a positive integer or None")
        if self.new_team_id is not None and (not isinstance(self.new_team_id, int) or self.new_team_id <= 0):
            raise ValueError("new_team_id must be a positive integer or None")