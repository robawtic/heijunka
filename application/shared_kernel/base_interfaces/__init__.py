"""Base interfaces for the shared kernel."""

from .command import ICommand
from .query import IQuery
from .domain_event import IDomainEvent

__all__ = ['ICommand', 'IQuery', 'IDomainEvent']