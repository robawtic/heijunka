"""
Assignment Context - Value Objects

This module contains all value objects related to assignment operations including:
- WorkAssignmentValidator: Validation logic for work assignments
- AssignmentCriteria: Criteria and constraints for assignment optimization
- WorkstationAssignment: Employee workstation assignment value object
- WorkAssignment: Work assignment value object
"""

from .work_assignment_validator import WorkAssignmentValidator
from .assignment_criteria import AssignmentCriteria
from .workstation_assignment import WorkstationAssignment
from .work_assignment import WorkAssignment

__all__ = [
    'WorkAssignmentValidator',
    'AssignmentCriteria',
    'WorkstationAssignment',
    'WorkAssignment',
]
