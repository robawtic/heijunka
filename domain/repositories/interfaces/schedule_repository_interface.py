# heijunka/domain/repositories/interfaces/schedule_repository_interface.py
from abc import abstractmethod
from typing import List, Optional
from datetime import date

from domain.entities.schedule import Schedule
from domain.repositories.interfaces.base_repository import BaseRepository


class ScheduleRepositoryInterface(BaseRepository[Schedule]):
    """
    Interface for schedule repository operations.
    """
    
    @abstractmethod
    def get_by_task_id(self, task_id: str) -> Optional[Schedule]:
        """
        Get a schedule by its task ID.
        
        Args:
            task_id: The task ID of the schedule.
            
        Returns:
            The schedule if found, None otherwise.
        """
        pass
    
    @abstractmethod
    def get_by_team_id(self, team_id: int, start_date: Optional[date] = None,
                      end_date: Optional[date] = None, status: Optional[str] = None,
                      skip: int = 0, limit: int = 100) -> List[Schedule]:
        """
        Get all schedules for a specific team with filtering and pagination.
        
        Args:
            team_id: The ID of the team.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            status: Optional status filter.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            
        Returns:
            A list of schedules for the team.
        """
        pass
    
    @abstractmethod
    def create_schedule(self, team_id: int, start_date: date, periods: int, 
                       call_ins: List[str] = None, offline: List[str] = None, 
                       force_complete: bool = False) -> Schedule:
        """
        Create a new schedule.
        
        Args:
            team_id: The ID of the team.
            start_date: The start date of the schedule.
            periods: Number of periods.
            call_ins: List of employee names who called in (unavailable).
            offline: List of strings in format "employee:periods" specifying which employees are offline for which periods.
            force_complete: Whether to force completion of the schedule.
            
        Returns:
            The created schedule.
        """
        pass
    
    @abstractmethod
    def update_status(self, schedule_id: int, status: str, error_message: Optional[str] = None) -> Optional[Schedule]:
        """
        Update the status of a schedule.
        
        Args:
            schedule_id: The ID of the schedule.
            status: The new status.
            error_message: Optional error message.
            
        Returns:
            The updated schedule if found, None otherwise.
        """
        pass
    
    @abstractmethod
    def count(self, team_id: Optional[int] = None, start_date: Optional[date] = None,
             end_date: Optional[date] = None, status: Optional[str] = None) -> int:
        """
        Count schedules with filtering.
        
        Args:
            team_id: Optional team ID filter.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            status: Optional status filter.
            
        Returns:
            The number of schedules matching the filters.
        """
        pass