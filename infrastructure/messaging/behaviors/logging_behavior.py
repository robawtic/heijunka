import logging
import time
from typing import Any, Callable, Awaitable
from .behavior_interface import IBehavior

logger = logging.getLogger(__name__)

class LoggingBehavior(IBehavior):
    """Cross-cutting logging behavior for commands and queries."""

    async def execute(
        self,
        request: Any,
        next_handler: Callable[[Any], Awaitable[Any]]
    ) -> Any:
        """Execute handler with logging."""
        request_name = type(request).__name__
        start_time = time.time()

        logger.info(f"Executing {request_name}")

        try:
            result = await next_handler(request)
            execution_time = time.time() - start_time
            logger.info(f"Successfully executed {request_name} in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Failed to execute {request_name} in {execution_time:.3f}s: {str(e)}")
            raise
