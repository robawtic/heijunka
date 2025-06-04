from abc import abstractmethod
from typing import Optional, List, Dict, Tuple
from datetime import date

from domain.entities.employee import Employee
from domain.repositories.interfaces.base_repository import BaseRepository


class EmployeeRepositoryInterface(BaseRepository[Employee]):
    """
    Interface for employee repository operations.
    """

    @abstractmethod
    def get(self, employee_id: int) -> Optional[Employee]:
        """
        Retrieve an employee by their ID.

        Args:
            employee_id: The ID of the employee to retrieve.

        Returns:
            An employee object if found, None otherwise.
        """

    @abstractmethod
    def get_by_team_id(self, team_id: int) -> List[Employee]:
        """
        Retrieve all employees for a specific team.

        Args:
            team_id: The ID of the team.

        Returns:
            A list of employees belonging to the team.
        """
        pass

    @abstractmethod
    def is_available(self, employee_id: int, date_obj: date, period: Optional[int] = None) -> bool:
        """
        Check if employee is available on the given date and period.

        Args:
            employee_id: The ID of the employee.
            date_obj: The date to check availability for.
            period: Optional period of the day to check.

        Returns:
            True if the employee is available, False otherwise.
        """
        pass

    @abstractmethod
    def assign_role(self, employee_id: int, role_name: str, team_id: int) -> Dict[str, str]:
        """
        Assign a role to an employee within a team.

        Args:
            employee_id: The ID of the employee.
            role_name: The name of the role to assign.
            team_id: The ID of the team.

        Returns:
            A dictionary with status and message.
        """
        pass

    @abstractmethod
    def remove_role(self, employee_id: int, role_name: str, team_id: int) -> Dict[str, str]:
        """
        Remove a role from an employee within a team.

        Args:
            employee_id: The ID of the employee.
            role_name: The name of the role to remove.
            team_id: The ID of the team.

        Returns:
            A dictionary with status and message.
        """
        pass

    @abstractmethod
    def assign_workstation(self, employee_id: int, workstation_id: int) -> Dict[str, str]:
        """
        Assign a workstation to an employee.

        Args:
            employee_id: The ID of the employee.
            workstation_id: The ID of the workstation.

        Returns:
            A dictionary with status and message.
        """
        pass

    @abstractmethod
    def get_work_history(self, employee_id: int, workstation_id: int) -> list:
        """
        Get employee's work history for a specific workstation.

        Args:
            employee_id: The ID of the employee.
            workstation_id: The ID of the workstation.

        Returns:
            A list of work history entries.
        """
        pass

    @abstractmethod
    def add_work_history(self, employee_id: int, workstation_id: int,
                         worked_date: date, work_period: int, end_flag: bool = False) -> bool:
        """
        Add a work history entry.

        Args:
            employee_id: The ID of the employee.
            workstation_id: The ID of the workstation.
            worked_date: The date the work was performed.
            work_period: The period of the day the work was performed.
            end_flag: Whether this is the end of a work session.

        Returns:
            True if the entry was added successfully, False otherwise.
        """
        pass

    @abstractmethod
    def get_last_worked_date(self, employee_id: int, workstation_id: int) -> Tuple[Optional[date], Optional[int]]:
        """
        Get the last date an employee worked at a specific workstation.

        Args:
            employee_id: The ID of the employee.
            workstation_id: The ID of the workstation.

        Returns:
            A tuple containing the date and period, or (None, None) if no history exists.
        """
        pass

    @abstractmethod
    def get_by_team_ids(self, team_ids: List[int]) -> List[Employee]:
        """
        Retrieve all employees for multiple teams in a single query.

        Args:
            team_ids: List of team IDs to fetch employees for.

        Returns:
            A list of employees belonging to any of the specified teams.
        """
        pass
