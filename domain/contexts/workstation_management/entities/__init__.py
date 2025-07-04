"""
Workstation Management Context - Entities

This module contains all entities related to workstation management including:
- Workstation: Core workstation entity with business logic and validation
- Workstation domain events and lifecycle management
"""

from .workstation import Workstation

__all__ = [
    'Workstation',
]