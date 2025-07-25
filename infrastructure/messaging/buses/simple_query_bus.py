from typing import TypeVar, Type
from application.shared.interfaces.query_bus import IQueryBus, IQuery
from application.shared.interfaces.query_handler import IQueryHandler
from application.shared.exceptions.query_execution_error import QueryExecutionError, QueryValidationError
from .bus_base import BusBase

TQuery = TypeVar('TQuery', bound=IQuery)
TResult = TypeVar('TResult')

class SimpleQueryBus(IQueryBus, BusBase):
    """
    Production-grade in-memory async Query Bus with dynamic handler loading, 
    behavior pipeline, and robust error handling.

    Features:
    - Dynamic handler discovery via naming conventions
    - Explicit handler registration with validation
    - Behavior pipeline for cross-cutting concerns (logging, validation, caching)
    - Robust handler instantiation with detailed error messages
    - Comprehensive logging and debugging support
    - Dependency injection container support

    Usage:
        # Basic usage without DI
        bus = SimpleQueryBus()
        bus.register_handler(GetUserQuery, GetUserHandler)
        result = await bus.send(GetUserQuery(user_id=123))

        # With dependency injection
        bus = SimpleQueryBus(dependency_container=container)
        # Handlers will be resolved from container

        # With behaviors
        bus.add_behavior(logging_behavior)
        bus.add_behavior(caching_behavior)
    """

    def __init__(self, dependency_container=None):
        super().__init__(dependency_container)

    def register_handler(self, query_type: Type[TQuery], handler_type: Type[IQueryHandler]) -> None:
        BusBase.register_handler(self, query_type, handler_type)

    async def send(self, query: TQuery) -> TResult:
        return await self.execute_request(query, QueryExecutionError)
