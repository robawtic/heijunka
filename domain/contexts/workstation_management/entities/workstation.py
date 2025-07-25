# heijunka/domain/contexts/workstation_management/entities/workstation.py

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from domain.events import (
    DomainEvent,
    WorkstationCreated,
    WorkstationUpdated,
    WorkstationPropertyChanged,
    WorkstationLineTypeChanged,
    WorkstationTeamChanged
)

@dataclass
class Workstation:
    """
    Aggregate root for a physical workstation.
    All boolean‐style “flags” now live in the _attributes list.
    """
    id: Optional[int]       = None
    name: str               = ""
    line_type: str          = ""
    team_id: Optional[int]  = None

    # replaces all the old boolean columns
    _attributes: List[str] = field(default_factory=list, repr=False)

    # domain events
    _domain_events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        # fire a creation event if this is a new aggregate
        if self.id is not None:
            self.register_domain_event(WorkstationCreated(
                workstation_id=self.id,
                name=self.name,
                line_type=self.line_type
            ))

    @property
    def domain_events(self) -> List[DomainEvent]:
        return list(self._domain_events)

    def clear_domain_events(self) -> None:
        self._domain_events.clear()

    def register_domain_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    #
    # --- attribute helpers ---
    #

    @property
    def attributes(self) -> List[str]:
        """Read-only view of the current attributes."""
        return list(self._attributes)

    def has_attribute(self, attr_name: str) -> bool:
        return attr_name in self._attributes

    @property
    def is_loading(self) -> bool:
        return self.has_attribute("loading")

    @property
    def is_heavy(self) -> bool:
        return self.has_attribute("heavy")

    @property
    def requires_key_skill(self) -> bool:
        # depending on your logic you might check any 'skill_level_*'
        return any(a.startswith("skill_level_") for a in self._attributes)

    def add_attribute(self, attr_name: str) -> bool:
        """
        Add one attribute (e.g. 'loading', 'heavy', 'skill_level_2').
        Returns True if changed.
        """
        if attr_name in self._attributes:
            return False

        old = list(self._attributes)
        self._attributes.append(attr_name)
        # fire a single event for the attribute change
        self.register_domain_event(WorkstationPropertyChanged(
            workstation_id=self.id,
            property_name="attributes",
            old_value=old,
            new_value=list(self._attributes)
        ))
        return True

    def remove_attribute(self, attr_name: str) -> bool:
        """
        Remove one attribute. Returns True if changed.
        """
        if attr_name not in self._attributes:
            return False

        old = list(self._attributes)
        self._attributes.remove(attr_name)
        self.register_domain_event(WorkstationPropertyChanged(
            workstation_id=self.id,
            property_name="attributes",
            old_value=old,
            new_value=list(self._attributes)
        ))
        return True

    def change_attributes(self, new_attrs: List[str]) -> bool:
        """
        Replace the entire attribute set. Returns True if any difference.
        """
        old = list(self._attributes)
        if old == new_attrs:
            return False
        self._attributes = list(new_attrs)
        self.register_domain_event(WorkstationPropertyChanged(
            workstation_id=self.id,
            property_name="attributes",
            old_value=old,
            new_value=list(self._attributes)
        ))
        return True

    #
    # --- other setters remain mostly the same ---
    #

    def set_line_type(self, new_line_type: str) -> bool:
        if not new_line_type or not isinstance(new_line_type, str):
            raise ValueError("line_type must be a non-empty string")
        if self.line_type == new_line_type:
            return False
        old = self.line_type
        self.line_type = new_line_type
        self.register_domain_event(WorkstationLineTypeChanged(
            workstation_id=self.id,
            old_line_type=old,
            new_line_type=new_line_type
        ))
        return True

    def set_team(self, new_team_id: Optional[int]) -> bool:
        if new_team_id is not None and not isinstance(new_team_id, int):
            raise ValueError("team_id must be an integer or None")
        if self.team_id == new_team_id:
            return False
        old = self.team_id
        self.team_id = new_team_id
        self.register_domain_event(WorkstationTeamChanged(
            workstation_id=self.id,
            old_team_id=old,
            new_team_id=new_team_id
        ))
        return True

    def set_name(self, new_name: str) -> bool:
        if not new_name or not isinstance(new_name, str):
            raise ValueError("name must be a non-empty string")
        if self.name == new_name:
            return False
        old = self.name
        self.name = new_name
        self.register_domain_event(WorkstationPropertyChanged(
            workstation_id=self.id,
            property_name="name",
            old_value=old,
            new_value=new_name
        ))
        return True

    def update(
        self,
        *,
        name: Optional[str]             = None,
        line_type: Optional[str]        = None,
        attributes: Optional[List[str]] = None,
        team_id: Optional[int]          = None
    ) -> bool:
        """
        Bulk‐update multiple fields in one shot.
        """
        changed = False
        if name is not None:
            changed |= self.set_name(name)
        if line_type is not None:
            changed |= self.set_line_type(line_type)
        if attributes is not None:
            changed |= self.change_attributes(attributes)
        if team_id is not None:
            changed |= self.set_team(team_id)

        if changed:
            self.register_domain_event(WorkstationUpdated(workstation_id=self.id))
        return changed

    def validate(self) -> Dict[str, Any]:
        errors = []
        if not self.name:
            errors.append("Name is required")
        if not self.line_type:
            errors.append("Line type is required")
        return {"is_valid": not errors, "errors": errors}
