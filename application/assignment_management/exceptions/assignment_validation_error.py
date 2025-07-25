class AssignmentValidationError(Exception):
    """Validation error specific to assignment management context."""
    
    def __init__(self, message: str, command_type: str = None, validation_errors: list = None):
        super().__init__(message)
        self.command_type = command_type
        self.validation_errors = validation_errors or []
        
    def __str__(self):
        base_message = super().__str__()
        if self.command_type:
            base_message = f"[{self.command_type}] {base_message}"
        if self.validation_errors:
            errors_str = ", ".join(self.validation_errors)
            base_message = f"{base_message} - Validation errors: {errors_str}"
        return base_message