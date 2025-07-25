from typing import TypeVar, Type
from application.shared.interfaces.command_bus import ICommandBus, ICommand
from application.shared.interfaces.command_handler import ICommandHandler
from application.shared.exceptions.command_validation_error import CommandValidationError, CommandExecutionError
from .bus_base import BusBase

TCommand = TypeVar('TCommand', bound=ICommand)
TResult = TypeVar('TResult')

class SimpleCommandBus(ICommandBus, BusBase):
    """
    Production-grade in-memory async Command Bus with dynamic handler loading, 
    behavior pipeline, and robust error handling.

    Features:
    - Dynamic handler discovery via naming conventions
    - Explicit handler registration with validation
    - Behavior pipeline for cross-cutting concerns (logging, validation, transactions)
    - Robust handler instantiation with detailed error messages
    - Comprehensive logging and debugging support
    - Dependency injection container support

    Usage:
        # Basic usage without DI
        bus = SimpleCommandBus()
        bus.register_handler(CreateUserCommand, CreateUserHandler)
        result = await bus.send(CreateUserCommand(username="john"))

        # With dependency injection
        bus = SimpleCommandBus(dependency_container=container)
        # Handlers will be resolved from container

        # With behaviors
        bus.add_behavior(logging_behavior)
        bus.add_behavior(validation_behavior)
    """

    def __init__(self, dependency_container=None):
        super().__init__(dependency_container)

    def register_handler(self, command_type: Type[TCommand], handler_type: Type[ICommandHandler]) -> None:
        BusBase.register_handler(self, command_type, handler_type)


    async def send(self, command: TCommand) -> TResult:
        return await self.execute_request(command, CommandExecutionError)
