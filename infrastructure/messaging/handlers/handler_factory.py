# application/shared/handlers/handler_factory.py
from typing import Type, Any
import inspect

class HandlerFactory:
    def __init__(self, dependency_container=None):
        self._container = dependency_container

    def create_handler(self, handler_type: Type, request: Any, error_class: Type[Exception]) -> Any:
        """Create handler instance with DI support and error handling."""
        try:
            if self._container:
                handler = self._container.resolve(handler_type)
                if handler is None:
                    raise error_class(f"DI container returned None for handler {handler_type.__name__}")
            else:
                # Check constructor requirements
                sig = inspect.signature(handler_type.__init__)
                required_params = [p for p in sig.parameters.values() 
                                 if p.default is inspect.Parameter.empty and p.name != 'self']
                
                if required_params:
                    param_names = [p.name for p in required_params]
                    raise error_class(
                        f"Handler {handler_type.__name__} requires constructor arguments: {param_names}. "
                        f"Provide a dependency injection container."
                    )
                
                handler = handler_type()
            
            return handler
            
        except Exception as e:
            if isinstance(e, error_class):
                raise
            raise error_class(f"Failed to instantiate handler {handler_type.__name__}: {str(e)}")