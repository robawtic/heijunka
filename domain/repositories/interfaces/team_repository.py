from abc import abstractmethod
from typing import List, Optional, Any

from domain.contexts.employee_management.entities.team import Team
from domain.contexts.employee_management.entities.employee import Employee
from domain.contexts.workstation_management.entities.workstation import Workstation
from domain.repositories.interfaces.base_repository import BaseRepository


class TeamRepositoryInterface(BaseRepository[Team]):
    """
    Interface for team repository operations.
    """

    @abstractmethod
    def get(self, team_id: int) -> Optional[Team]:
        """
        Retrieve a team by its ID.

        Arggs:
            team_id: The ID of the team to retrieve.

        Returns:
            A team object if found, None otherwise.
        """

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Team]:
        """
        Retrieve a team by its name.

        Args:
            name: The name of the team.

        Returns:
            The team if found, None otherwise.
        """
        pass

    @abstractmethod
    def add_member(self, team_id: int, employee: Employee) -> bool:
        """
        Add an employee to a team.

        Args:
            team_id: The ID of the team.
            employee: The employee to add.

        Returns:
            True if the employee was added successfully, False otherwise.
        """
        pass

    @abstractmethod
    def remove_member(self, team_id: int, employee_id: int) -> bool:
        """
        Remove an employee from a team.

        Args:
            team_id: The ID of the team.
            employee_id: The ID of the employee to remove.

        Returns:
            True if the employee was removed successfully, False otherwise.
        """
        pass

    @abstractmethod
    def add_workstation(self, team_id: int, workstation: Workstation) -> bool:
        """
        Add a workstation to a team.

        Args:
            team_id: The ID of the team.
            workstation: The workstation to add.

        Returns:
            True if the workstation was added successfully, False otherwise.
        """
        pass

    @abstractmethod
    def remove_workstation(self, team_id: int, workstation_id: int) -> bool:
        """
        Remove a workstation from a team.

        Args:
            team_id: The ID of the team.
            workstation_id: The ID of the workstation to remove.

        Returns:
            True if the workstation was removed successfully, False otherwise.
        """
        pass

    @abstractmethod
    def get_members(self, team_id: int) -> List[Employee]:
        """
        Get all members of a team.

        Args:
            team_id: The ID of the team.

        Returns:
            A list of employees that are members of the team.
        """
        pass

    @abstractmethod
    def get_workstations(self, team_id: int) -> List[Workstation]:
        """
        Get all workstations of a team.

        Args:
            team_id: The ID of the team.

        Returns:
            A list of workstations that belong to the team.
        """
        pass

    @abstractmethod
    def get_with_counts(self, team_id: int) -> Optional[dict]:
        """
        Get a team with employee and workstation counts.

        Args:
            team_id: The ID of the team.

        Returns:
            A dictionary containing the team and counts if found, None otherwise.
            Example: {'team': team, 'employee_count': 10, 'workstation_count': 5}
        """
        pass

    @abstractmethod
    def get_by_group_name(self, group_name: str) -> List[Team]:
        """
        Retrieve all teams that belong to a group with the given name.

        Args:
            group_name: The name of the group.

        Returns:
            A list of teams that belong to the group.
        """
        pass

    @abstractmethod
    def get_by_department_name(self, department_name: str) -> List[Team]:
        """
        Retrieve all teams that belong to a department with the given name.

        Args:
            department_name: The name of the department.

        Returns:
            A list of teams that belong to the department (directly or through groups).
        """
        pass

    @abstractmethod
    def get_group(self, team_id: int) -> Optional[Any]:
        """
        Retrieve the group that a team belongs to.

        Args:
            team_id: The ID of the team.

        Returns:
            The group if found, None otherwise.
        """
        pass

    @abstractmethod
    def get_department(self, department_id: int) -> Optional[Any]:
        """
        Retrieve a department by its ID.

        Args:
            department_id: The ID of the department.

        Returns:
            The department if found, None otherwise.
        """
        pass
