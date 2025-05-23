class RepositoryError(Exception):
    """Custom exception for repository operations.

    Attributes:
        message -- explanation of the error
        code -- optional error code
        details -- optional dictionary with additional error details
    """
    def __init__(self, message: str, code: str = None, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        error_msg = self.message
        if self.code:
            error_msg = f"[{self.code}] {error_msg}"
        if self.details:
            error_msg = f"{error_msg} - Details: {self.details}"
        return error_msg