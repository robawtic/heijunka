"""Minimal domain event marker interface for inter-context communication."""
from abc import ABC

class IDomainEvent(ABC):
    """Marker interface for domain events that cross bounded context boundaries."""
    pass
