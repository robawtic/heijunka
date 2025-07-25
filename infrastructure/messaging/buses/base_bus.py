from typing import Any, Type, Dict, TypeVar, Generic, List, Callable, Awaitable, Optional
import importlib
import logging
import time
import inspect
from abc import ABC, abstractmethod

from application.shared.exceptions.enhanced_exceptions import ExceptionHelper

# Set up logger for this module
logger = logging.getLogger(__name__)

# Type alias for behavior functions
BehaviorFunction = Callable[[Any, Callable[[Any], Awaitable[Any]]], Awaitable[Any]]


class BehaviorPipelineMixin:
    """
    Mixin class that provides behavior pipeline functionality for command and query buses.

    This mixin handles:
    - Behavior registration and management
    - Pipeline execution with proper ordering
    - Common logging and error handling patterns
    """

    def __init__(self):
        self._behaviors: List[BehaviorFunction] = []

    def add_behavior(self, behavior: BehaviorFunction) -> None:
        """
        Add a behavior to the pipeline. Behaviors are executed in the order they are added.

        Args:
            behavior: A function that takes (request, next_handler) and returns awaitable result
        """
        self._behaviors.append(behavior)
        logger.debug("Added behavior: %s", getattr(behavior, '__name__', str(behavior)))

    async def _execute_with_behaviors(self, request: Any, handler: Any) -> Any:
        """
        Execute the handler through the behavior pipeline.

        Args:
            request: The request (command or query) to process
            handler: The handler instance

        Returns:
            Result from handler execution
        """
        if not self._behaviors:
            # No behaviors, execute handler directly
            return await handler.handle(request)

        # Build behavior pipeline
        async def execute_handler(req):
            return await handler.handle(req)

        # Apply behaviors in reverse order (last added executes first)
        pipeline = execute_handler
        for behavior in reversed(self._behaviors):
            current_pipeline = pipeline

            def create_pipeline_step(behavior_func, next_pipeline):
                async def pipeline_step(req):
                    return await behavior_func(req, next_pipeline)

                return pipeline_step

            pipeline = create_pipeline_step(behavior, current_pipeline)

        return await pipeline(request)


class HandlerInstantiationMixin:
    """
    Mixin class that provides robust handler instantiation with error handling.

    This mixin handles:
    - DI container integration
    - Constructor validation
    - Detailed error messages for instantiation failures
    """

    def __init__(self, dependency_container=None):
        self._container = dependency_container

    def _create_handler_instance(self, handler_type: Type, request_name: str, error_class: Type[Exception]) -> Any:
        """
        Create handler instance with robust error handling and helpful error messages.

        Args:
            handler_type: The handler class to instantiate
            request_name: Name of the request (command/query) for error messages
            error_class: Exception class to raise on errors

        Returns:
            Handler instance ready for execution

        Raises:
            error_class: If handler instantiation fails
        """
        try:
            if self._container:
                logger.debug("Resolving handler %s from DI container", handler_type.__name__)
                handler = self._container.resolve(handler_type)
                if handler is None:
                    if hasattr(error_class, '__init__'):
                        sig = inspect.signature(error_class.__init__)
                        if 'command_type' in sig.parameters:
                            raise ExceptionHelper.create_typed_exception(error_class=error_class,
                                message=(f"DI container returned None for handler {handler_type.__name__}. "
                                         f"Ensure the handler is registered and resolvable."),
                                request_name=request_name, handler_type=handler_type.__name__,
                                execution_context={"resolver": "DI container", "reason": "null handler"})
                        elif 'query_type' in sig.parameters:
                            raise ExceptionHelper.create_typed_exception(error_class=error_class,
                                message=(f"DI container returned None for handler {handler_type.__name__}. "
                                         f"Ensure the handler is registered and resolvable."),
                                request_name=request_name, handler_type=handler_type.__name__,
                                execution_context={"resolution_strategy": "DI container",
                                    "handler_class": handler_type.__name__, "reason": "Null handler returned"})

                    raise ExceptionHelper.create_typed_exception(error_class=error_class,
                        message=(f"DI container returned None for handler {handler_type.__name__}. "
                                 f"Ensure the handler is registered and resolvable."), request_name=request_name,
                        handler_type=handler_type.__name__, execution_context={"resolution_strategy": "DI container",
                            "handler_class": handler_type.__name__, "reason": "Fallback instantiation logic triggered"})
            else:
                logger.debug("Creating handler %s directly (no DI container)", handler_type.__name__)\

                sig = inspect.signature(handler_type.__init__)
                required_params = [p for p in sig.parameters.values() if
                    p.default is inspect.Parameter.empty and p.name != 'self']

                if required_params:
                    param_names = [p.name for p in required_params]
                    raise ExceptionHelper.create_typed_exception(error_class=error_class,
                        message=(f"Handler {handler_type.__name__} requires constructor arguments: {param_names}. "
                                 f"Either provide a dependency injection container or modify the handler "
                                 f"to have a parameterless constructor."), request_name=request_name,
                        handler_type=handler_type.__name__,
                        execution_context={"resolution_strategy": "direct instantiation",
                            "handler_class": handler_type.__name__, "missing_parameters": param_names,
                            "reason": "constructor argument mismatch"})

                handler = handler_type()

            logger.debug("Successfully created handler instance: %s", type(handler).__name__)

            return handler

        except Exception as e:

            if isinstance(e, error_class):
                raise
            logger.error("Failed to instantiate handler %s: %s", handler_type.__name__, str(e))
            raise ExceptionHelper.create_typed_exception(
                error_class=error_class,
                message=f"Handler instantiation failed for {handler_type.__name__}: {str(e)}",
                request_name=request_name,
                handler_type=handler_type.__name__,
                inner_exception=e,
                execution_context={
                    "resolution_strategy": "direct instantiation",
                    "handler_class": handler_type.__name__,
                    "reason": "Unhandled exception",
                    "exception_type": type(e).__name__
                }
            )


class HandlerDiscoveryMixin:
    """
    Mixin class that provides handler discovery and registration functionality.

    This mixin handles:
    - Explicit handler registration with validation
    - Dynamic handler discovery via naming conventions
    - Enhanced error reporting for missing handlers
    """

    def __init__(self):
        self._handlers: Dict[Type, Type] = {}

    def _register_handler_with_validation(self, request_type: Type, handler_type: Type, request_interface: Type,
                                          handler_method: str = 'handle') -> None:
        """
        Register a handler with validation.

        Args:
            request_type: The request class (command/query) that this handler processes
            handler_type: The handler class
            request_interface: The interface that request_type should implement
            handler_method: The method name that handler should have (default: 'handle')

        Raises:
            ValueError: If request_type or handler_type is invalid
        """
        if not issubclass(request_type, request_interface):
            raise ValueError(f"request_type must implement {request_interface.__name__}, got {request_type}")

        if not hasattr(handler_type, handler_method):
            raise ValueError(f"handler_type must implement {handler_method} method, got {handler_type}")

        self._handlers[request_type] = handler_type
        logger.debug("Registered handler %s for request %s", handler_type.__name__, request_type.__name__)

    def _get_handler_type_with_discovery(self, request_type: Type, request_suffix: str, handler_suffix: str,
            module_path_from: str, module_path_to: str, error_class: Type[Exception]) -> Type:
        """
        Get handler type for request with auto-discovery fallback and enhanced error messages.
        """
        request_name = request_type.__name__

        if request_type in self._handlers:
            handler_type = self._handlers[request_type]
            logger.debug("Found registered handler %s for request %s", handler_type.__name__, request_name)
            return handler_type

        handler_name = request_name.replace(request_suffix, handler_suffix)
        module_name = request_type.__module__.replace(module_path_from, module_path_to)

        logger.debug("Attempting dynamic discovery: %s in module %s", handler_name, module_name)

        try:
            module = importlib.import_module(module_name)
            handler_type = getattr(module, handler_name)
            self._handlers[request_type] = handler_type

            logger.info("Dynamically discovered and cached handler %s for request %s", handler_name, request_name)
            return handler_type

        except ImportError as e:
            logger.warning("Could not import handler module %s: %s", module_name, str(e))

            raise ExceptionHelper.create_typed_exception(error_class=error_class, message=(
                f"No handler registered for {request_name} and failed to import handler module '{module_name}'. "
                f"Expected handler: {handler_name}. Either register the handler explicitly or fix the import path."),
                request_name=request_name, handler_type=handler_name, inner_exception=e,
                execution_context={"resolution_strategy": "dynamic discovery", "request_class": request_name,
                    "handler_class_expected": handler_name, "module_path_attempted": module_name,
                    "reason": "module import failure"})

        except AttributeError as e:
            logger.warning("Handler %s not found in module %s: %s", handler_name, module_name, str(e))

            raise ExceptionHelper.create_typed_exception(error_class=error_class,
                message=(f"No handler registered for {request_name} and handler class '{handler_name}' "
                         f"was not found in module '{module_name}'. Either register explicitly or ensure the class exists."),
                request_name=request_name, handler_type=handler_name, inner_exception=e,
                execution_context={"resolution_strategy": "dynamic discovery", "request_class": request_name,
                    "handler_class_expected": handler_name, "module_path_attempted": module_name,
                    "reason": "class lookup failure"})
