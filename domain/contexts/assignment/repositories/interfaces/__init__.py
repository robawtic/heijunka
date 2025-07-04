"""
Assignment Context - Repository Interfaces

This module contains repository interface definitions for assignment entities:
- AssignmentRepositoryInterface: Interface for work assignment data access operations
- AROAssignmentRepositoryInterface: Interface for ARO assignment data access operations
"""

from .assignment_repository import AssignmentRepositoryInterface
from .aro_assignment_repository import AROAssignmentRepositoryInterface

__all__ = [
    'AssignmentRepositoryInterface',
    'AROAssignmentRepositoryInterface',
]