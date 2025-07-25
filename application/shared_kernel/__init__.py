"""
Minimal Shared Kernel for Heijunka System
Essential abstractions shared across all bounded contexts (<2KB total).
"""

from .base_interfaces.command import ICommand
from .base_interfaces.query import IQuery
from .base_interfaces.domain_event import IDomainEvent
from .common_exceptions.system_error import SystemError, InfrastructureError

__all__ = [
    'ICommand',
    'IQuery', 
    'IDomainEvent',
    'SystemError',
    'InfrastructureError'
]

# Version for tracking shared kernel changes
__version__ = '1.0.0'
