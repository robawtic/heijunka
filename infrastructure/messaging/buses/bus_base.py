# application/shared/buses/bus_base.py
from typing import Any, Type
from infrastructure.messaging.behaviors.behavior_pipeline import BehaviorPipeline
from ..handlers.handler_registry import HandlerRegistry
from ..handlers.handler_factory import HandlerFactory

class BusBase:
    def __init__(self, dependency_container=None):
        self.pipeline = BehaviorPipeline()
        self.registry = HandlerRegistry()
        self.factory = HandlerFactory(dependency_container)

    def add_behavior(self, behavior):
        self.pipeline.add_behavior(behavior)

    def register_handler(self, request_type: Type, handler_type: Type):
        self.registry.register(request_type, handler_type)

    async def execute_request(self, request: Any, execution_error_class: Type[Exception]):
        # For handler discovery, we need to determine the appropriate validation error class
        # This is a temporary solution - in a full implementation, we'd pass both error classes
        validation_error_class = execution_error_class
        if hasattr(execution_error_class, '__name__'):
            if 'CommandExecution' in execution_error_class.__name__:
                from ..exceptions.command_validation_error import CommandValidationError
                validation_error_class = CommandValidationError
            elif 'QueryExecution' in execution_error_class.__name__:
                from ..exceptions.query_execution_error import QueryValidationError
                validation_error_class = QueryValidationError

        handler_type = self.registry.get_handler(request, validation_error_class)
        handler = self.factory.create_handler(handler_type, request, execution_error_class)
        return await self.pipeline.execute(request, handler)
