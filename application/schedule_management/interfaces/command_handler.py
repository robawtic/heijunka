from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from application.shared_kernel.base_interfaces.command import ICommand

TCommand = TypeVar('TCommand', bound=ICommand)
TResult = TypeVar('TResult')

class IScheduleCommandHandler(ABC, Generic[TCommand, TResult]):
    """Schedule management specific command handler interface."""
    
    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        """Handle schedule management command."""
        pass