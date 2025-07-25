class QueryExecutionError(Exception):
    """Raised when query execution fails."""
    
    def __init__(self, message: str, query_type: str = None, inner_exception: Exception = None):
        super().__init__(message)
        self.query_type = query_type
        self.inner_exception = inner_exception

class QueryValidationError(Exception):
    """Raised when query validation fails."""
    
    def __init__(self, message: str, query_type: str = None, validation_errors: dict = None):
        super().__init__(message)
        self.query_type = query_type
        self.validation_errors = validation_errors or {}
