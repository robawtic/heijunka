from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from application.shared_kernel.base_interfaces.query import IQuery

TQuery = TypeVar('TQuery', bound=IQuery)
TResult = TypeVar('TResult')

class IScheduleQueryHandler(ABC, Generic[TQuery, TResult]):
    """Schedule management specific query handler interface."""
    
    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        """Handle schedule management query."""
        pass