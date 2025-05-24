# heijunka/domain/entities/workstation.py
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
    id: int
    name: str
    line_type: str
    is_loading_job: bool = False
    is_heavy_job: bool = False
    is_key_skill_job: bool = False
    team_id: Optional[int] = None
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Initialize collections if they are None."""
        if self._domain_events is None:
            self._domain_events = []

        # Register creation event
        if self.id > 0:  # Only register if this is a real entity (not a placeholder)
            self.register_domain_event(WorkstationCreated(
                workstation_id=self.id,
                name=self.name,
                line_type=self.line_type
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

    def is_heavy(self) -> bool:
        """Returns True if this workstation is a heavy job."""
        return self.is_heavy_job

    def is_loading(self) -> bool:
        """Returns True if this workstation is a loading job."""
        return self.is_loading_job

    def requires_key_skill(self) -> bool:
        """Returns True if this workstation requires key skill."""
        return self.is_key_skill_job

    def set_line_type(self, new_line_type: str) -> bool:
        """
        Change the line type of the workstation.

        Args:
            new_line_type: The new line type

        Returns:
            True if the line type was changed, False if it's the same

        Raises:
            ValueError: If the new line type is invalid
        """
        if not isinstance(new_line_type, str) or not new_line_type:
            raise ValueError("Line type must be a non-empty string")

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
        Assign the workstation to a team.

        Args:
            new_team_id: The ID of the new team, or None to unassign

        Returns:
            True if the team was changed, False if it's the same

        Raises:
            ValueError: If the new team ID is invalid
        """
        if new_team_id is not None and (not isinstance(new_team_id, int) or new_team_id <= 0):
            raise ValueError("Team ID must be a positive integer or None")

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
        Set whether this workstation is a loading job.

        Args:
            is_loading: True if this is a loading job, False otherwise

        Returns:
            True if the value was changed, False if it's the same
        """
        if self.is_loading_job == is_loading:
            return False

        old_value = self.is_loading_job
        self.is_loading_job = is_loading

        self.register_domain_event(WorkstationPropertyChanged(
            workstation_id=self.id,
            property_name="is_loading_job",
            old_value=old_value,
            new_value=is_loading
        ))

        return True

    def set_heavy_job(self, is_heavy: bool) -> bool:
        """
        Set whether this workstation is a heavy job.

        Args:
            is_heavy: True if this is a heavy job, False otherwise

        Returns:
            True if the value was changed, False if it's the same
        """
        if self.is_heavy_job == is_heavy:
            return False

        old_value = self.is_heavy_job
        self.is_heavy_job = is_heavy

        self.register_domain_event(WorkstationPropertyChanged(
            workstation_id=self.id,
            property_name="is_heavy_job",
            old_value=old_value,
            new_value=is_heavy
        ))

        return True

    def set_key_skill_job(self, requires_key_skill: bool) -> bool:
        """
        Set whether this workstation requires key skill.

        Args:
            requires_key_skill: True if this requires key skill, False otherwise

        Returns:
            True if the value was changed, False if it's the same
        """
        if self.is_key_skill_job == requires_key_skill:
            return False

        old_value = self.is_key_skill_job
        self.is_key_skill_job = requires_key_skill

        self.register_domain_event(WorkstationPropertyChanged(
            workstation_id=self.id,
            property_name="is_key_skill_job",
            old_value=old_value,
            new_value=requires_key_skill
        ))

        return True

    def set_name(self, new_name: str) -> bool:
        """
        Set the name of the workstation.

        Args:
            new_name: The new name

        Returns:
            True if the name was changed, False if it's the same

        Raises:
            ValueError: If the new name is invalid
        """
        if not isinstance(new_name, str) or not new_name:
            raise ValueError("Name must be a non-empty string")

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

    def update(self, 
               name: Optional[str] = None,
               line_type: Optional[str] = None,
               is_loading_job: Optional[bool] = None,
               is_heavy_job: Optional[bool] = None,
               is_key_skill_job: Optional[bool] = None,
               team_id: Optional[int] = None) -> None:
        """
        Update multiple properties of the workstation at once.

        Args:
            name: The new name (if provided)
            line_type: The new line type (if provided)
            is_loading_job: Whether this is a loading job (if provided)
            is_heavy_job: Whether this is a heavy job (if provided)
            is_key_skill_job: Whether this requires key skill (if provided)
            team_id: The new team ID (if provided)

        Raises:
            ValueError: If any of the provided values are invalid
        """
        updated = False

        if name is not None:
            updated = self.set_name(name) or updated

        if line_type is not None:
            updated = self.set_line_type(line_type) or updated

        if is_loading_job is not None:
            updated = self.set_loading_job(is_loading_job) or updated

        if is_heavy_job is not None:
            updated = self.set_heavy_job(is_heavy_job) or updated

        if is_key_skill_job is not None:
            updated = self.set_key_skill_job(is_key_skill_job) or updated

        if team_id is not None:
            updated = self.set_team(team_id) or updated

        if updated:
            self.register_domain_event(WorkstationUpdated(workstation_id=self.id))

    def validate(self) -> None:
        """
        Validates the workstation entity.
        Raises ValueError if validation fails.
        """
        if not self.name:
            raise ValueError("Workstation name cannot be empty")
        if len(self.name) > 100:  # Example validation rule
            raise ValueError("Workstation name cannot be longer than 100 characters")
        if not self.line_type:
            raise ValueError("Line type cannot be empty")
