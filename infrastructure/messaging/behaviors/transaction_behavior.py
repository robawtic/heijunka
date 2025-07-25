from typing import Any, Callable, Awaitable
from contextlib import asynccontextmanager
from .behavior_interface import IBehavior

class TransactionBehavior(IBehavior):
    """Cross-cutting transaction behavior for commands."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    async def execute(
        self,
        request: Any,
        next_handler: Callable[[Any], Awaitable[Any]]
    ) -> Any:
        """Execute handler within a transaction."""
        if self._session_factory:
            async with self._create_transaction() as session:
                try:
                    result = await next_handler(request)
                    await session.commit()
                    return result
                except Exception:
                    await session.rollback()
                    raise
        else:
            # No transaction support configured
            return await next_handler(request)

    @asynccontextmanager
    async def _create_transaction(self):
        """Create a database transaction context."""
        session = self._session_factory()
        try:
            yield session
        finally:
            await session.close()
