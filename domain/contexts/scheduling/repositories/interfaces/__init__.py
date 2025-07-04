"""
Scheduling Context - Repository Interfaces

This module contains repository interface definitions for scheduling entities:
- ScheduleRepository: Interface for schedule data access operations (model-based)
- ScheduleRepositoryInterface: Interface for schedule data access operations (entity-based)
"""

from .schedule_repository import ScheduleRepository
from .schedule_repository_interface import ScheduleRepositoryInterface

__all__ = [
    'ScheduleRepository',
    'ScheduleRepositoryInterface',
]
