"""
Workstation Management Context - Value Objects

This module contains all value objects related to workstation management including:
- WorkstationCapacity: Value object for workstation capacity management
- LineType: Value object for production line type definitions
"""

from .workstation_capacity import WorkstationCapacity
from .line_type import LineType

__all__ = [
    'WorkstationCapacity',
    'LineType',
]