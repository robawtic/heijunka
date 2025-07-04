# heijunka/domain/contexts/workstation_management/entities/workstation.py
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from domain.events import (
    DomainEvent, WorkstationCreated, WorkstationUpdated, 
    WorkstationPropertyChanged, WorkstationLineTypeChanged, WorkstationTeamChanged
)

@dataclass
class Workstation:
    """
    Workstation aggregate root entity.
    
    Represents a physical workstation in the manufacturing system.
    """
    id: Optional[int] = None
    name: str = ""
    line_type: str = ""
    is_loading_job: bool = False
    is_heavy_job: bool = False
    is_key_skill_job: bool = False
    team_id: Optional[int] = None
    _domain_events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)
    
    def __post_init__(self):
        """Initialize the workstation and register creation event."""
        if self.id is not None:
            # Only register creation event for new workstations
            self.register_domain_event(WorkstationCreated(
                workstation_id=self.id,
                name=self.name,
                line_type=self.line_type
            ))
    
    @property
    def domain_events(self) -> List[DomainEvent]:
        """Get the list of domain events."""
        return self._domain_events.copy()
    
    def clear_domain_events(self) -> None:
        """Clear all domain events."""
        self._domain_events.clear()
    
    def register_domain_event(self, event: DomainEvent) -> None:
        """Register a domain event."""
        self._domain_events.append(event)
    
    @property
    def is_heavy(self) -> bool:
        """Check if this is a heavy job workstation."""
        return self.is_heavy_job
    
    @property
    def is_loading(self) -> bool:
        """Check if this is a loading job workstation."""
        return self.is_loading_job
    
    @property
    def requires_key_skill(self) -> bool:
        """Check if this workstation requires key skills."""
        return self.is_key_skill_job
    
    def set_line_type(self, new_line_type: str) -> bool:
        """
        Set the line type for this workstation.
        
        Args:
            new_line_type: The new line type
            
        Returns:
            True if the line type was changed, False otherwise
        """
        if not isinstance(new_line_type, str) or not new_line_type:
            raise ValueError("line_type must be a non-empty string")
        
        if self.line_type == new_line_type:
            return False
        
        old_line_type = self.line_type
        self.line_type = new_line_type
        
        self.register_domain_event(WorkstationLineTypeChanged(
            workstation_id=self.id,
            old_line_type=old_line_type,
            new_line_type=new_line_type
        ))
        
        return True
    
    def set_team(self, new_team_id: Optional[int]) -> bool:
        """
        Set the team for this workstation.
        
        Args:
            new_team_id: The new team ID
            
        Returns:
            True if the team was changed, False otherwise
        """
        if new_team_id is not None and not isinstance(new_team_id, int):
            raise ValueError("team_id must be an integer or None")
        
        if self.team_id == new_team_id:
            return False
        
        old_team_id = self.team_id
        self.team_id = new_team_id
        
        self.register_domain_event(WorkstationTeamChanged(
            workstation_id=self.id,
            old_team_id=old_team_id,
            new_team_id=new_team_id
        ))
        
        return True
    
    def set_loading_job(self, is_loading: bool) -> bool:
        """
        Set whether this is a loading job workstation.
        
        Args:
            is_loading: Whether this is a loading job
            
        Returns:
            True if the property was changed, False otherwise
        """
        if not isinstance(is_loading, bool):
            raise ValueError("is_loading must be a boolean")
        
        if self.is_loading_job == is_loading:
            return False
        
        self.is_loading_job = is_loading
        
        self.register_domain_event(WorkstationPropertyChanged(
            workstation_id=self.id,
            property_name="is_loading_job",
            old_value=not is_loading,
            new_value=is_loading
        ))
        
        return True
    
    def set_heavy_job(self, is_heavy: bool) -> bool:
        """
        Set whether this is a heavy job workstation.
        
        Args:
            is_heavy: Whether this is a heavy job
            
        Returns:
            True if the property was changed, False otherwise
        """
        if not isinstance(is_heavy, bool):
            raise ValueError("is_heavy must be a boolean")
        
        if self.is_heavy_job == is_heavy:
            return False
        
        self.is_heavy_job = is_heavy
        
        self.register_domain_event(WorkstationPropertyChanged(
            workstation_id=self.id,
            property_name="is_heavy_job",
            old_value=not is_heavy,
            new_value=is_heavy
        ))
        
        return True
    
    def set_key_skill_job(self, requires_key_skill: bool) -> bool:
        """
        Set whether this workstation requires key skills.
        
        Args:
            requires_key_skill: Whether key skills are required
            
        Returns:
            True if the property was changed, False otherwise
        """
        if not isinstance(requires_key_skill, bool):
            raise ValueError("requires_key_skill must be a boolean")
        
        if self.is_key_skill_job == requires_key_skill:
            return False
        
        self.is_key_skill_job = requires_key_skill
        
        self.register_domain_event(WorkstationPropertyChanged(
            workstation_id=self.id,
            property_name="is_key_skill_job",
            old_value=not requires_key_skill,
            new_value=requires_key_skill
        ))
        
        return True
    
    def set_name(self, new_name: str) -> bool:
        """
        Set the name for this workstation.
        
        Args:
            new_name: The new name
            
        Returns:
            True if the name was changed, False otherwise
        """
        if not isinstance(new_name, str) or not new_name:
            raise ValueError("name must be a non-empty string")
        
        if self.name == new_name:
            return False
        
        old_name = self.name
        self.name = new_name
        
        self.register_domain_event(WorkstationPropertyChanged(
            workstation_id=self.id,
            property_name="name",
            old_value=old_name,
            new_value=new_name
        ))
        
        return True
    
    def update(self, name: Optional[str] = None, line_type: Optional[str] = None,
               is_loading_job: Optional[bool] = None, is_heavy_job: Optional[bool] = None,
               is_key_skill_job: Optional[bool] = None, team_id: Optional[int] = None) -> bool:
        """
        Update multiple properties of the workstation.
        
        Args:
            name: New name (optional)
            line_type: New line type (optional)
            is_loading_job: New loading job status (optional)
            is_heavy_job: New heavy job status (optional)
            is_key_skill_job: New key skill requirement (optional)
            team_id: New team ID (optional)
            
        Returns:
            True if any property was changed, False otherwise
        """
        changed = False
        
        if name is not None:
            changed |= self.set_name(name)
        if line_type is not None:
            changed |= self.set_line_type(line_type)
        if is_loading_job is not None:
            changed |= self.set_loading_job(is_loading_job)
        if is_heavy_job is not None:
            changed |= self.set_heavy_job(is_heavy_job)
        if is_key_skill_job is not None:
            changed |= self.set_key_skill_job(is_key_skill_job)
        if team_id is not None:
            changed |= self.set_team(team_id)
        
        if changed:
            self.register_domain_event(WorkstationUpdated(workstation_id=self.id))
        
        return changed
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate the workstation.
        
        Returns:
            Dictionary containing validation results
        """
        errors = []
        
        if not self.name:
            errors.append("Name is required")
        if not self.line_type:
            errors.append("Line type is required")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }