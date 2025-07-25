# application/shared/handlers/handler_registry.py
from typing import Dict, Type, Any

class HandlerRegistry:
    def __init__(self):
        self._registry: Dict[Type, Type] = {}

    def register(self, request_type: Type, handler_type: Type):
        self._registry[request_type] = handler_type

    def get_handler(self, request: Any, error_class: Type[Exception]) -> Type:
        handler_type = self._registry.get(type(request))
        if not handler_type:
            raise error_class(f"No handler registered for request: {type(request).__name__}")
        return handler_type
