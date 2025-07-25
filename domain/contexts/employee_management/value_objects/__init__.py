"""
Employee Management Context - Value Objects

This module contains all value objects related to employee management including:
- EmployeeAvailability: Employee availability for specific dates and periods
- EmployeeTraining: Employee training records and certifications
- WorkHistoryEntry: Employee work history entries
"""

from .employee_availability import EmployeeAvailability, AvailabilityStatus
from .employee_training import EmployeeTraining
from .work_history_entry import WorkHistoryEntry

__all__ = [
    'EmployeeAvailability',
    'AvailabilityStatus',
    'EmployeeTraining',
    'WorkHistoryEntry'
]
