from abc import abstractmethod
from typing import List

from domain.value_objects.work_assignment import WorkAssignment
from domain.repositories.interfaces.base_repository import BaseRepository


class AssignmentRepositoryInterface(BaseRepository[WorkAssignment]):
    """
    Interface for assignment repository operations.
    """

    @abstractmethod
    def save_all(self, assignments: List[WorkAssignment]) -> bool:
        """
        Save a list of work assignments.

        Args:
            assignments: The list of work assignments to save.

        Returns:
            True if all assignments were saved successfully, False otherwise.
        """
        pass

    @abstractmethod
    def get_by_employee_id(self, employee_id: int) -> List[WorkAssignment]:
        """
        Retrieve all assignments for a specific employee.

        Args:
            employee_id: The ID of the employee.

        Returns:
            A list of work assignments for the employee.
        """
        pass

    @abstractmethod
    def get_by_workstation_id(self, workstation_id: int) -> List[WorkAssignment]:
        """
        Retrieve all assignments for a specific workstation.

        Args:
            workstation_id: The ID of the workstation.

        Returns:
            A list of work assignments for the workstation.
        """
        pass

    @abstractmethod
    def get_by_schedule_id(self, schedule_id: int) -> List[WorkAssignment]:
        """
        Retrieve all assignments for a specific schedule.

        Args:
            schedule_id: The ID of the schedule.

        Returns:
            A list of work assignments for the schedule.
        """
        pass

    @abstractmethod
    def create_temporary_assignment(self, employee_id: int, workstation_id: int, date, period: int, schedule_id: int = None) -> bool:
        """
        Create a temporary assignment for an employee at a workstation.

        This method is used when an employee temporarily takes over a station from another employee.

        Args:
            employee_id: The ID of the employee taking over the station.
            workstation_id: The ID of the workstation being taken over.
            date: The date of the assignment.
            period: The period of the day.
            schedule_id: Optional ID of the schedule this assignment belongs to.

        Returns:
            True if the assignment was created successfully, False otherwise.
        """
        pass
