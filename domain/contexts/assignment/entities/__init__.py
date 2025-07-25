"""
Assignment Context - Entities

This module contains all entities related to assignment operations including:
- WorkAssignment: Core entity representing employee-workstation assignments
- TeamAro: Team ARO (Auxiliary Relief Operator) entity
- Assignment business logic and validation
"""

from .work_assignment import WorkAssignment
from .team_aro import TeamAro

__all__ = [
    'WorkAssignment',
    'TeamAro',
]
