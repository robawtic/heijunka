"""
Assignment Context - Value Objects

This module contains all value objects related to assignment operations including:
- WorkAssignmentValidator: Validation logic for work assignments
- AssignmentCriteria: Criteria and constraints for assignment optimization
"""

from .work_assignment_validator import WorkAssignmentValidator
from .assignment_criteria import AssignmentCriteria

__all__ = [
    'WorkAssignmentValidator',
    'AssignmentCriteria',
]