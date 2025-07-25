class ScheduleExecutionError(Exception):
    """Execution error specific to schedule management context."""
    
    def __init__(self, message: str, command_type: str = None, inner_exception: Exception = None):
        super().__init__(message)
        self.command_type = command_type
        self.inner_exception = inner_exception
        
    def __str__(self):
        base_message = super().__str__()
        if self.command_type:
            base_message = f"[{self.command_type}] {base_message}"
        if self.inner_exception:
            base_message = f"{base_message} - Inner exception: {str(self.inner_exception)}"
        return base_message