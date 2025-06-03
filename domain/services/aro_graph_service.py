import warnings
from typing import List, Dict, Tuple, Set, Optional, Any, Callable
from datetime import date, timedelta

# Forward imports to maintain backward compatibility
from domain.contexts.assignment.services.aro_graph_service import AROGraphService as ContextAROGraphService
from domain.events.publisher import DomainEventPublisher

class AROGraphService:
    """
    Service for optimizing ARO assignments using graph theory.

    This service extends the basic AROService with advanced optimization
    capabilities based on graph theory algorithms.
    
    DEPRECATED: This class is deprecated. Use domain.contexts.assignment.services.aro_graph_service.AROGraphService instead.
    """

    def __init__(self, 
                 aro_service,
                 aro_repository,
                 employee_repository,
                 team_repository,
                 workstation_repository,
                 event_publisher=None):
        warnings.warn(
            "This class is deprecated. Use domain.contexts.assignment.services.aro_graph_service.AROGraphService instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Create an instance of the context-specific AROGraphService
        self._context_service = ContextAROGraphService(
            aro_service=aro_service,
            aro_repository=aro_repository,
            employee_repository=employee_repository,
            team_repository=team_repository,
            workstation_repository=workstation_repository,
            event_publisher=event_publisher or DomainEventPublisher()
        )
        
        # Forward attributes for backward compatibility
        self.aro_service = aro_service
        self.aro_repository = aro_repository
        self.employee_repository = employee_repository
        self.team_repository = team_repository
        self.workstation_repository = workstation_repository
        self._edge_cost_cache = self._context_service._edge_cost_cache
        self._graph_cache = self._context_service._graph_cache
        self._session = getattr(aro_repository, '_session', None)

    def __getattr__(self, name):
        """Forward all method calls to the context-specific implementation."""
        return getattr(self._context_service, name)