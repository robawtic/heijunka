"""
Employee Management Context - Entities

This module contains all entities related to employee management including:
- Employee: The main employee entity for workforce management
- TeamMember: Team membership entity for employee-team relationships
- Department: Organizational department entity
- Group: Organizational group entity
- Team: Team entity for organizing employees
"""

from .employee import Employee
from .team_member import TeamMember
from .department import Department
from .group import Group
from .team import Team

__all__ = [
    'Employee',
    'TeamMember', 
    'Department',
    'Group',
    'Team'
]
