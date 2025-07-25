"""
System-level exceptions that truly span all bounded contexts.
Keep this minimal - most exceptions should be context-specific.
"""

class SystemError(Exception):
    """
    Base exception for system-level errors that cross bounded contexts.
    Use sparingly - most exceptions should be context-specific.
    """
    pass

class InfrastructureError(SystemError):
    """
    Exception for infrastructure-level failures that affect multiple contexts.
    Examples: Database connection failures, external service outages.
    """
    pass
