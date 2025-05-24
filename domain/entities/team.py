# heijunka/domain/entities/team.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from domain.entities.team_member import TeamMember
from domain.events import (
    DomainEvent, TeamMemberAdded, TeamMemberRemoved, 
    WorkstationAddedToTeam, WorkstationRemovedFromTeam
)


@dataclass
class Team:
    id: int
    name: str
    description: str = ""
    _members: List["Employee"] = field(default_factory=list, repr=False)
    _workstations: List["Workstation"] = field(default_factory=list, repr=False)
    _team_members: List[TeamMember] = field(default_factory=list, repr=False)
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Initialize collections if they are None."""
        if self._members is None:
            self._members = []
        if self._workstations is None:
            self._workstations = []
        if self._team_members is None:
            self._team_members = []
        if self._domain_events is None:
            self._domain_events = []

    @classmethod
    def create(cls, name: str, description: str = "") -> 'Team':
        """
        Creates a new Team entity.
        Note: This doesn't persist the team - that's the responsibility of the repository.

        Args:
            name: The name of the team
            description: Optional description of the team

        Returns:
            A new Team instance
        """
        # In a real application, you'd probably want to generate the ID
        # through your persistence mechanism
        return cls(
            id=0,  # This should be handled by your persistence layer
            name=name,
            description=description
        )

    @property
    def members(self) -> List["Employee"]:
        """Get a copy of the members list to prevent direct modification."""
        return self._members.copy()

    @property
    def workstations(self) -> List["Workstation"]:
        """Get a copy of the workstations list to prevent direct modification."""
        return self._workstations.copy()

    @property
    def team_members(self) -> List[TeamMember]:
        """Get a copy of the team members list to prevent direct modification."""
        return self._team_members.copy()

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

    def add_member(self, employee: "Employee") -> bool:
        """
        Add an employee to the team.

        Args:
            employee: The employee to add.

        Returns:
            True if the employee was added, False if already a member.
        """
        # Check if the employee is already a member
        for member in self._members:
            if member.id == employee.id:
                return False  # Already a member

        # Add the employee to the team
        self._members.append(employee)

        # Create a new TeamMember entity
        team_member = TeamMember(
            team_member_id=0,  # This should be handled by the repository
            team_id=self.id,
            employee_id=employee.id
        )
        self._team_members.append(team_member)

        # Register the domain event
        self.register_domain_event(TeamMemberAdded(self.id, employee.id))

        return True

    def remove_member(self, employee_id: int) -> bool:
        """
        Remove an employee from the team.

        Args:
            employee_id: The ID of the employee to remove.

        Returns:
            True if the employee was removed, False if not a member.
        """
        # Find the employee in the members list
        for i, member in enumerate(self._members):
            if member.id == employee_id:
                # Remove the employee from the members list
                self._members.pop(i)

                # Remove the corresponding TeamMember entity
                for j, team_member in enumerate(self._team_members):
                    if team_member.employee_id == employee_id:
                        self._team_members.pop(j)
                        break

                # Register the domain event
                self.register_domain_event(TeamMemberRemoved(self.id, employee_id))

                return True

        return False

    def add_workstation(self, workstation: "Workstation") -> bool:
        """
        Add a workstation to the team.

        Args:
            workstation: The workstation to add.

        Returns:
            True if the workstation was added, False if already assigned.
        """
        # Check if the workstation is already assigned to the team
        for ws in self._workstations:
            if ws.id == workstation.id:
                return False  # Already assigned

        # Add the workstation to the team
        self._workstations.append(workstation)

        # Update the workstation's team_id
        workstation.team_id = self.id

        # Register the domain event
        self.register_domain_event(WorkstationAddedToTeam(self.id, workstation.id))

        return True

    def remove_workstation(self, workstation_id: int) -> bool:
        """
        Remove a workstation from the team.

        Args:
            workstation_id: The ID of the workstation to remove.

        Returns:
            True if the workstation was removed, False if not assigned.
        """
        # Find the workstation in the workstations list
        for i, ws in enumerate(self._workstations):
            if ws.id == workstation_id:
                # Remove the workstation from the workstations list
                workstation = self._workstations.pop(i)

                # Update the workstation's team_id
                workstation.team_id = None

                # Register the domain event
                self.register_domain_event(WorkstationRemovedFromTeam(self.id, workstation_id))

                return True

        return False

    def get_member_by_id(self, employee_id: int) -> Optional["Employee"]:
        """
        Get a team member by employee ID.

        Args:
            employee_id: The ID of the employee to find.

        Returns:
            The employee if found, None otherwise.
        """
        for member in self._members:
            if member.id == employee_id:
                return member
        return None

    def get_workstation_by_id(self, workstation_id: int) -> Optional["Workstation"]:
        """
        Get a workstation by ID.

        Args:
            workstation_id: The ID of the workstation to find.

        Returns:
            The workstation if found, None otherwise.
        """
        for ws in self._workstations:
            if ws.id == workstation_id:
                return ws
        return None

    def get_team_member_by_employee_id(self, employee_id: int) -> Optional[TeamMember]:
        """
        Get a TeamMember entity by employee ID.

        Args:
            employee_id: The ID of the employee to find.

        Returns:
            The TeamMember entity if found, None otherwise.
        """
        for team_member in self._team_members:
            if team_member.employee_id == employee_id:
                return team_member
        return None

    def assign_role_to_member(self, employee_id: int, role_name: str) -> bool:
        """
        Assign a role to a team member.

        Args:
            employee_id: The ID of the employee.
            role_name: The name of the role to assign.

        Returns:
            True if the role was assigned, False if the employee is not a member
            or already has the role.
        """
        team_member = self.get_team_member_by_employee_id(employee_id)
        if not team_member:
            return False

        return team_member.add_role(role_name)

    def remove_role_from_member(self, employee_id: int, role_name: str) -> bool:
        """
        Remove a role from a team member.

        Args:
            employee_id: The ID of the employee.
            role_name: The name of the role to remove.

        Returns:
            True if the role was removed, False if the employee is not a member
            or doesn't have the role.
        """
        team_member = self.get_team_member_by_employee_id(employee_id)
        if not team_member:
            return False

        return team_member.remove_role(role_name)

    def validate(self) -> None:
        """
        Validates the team entity.
        Raises ValueError if validation fails.
        """
        if not self.name:
            raise ValueError("Team name cannot be empty")
        if len(self.name) > 100:  # Example validation rule
            raise ValueError("Team name cannot be longer than 100 characters")
