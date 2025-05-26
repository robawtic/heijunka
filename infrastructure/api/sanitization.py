from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import re

class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for sanitizing input to prevent injection attacks.
    """
    async def dispatch(self, request: Request, call_next):
        # Create a new scope to avoid modifying the original request
        # This is a simplified example - in practice, you'd need to handle
        # the request body more carefully
        
        # For query parameters - sanitize them
        if request.query_params:
            sanitized_params = {}
            for key, value in request.query_params.items():
                if isinstance(value, str):
                    # Remove potentially dangerous characters
                    sanitized_value = re.sub(r'[<>\'";]', '', value)
                    sanitized_params[key] = sanitized_value
            
            # In a real implementation, you would update the query params
            # This is just a placeholder for the concept
        
        # Continue with the request
        response = await call_next(request)
        return response