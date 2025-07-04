# heijunka/domain/contexts/employee_management/entities/employee.py
from dataclasses import dataclass, field
from typing import List, Optional, Set
from datetime import date
from domain.contexts.employee_management.value_objects.employee_availability import EmployeeAvailability, AvailabilityStatus
from domain.contexts.employee_management.entities.team_member import TeamMember
from domain.contexts.employee_management.value_objects.work_history_entry import WorkHistoryEntry
from domain.contexts.employee_management.value_objects.workstation_assignment import WorkstationAssignment
from domain.events import (
    DomainEvent, QualificationAdded, QualificationRemoved, 
    RoleAssigned, TeamRoleAssigned, WorkHistoryEntryAdded
)

@dataclass
class Employee:
    id: int
    name: str
    team_id: int
    is_active: bool = True
    _roles: List[str] = field(default_factory=list, repr=False)
    _qualifications: List[str] = field(default_factory=list, repr=False)
    _available_periods: List[EmployeeAvailability] = field(default_factory=list, repr=False)
    _work_history: List[WorkHistoryEntry] = field(default_factory=list, repr=False)
    _assigned_workstations: List[WorkstationAssignment] = field(default_factory=list, repr=False)
    _team_memberships: List[TeamMember] = field(default_factory=list, repr=False)
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Initialize collections if they are None."""
        if self._roles is None:
            self._roles = []
        if self._qualifications is None:
            self._qualifications = []
        if self._available_periods is None:
            self._available_periods = []
        if self._work_history is None:
            self._work_history = []
        if self._assigned_workstations is None:
            self._assigned_workstations = []
        if self._team_memberships is None:
            self._team_memberships = []
        if self._domain_events is None:
            self._domain_events = []


    @property
    def roles(self) -> List[str]:
        """Get a copy of the roles list to prevent direct modification."""
        return self._roles.copy()

    @property
    def qualifications(self) -> List[str]:
        """Get a copy of the qualifications list to prevent direct modification."""
        return self._qualifications.copy()

    @property
    def available_periods(self) -> List[EmployeeAvailability]:
        """Get a copy of the available periods list to prevent direct modification."""
        return self._available_periods.copy()

    @property
    def work_history(self) -> List[WorkHistoryEntry]:
        """Get a copy of the work history list to prevent direct modification."""
        return self._work_history.copy()

    @property
    def assigned_workstations(self) -> List[WorkstationAssignment]:
        """Get a copy of the assigned workstations list to prevent direct modification."""
        return self._assigned_workstations.copy()

    @property
    def team_memberships(self) -> List[TeamMember]:
        """Get a copy of the team memberships list to prevent direct modification."""
        return self._team_memberships.copy()

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

    def can_work(self, workstation: "Workstation") -> bool:
        """Check if employee is qualified to work at the given workstation"""
        return workstation.name in self._qualifications

    def has_role(self, role_name: str) -> bool:
        """Check if employee has the specified role"""
        return role_name in self._roles

    def can_handle_workstation_type(self, workstation: "Workstation") -> bool:
        """
        Check if employee can handle specific workstation type based on their qualifications
        and the workstation's requirements (heavy job, key skill, etc.)
        """
        if workstation.is_heavy() and not self.has_role("heavy_lifting_certified"):
            return False
        if workstation.requires_key_skill() and not self.has_role("key_skill_certified"):
            return False
        return True

    def is_qualified_for_line(self, line_type: str) -> bool:
        """Check if employee is qualified to work on a specific line type"""
        return f"{line_type}_qualified" in self._qualifications

    def add_qualification(self, qualification: str) -> bool:
        """
        Add a new qualification to the employee's skill set
        Returns False if already qualified
        Raises ValueError if qualification is invalid
        """
        if not isinstance(qualification, str) or not qualification:
            raise ValueError("Qualification must be a non-empty string")

        if qualification in self._qualifications:
            return False

        self._qualifications.append(qualification)
        self.register_domain_event(QualificationAdded(self.id, qualification))
        return True

    def remove_qualification(self, qualification: str) -> bool:
        """
        Remove a qualification from the employee's skill set
        Returns False if qualification didn't exist
        Raises ValueError if qualification is invalid
        """
        if not isinstance(qualification, str) or not qualification:
            raise ValueError("Qualification must be a non-empty string")

        if qualification not in self._qualifications:
            return False

        self._qualifications.remove(qualification)
        self.register_domain_event(QualificationRemoved(self.id, qualification))
        return True

    def assign_role(self, role: str) -> bool:
        """
        Assign a new role to the employee
        Returns False if already has the role
        Raises ValueError if role is invalid
        """
        if not isinstance(role, str) or not role:
            raise ValueError("Role must be a non-empty string")

        if role in self._roles:
            return False

        self._roles.append(role)
        self.register_domain_event(RoleAssigned(self.id, role))
        return True

    def can_substitute_for(self, workstation: "Workstation") -> bool:
        """
        Check if employee can be a substitute worker at the workstation
        This might have different criteria than regular assignment
        """
        return (self.can_work(workstation) and 
                self.can_handle_workstation_type(workstation) and
                self.is_qualified_for_line(workstation.line_type))

    def is_available_for_period(self, date_obj: date, period: Optional[int] = None) -> bool:
        """
        Check if employee is available for a specific date and period

        Args:
            date_obj: The date to check availability for
            period: Optional period of the day to check

        Returns:
            True if the employee is available, False otherwise
        """
        # By default, employees are available unless there's a record indicating unavailability
        is_aro = False

        for av in self._available_periods:
            if av.date != date_obj:
                continue

            # Full day unavailability (CALL_IN only - ARO is now considered available)
            if av.status == AvailabilityStatus.CALL_IN:
                return False

            # Track if employee is an ARO
            if av.status == AvailabilityStatus.ARO:
                is_aro = True

            # Period-specific unavailability
            if period is not None and av.period == period:
                if av.status in (AvailabilityStatus.PARTIAL, AvailabilityStatus.OFFLINE):
                    return False

        # ARO employees are considered available
        return True

    def add_availability(self, availability: EmployeeAvailability) -> bool:
        """
        Add an availability period for the employee

        Args:
            availability: The availability period to add

        Returns:
            True if the availability was added, False if it already exists

        Raises:
            ValueError: If the availability is invalid
        """
        if not isinstance(availability, EmployeeAvailability):
            raise ValueError("availability must be an EmployeeAvailability instance")

        # Check if this availability already exists
        for av in self._available_periods:
            if (av.date == availability.date and 
                av.period == availability.period):
                return False

        self._available_periods.append(availability)
        return True

    def assign_as_aro(self, to_team_id: int, assignment_date: date, period: Optional[int] = None) -> bool:
        """
        Assign this employee as an ARO to another team.

        Args:
            to_team_id: The ID of the team the employee is being assigned to
            assignment_date: The date of the assignment
            period: Optional period of the day for the assignment

        Returns:
            True if the assignment was created, False if already assigned
        """
        # Create an availability record with ARO status
        availability = EmployeeAvailability(
            employee_id=self.id,
            date=assignment_date,
            period=period,
            status=AvailabilityStatus.ARO
        )

        # Add the availability record
        if not self.add_availability(availability):
            return False

        # No need to raise an event here as the AROAssignment aggregate will do that
        return True

    def add_work_history_entry(self, workstation_id: int, worked_date: date, work_period: int) -> bool:
        """
        Add a work history entry

        Args:
            workstation_id: The ID of the workstation
            worked_date: The date the work was performed
            work_period: The period of the day the work was performed

        Returns:
            True if the entry was added successfully

        Raises:
            ValueError: If any of the parameters are invalid
        """
        if not isinstance(workstation_id, int) or workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(worked_date, date):
            raise ValueError("worked_date must be a date object")
        if not isinstance(work_period, int) or not 1 <= work_period <= 5:
            raise ValueError("work_period must be an integer between 1 and 5")

        entry = WorkHistoryEntry(
            employee_id=self.id,
            workstation_id=workstation_id,
            worked_date=worked_date,
            work_period=work_period
        )

        self._work_history.append(entry)
        self.register_domain_event(WorkHistoryEntryAdded(
            self.id, workstation_id, worked_date, work_period
        ))
        return True

    def assign_workstation(self, workstation_id: int, workstation_name: str) -> bool:
        """
        Assign a workstation to the employee

        Args:
            workstation_id: The ID of the workstation
            workstation_name: The name of the workstation

        Returns:
            True if the workstation was assigned, False if it was already assigned

        Raises:
            ValueError: If any of the parameters are invalid
        """
        if not isinstance(workstation_id, int) or workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(workstation_name, str) or not workstation_name:
            raise ValueError("workstation_name must be a non-empty string")

        # Check if this workstation is already assigned
        for ws in self._assigned_workstations:
            if ws.workstation_id == workstation_id:
                return False

        assignment = WorkstationAssignment(
            employee_id=self.id,
            workstation_id=workstation_id,
            workstation_name=workstation_name
        )

        self._assigned_workstations.append(assignment)
        return True

    def get_team_roles(self, team_id: int) -> List[str]:
        """
        Get all roles for a specific team

        Args:
            team_id: The ID of the team

        Returns:
            A list of role names for the team
        """
        for membership in self._team_memberships:
            if membership.team_id == team_id:
                return membership.roles.copy()
        return []

    def has_team_role(self, role_name: str, team_id: int) -> bool:
        """
        Check if employee has a specific role in a team

        Args:
            role_name: The name of the role to check
            team_id: The ID of the team

        Returns:
            True if the employee has the role in the team, False otherwise
        """
        team_roles = self.get_team_roles(team_id)
        return role_name in team_roles

    def add_team_role(self, role_name: str, team_id: int) -> bool:
        """
        Add a role for a specific team

        Args:
            role_name: The name of the role to add
            team_id: The ID of the team

        Returns:
            True if the role was added, False if it already exists or the team doesn't exist

        Raises:
            ValueError: If any of the parameters are invalid
        """
        if not isinstance(role_name, str) or not role_name:
            raise ValueError("role_name must be a non-empty string")
        if not isinstance(team_id, int) or team_id <= 0:
            raise ValueError("team_id must be a positive integer")

        for membership in self._team_memberships:
            if membership.team_id == team_id:
                if membership.add_role(role_name):
                    self.register_domain_event(TeamRoleAssigned(self.id, team_id, role_name))
                    return True
                return False
        return False