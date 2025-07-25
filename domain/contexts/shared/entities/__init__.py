"""
Shared Context - Entities

This module contains all entities that are shared across multiple contexts including:
- Role: User role entity for authorization and permissions
- Seed Data: Various seed data entities for database initialization
"""

from .role import Role
from .seed_data import DepartmentSeedData, GroupSeedData, TeamSeedData, WorkstationSeedData, EmployeeSeedData

__all__ = [
    'Role',
    'DepartmentSeedData',
    'GroupSeedData', 
    'TeamSeedData',
    'WorkstationSeedData',
    'EmployeeSeedData',
]
