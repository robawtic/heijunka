from typing import Optional

class CommandExecutionError(Exception):
    """Exception raised when command execution fails."""

    def __init__(
        self,
        message: str,
        command_type: Optional[str] = None,
        inner_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.command_type = command_type
        self.inner_exception = inner_exception

    def __str__(self):
        base_message = super().__str__()
        details = f" (Command: {self.command_type})" if self.command_type else ""
        inner = f" Caused by: {str(self.inner_exception)}" if self.inner_exception else ""
        return f"{base_message}{details}{inner}"