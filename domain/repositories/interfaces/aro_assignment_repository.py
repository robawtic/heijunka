from abc import abstractmethod
from typing import List, Optional
from datetime import date

from domain.contexts.assignment.aro_assignment import AROAssignment
from domain.repositories.interfaces.base_repository import BaseRepository

class AROAssignmentRepositoryInterface(BaseRepository[AROAssignment]):
    @abstractmethod
    def get_by_date(self, assignment_date: date) -> List[AROAssignment]:
        """Get all ARO assignments for a specific date."""
        pass

    @abstractmethod
    def get_by_employee_id(self, employee_id: int, assignment_date: Optional[date] = None) -> List[AROAssignment]:
        """Get ARO assignments for a specific employee, optionally filtered by date."""
        pass

    @abstractmethod
    def get_by_from_team_id(self, team_id: int, assignment_date: date) -> List[AROAssignment]:
        """Get ARO assignments where employees are leaving a specific team on a date."""
        pass

    @abstractmethod
    def get_by_to_team_id(self, team_id: int, assignment_date: date) -> List[AROAssignment]:
        """Get ARO assignments where employees are joining a specific team on a date."""
        pass

    @abstractmethod
    def get_employees_leaving(self, team_id: int, assignment_date: date, period: Optional[int] = None) -> List[int]:
        """Get IDs of employees leaving a team as AROs for a specific date and period."""
        pass

    @abstractmethod
    def get_employees_joining(self, team_id: int, assignment_date: date, period: Optional[int] = None) -> List[int]:
        """Get IDs of employees joining a team as AROs for a specific date and period."""
        pass
