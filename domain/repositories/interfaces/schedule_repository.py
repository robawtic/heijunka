from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date

from domain.models.ScheduleModel import ScheduleModel

class ScheduleRepository(ABC):
    """Repository interface for schedule operations."""
    
    @abstractmethod
    def create(self, team_id: int, start_date: date, periods: int,
               call_ins: List[str] = None, offline: List[str] = None, 
               force_complete: bool = False) -> ScheduleModel:
        """Create a new schedule."""
        pass
    
    @abstractmethod
    def get_by_id(self, schedule_id: int) -> Optional[ScheduleModel]:
        """Get a schedule by ID."""
        pass
    
    @abstractmethod
    def get_by_task_id(self, task_id: str) -> Optional[ScheduleModel]:
        """Get a schedule by task ID."""
        pass
    
    @abstractmethod
    def update(self, schedule_id: int, **kwargs) -> Optional[ScheduleModel]:
        """Update a schedule."""
        pass
    
    @abstractmethod
    def get_all(self, team_id: Optional[int] = None, start_date: Optional[date] = None,
                end_date: Optional[date] = None, status: Optional[str] = None,
                skip: int = 0, limit: int = 100) -> List[ScheduleModel]:
        """Get all schedules with filtering and pagination."""
        pass
    
    @abstractmethod
    def count(self, team_id: Optional[int] = None, start_date: Optional[date] = None,
              end_date: Optional[date] = None, status: Optional[str] = None) -> int:
        """Count schedules with filtering."""
        pass