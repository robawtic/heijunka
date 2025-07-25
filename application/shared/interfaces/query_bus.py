from abc import ABC, abstractmethod
from typing import TypeVar, Any, Type
from .query_handler import IQuery, IQueryHandler

TQuery = TypeVar('TQuery', bound=IQuery)
TQueryHandler = TypeVar('TQueryHandler', bound=IQueryHandler)
TResult = TypeVar('TResult')

class IQueryBus(ABC):
    """Query bus interface for dispatching queries."""

    @abstractmethod
    async def send(self, query: TQuery) -> TResult:
        """Send a query and return the result."""
        pass

    @abstractmethod
    def register_handler(self, query_type: Type[TQuery], handler_type: Type[TQueryHandler]) -> None:
        """Register a query handler."""
        pass
