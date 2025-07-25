from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from datetime import date


@dataclass
class WorkstationSeedData:
    """Value object representing seed data for a workstation."""
    name: str
    line_type: str
    is_loading_job: bool
    is_heavy_job: bool
    is_key_skill_job: bool
    description: Optional[str] = None
    cycle_time_minutes: Optional[int] = None
    required_tools: List[str] = field(default_factory=list)
    safety_equipment: List[str] = field(default_factory=list)
    certification_required: bool = False
    training_hours_required: Optional[int] = None
    precision_requirement: Optional[str] = None
    quality_checks: List[str] = field(default_factory=list)
    
    def validate(self) -> bool:
        """Validate the workstation seed data."""
        if not self.name:
            return False
        if not self.line_type:
            return False
        return True


@dataclass
class EmployeeSeedData:
    """Value object representing seed data for an employee."""
    name: str
    role: str
    is_active: bool
    known_stations: List[str] = field(default_factory=list)
    hire_date: Optional[date] = None
    skills: Dict[str, str] = field(default_factory=dict)
    availability_pattern: Dict[str, List[Union[str, date]]] = field(default_factory=dict)
    is_trainer: bool = False
    certifications: List[str] = field(default_factory=list)
    training_progress: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    notes: Optional[str] = None
    
    def validate(self) -> bool:
        """Validate the employee seed data."""
        if not self.name:
            return False
        if not self.role:
            return False
        return True


@dataclass
class TeamSeedData:
    """Value object representing seed data for a team."""
    name: str
    workstations: List[WorkstationSeedData] = field(default_factory=list)
    employees: List[EmployeeSeedData] = field(default_factory=list)
    
    def validate(self) -> bool:
        """Validate the team seed data."""
        if not self.name:
            return False
        for workstation in self.workstations:
            if not workstation.validate():
                return False
        for employee in self.employees:
            if not employee.validate():
                return False
        return True


@dataclass
class GroupSeedData:
    """Value object representing seed data for a group."""
    name: str
    teams: List[TeamSeedData] = field(default_factory=list)
    
    def validate(self) -> bool:
        """Validate the group seed data."""
        if not self.name:
            return False
        for team in self.teams:
            if not team.validate():
                return False
        return True


@dataclass
class DepartmentSeedData:
    """Value object representing seed data for a department."""
    name: str
    groups: List[GroupSeedData] = field(default_factory=list)
    
    def validate(self) -> bool:
        """Validate the department seed data."""
        if not self.name:
            return False
        for group in self.groups:
            if not group.validate():
                return False
        return True