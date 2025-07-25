from abc import ABC, abstractmethod
from typing import TypeVar, Generic

TQuery = TypeVar('TQuery')
TResult = TypeVar('TResult')

class IQueryHandler(ABC, Generic[TQuery, TResult]):
    """Base interface for query handlers with async support."""

    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        """Handle the query asynchronously."""
        pass

class IQuery(ABC):
    """Marker interface for queries."""
    pass
