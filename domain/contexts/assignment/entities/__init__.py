"""
Assignment Context - Entities

This module contains all entities related to assignment operations including:
- WorkAssignment: Core entity representing employee-workstation assignments
- Assignment business logic and validation
"""

from .work_assignment import WorkAssignment

__all__ = [
    'WorkAssignment',
]