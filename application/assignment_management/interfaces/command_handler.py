from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from application.shared_kernel.base_interfaces.command import ICommand

TCommand = TypeVar('TCommand', bound=ICommand)
TResult = TypeVar('TResult')

class IAssignmentCommandHandler(ABC, Generic[TCommand, TResult]):
    """Assignment management specific command handler interface."""
    
    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        """Handle assignment management command."""
        pass