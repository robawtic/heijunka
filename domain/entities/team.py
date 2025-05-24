# heijunka/domain/entities/team.py
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Team:
    id: int
    name: str
    members: List["Employee"] = None
    workstations: List["Workstation"] = None
    description: str = ""

    def __post_init__(self):
        if self.members is None:
            self.members = []
        if self.workstations is None:
            self.workstations = []

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

    def add_member(self, employee: "Employee") -> bool:
        """
        Add an employee to the team.

        Args:
            employee: The employee to add.

        Returns:
            True if the employee was added, False if already a member.
        """
        for member in self.members:
            if member.id == employee.id:
                return False  # Already a member
        self.members.append(employee)
        return True

    def remove_member(self, employee_id: int) -> bool:
        """
        Remove an employee from the team.

        Args:
            employee_id: The ID of the employee to remove.

        Returns:
            True if the employee was removed, False if not a member.
        """
        for i, member in enumerate(self.members):
            if member.id == employee_id:
                self.members.pop(i)
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
        for ws in self.workstations:
            if ws.id == workstation.id:
                return False  # Already assigned
        self.workstations.append(workstation)
        return True

    def remove_workstation(self, workstation_id: int) -> bool:
        """
        Remove a workstation from the team.

        Args:
            workstation_id: The ID of the workstation to remove.

        Returns:
            True if the workstation was removed, False if not assigned.
        """
        for i, ws in enumerate(self.workstations):
            if ws.id == workstation_id:
                self.workstations.pop(i)
                return True
        return False

    def validate(self) -> None:
        """
        Validates the team entity.
        Raises ValueError if validation fails.
        """
        if not self.name:
            raise ValueError("Team name cannot be empty")
        if len(self.name) > 100:  # Example validation rule
            raise ValueError("Team name cannot be longer than 100 characters")