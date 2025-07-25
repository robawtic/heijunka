from abc import ABC, abstractmethod
from typing import TypeVar, Generic

TCommand = TypeVar('TCommand')
TResult = TypeVar('TResult')

class ICommandHandler(ABC, Generic[TCommand, TResult]):
    """Base interface for command handlers with async support."""

    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        """Handle the command asynchronously."""
        pass

class ICommand(ABC):
    """Marker interface for commands."""
    pass
