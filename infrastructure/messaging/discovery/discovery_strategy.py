# application/shared/discovery/discovery_strategy.py
from typing import Type, Optional, Dict, Any

class DiscoveryStrategy:
    """
    Configurable strategy for discovering handlers based on naming conventions.
    Reduces tight coupling by allowing customization of discovery patterns and error handling.
    """

    def __init__(self, 
                 request_suffix: str = "Command", 
                 handler_suffix: str = "Handler", 
                 module_path_from: str = ".commands", 
                 module_path_to: str = ".handlers",
                 validation_error_class: Optional[Type[Exception]] = None,
                 execution_error_class: Optional[Type[Exception]] = None,
                 custom_mappings: Optional[Dict[str, str]] = None):
        """
        Initialize discovery strategy with configurable options.

        Args:
            request_suffix: Suffix to identify request classes (e.g., "Command", "Query")
            handler_suffix: Suffix for handler classes (e.g., "Handler")
            module_path_from: Module path pattern to replace (e.g., ".commands")
            module_path_to: Module path replacement (e.g., ".handlers")
            validation_error_class: Exception class for validation errors
            execution_error_class: Exception class for execution errors
            custom_mappings: Custom module path mappings for special cases
        """
        self.request_suffix = request_suffix
        self.handler_suffix = handler_suffix
        self.module_path_from = module_path_from
        self.module_path_to = module_path_to
        self.validation_error_class = validation_error_class
        self.execution_error_class = execution_error_class
        self.custom_mappings = custom_mappings or {}

    def resolve_handler_module(self, request_module: str) -> str:
        """
        Resolve handler module path from request module path.

        Args:
            request_module: The module path of the request class

        Returns:
            The expected module path for the handler
        """
        # Check custom mappings first
        if request_module in self.custom_mappings:
            return self.custom_mappings[request_module]

        # Use standard pattern replacement
        return request_module.replace(self.module_path_from, self.module_path_to)

    def get_handler_class_name(self, request_class_name: str) -> str:
        """
        Generate handler class name from request class name.

        Args:
            request_class_name: Name of the request class

        Returns:
            Expected name of the handler class

        Raises:
            ValueError: If request class name doesn't follow naming convention
        """
        if not request_class_name.endswith(self.request_suffix):
            raise ValueError(
                f"Invalid request class naming convention. "
                f"Expected suffix '{self.request_suffix}', got '{request_class_name}'"
            )
        return request_class_name.replace(self.request_suffix, self.handler_suffix)

    def create_validation_error(self, message: str, request_name: str, **kwargs) -> Exception:
        """
        Create validation error with appropriate constructor arguments.

        Args:
            message: Error message
            request_name: Name of the request that failed validation
            **kwargs: Additional arguments for the exception

        Returns:
            Configured validation exception
        """
        if self.validation_error_class:
            return self._create_typed_exception(
                self.validation_error_class, message, request_name, **kwargs
            )
        return Exception(message)

    def create_execution_error(self, message: str, request_name: str, **kwargs) -> Exception:
        """
        Create execution error with appropriate constructor arguments.

        Args:
            message: Error message
            request_name: Name of the request that failed execution
            **kwargs: Additional arguments for the exception

        Returns:
            Configured execution exception
        """
        if self.execution_error_class:
            return self._create_typed_exception(
                self.execution_error_class, message, request_name, **kwargs
            )
        return Exception(message)

    def _create_typed_exception(self, error_class: Type[Exception], message: str, 
                              request_name: str, **kwargs) -> Exception:
        """
        Create exception with appropriate constructor arguments based on class signature.

        Args:
            error_class: Exception class to instantiate
            message: Error message
            request_name: Name of the request
            **kwargs: Additional arguments

        Returns:
            Configured exception instance
        """
        import inspect

        sig = inspect.signature(error_class.__init__)
        constructor_kwargs = {}

        # Map common parameter names
        if 'command_type' in sig.parameters:
            constructor_kwargs['command_type'] = request_name
        elif 'query_type' in sig.parameters:
            constructor_kwargs['query_type'] = request_name

        # Add any additional kwargs that match constructor parameters
        for key, value in kwargs.items():
            if key in sig.parameters:
                constructor_kwargs[key] = value

        return error_class(message, **constructor_kwargs)
