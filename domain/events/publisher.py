from typing import Dict, List, Callable, Any
from domain.events.base import DomainEvent

class DomainEventPublisher:
    """
    Central publisher for domain events.
    
    This class decouples event producers from event consumers,
    allowing for a more flexible and maintainable event-driven architecture.
    """
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable[[DomainEvent], None]]] = {}
    
    def register(self, event_type: str, handler: Callable[[DomainEvent], None]) -> None:
        """
        Register a handler for a specific event type.
        
        Args:
            event_type: The type of event to handle
            handler: The handler function to call when the event occurs
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def publish(self, event: DomainEvent) -> None:
        """
        Publish an event to all registered handlers.
        
        Args:
            event: The event to publish
        """
        event_type = event.__class__.__name__
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                handler(event)