from dataclasses import dataclass
from typing import Optional, List
from .base import DomainEvent

@dataclass
class TeamMemberAdded(DomainEvent):
    """Event raised when a member is added to a team"""
    team_id: int
    employee_id: int
    roles: List[str]

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.team_id, int) or self.team_id <= 0:
            raise ValueError("team_id must be a positive integer")
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.roles, list):
            raise ValueError("roles must be a list")
        if not all(isinstance(role, str) and role for role in self.roles):
            raise ValueError("All roles must be non-empty strings")

@dataclass
class TeamMemberRemoved(DomainEvent):
    """Event raised when a member is removed from a team"""
    team_id: int
    employee_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.team_id, int) or self.team_id <= 0:
            raise ValueError("team_id must be a positive integer")
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")

@dataclass
class WorkstationAddedToTeam(DomainEvent):
    """Event raised when a workstation is added to a team"""
    team_id: int
    workstation_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.team_id, int) or self.team_id <= 0:
            raise ValueError("team_id must be a positive integer")
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")

@dataclass
class WorkstationRemovedFromTeam(DomainEvent):
    """Event raised when a workstation is removed from a team"""
    team_id: int
    workstation_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.team_id, int) or self.team_id <= 0:
            raise ValueError("team_id must be a positive integer")
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")