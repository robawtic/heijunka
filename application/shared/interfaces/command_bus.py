from abc import ABC, abstractmethod
from typing import TypeVar, Any, Type
from .command_handler import ICommand, ICommandHandler

TCommand = TypeVar('TCommand', bound=ICommand)
TCommandHandler = TypeVar('TCommandHandler', bound=ICommandHandler)
TResult = TypeVar('TResult')

class ICommandBus(ABC):
    """Command bus interface for dispatching commands."""

    @abstractmethod
    async def send(self, command: TCommand) -> TResult:
        """Send a command and return the result."""
        pass

    @abstractmethod
    def register_handler(self, command_type: Type[TCommand], handler_type: Type[TCommandHandler]) -> None:
        """Register a command handler."""
        pass
