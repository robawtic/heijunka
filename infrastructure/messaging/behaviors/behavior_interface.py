from abc import ABC, abstractmethod
from typing import Any, Callable, Awaitable

class IBehavior(ABC):
    """Base interface for all behaviors in the CQRS pipeline."""
    
    @abstractmethod
    async def execute(
        self, 
        request: Any, 
        next_handler: Callable[[Any], Awaitable[Any]]
    ) -> Any:
        """
        Execute the behavior with the given request and next handler in the pipeline.
        
        Args:
            request: The request (command or query) being processed
            next_handler: The next handler in the pipeline to call
            
        Returns:
            The result from the pipeline execution
        """
        pass