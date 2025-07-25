
class CommandValidationError(Exception):
    """Raised when command validation fails."""

    def __init__(self, message: str, command_type: str = None, validation_errors: dict = None):
        super().__init__(message)
        self.command_type = command_type
        self.validation_errors = validation_errors or {}

    def __str__(self):
        base = super().__str__()
        context = f"[Command: {self.command_type}]" if self.command_type else ""
        errors = f"[Validation Errors: {self.validation_errors}]" if self.validation_errors else ""
        return " ".join(part for part in [base, context, errors] if part)


class CommandExecutionError(Exception):
    """Raised when command execution fails."""

    def __init__(self, message: str, command_type: str = None, inner_exception: Exception = None):
        super().__init__(message)
        self.command_type = command_type
        self.inner_exception = inner_exception

    def __str__(self):
        parts = [super().__str__()]
        if self.command_type:
            parts.append(f"[Command: {self.command_type}]")
        if self.inner_exception:
            parts.append(f"[Caused by: {self.inner_exception}]")
        return " ".join(parts)
