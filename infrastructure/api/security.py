from secure import SecureHeaders
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

# Initialize SecureHeaders
secure_headers = SecureHeaders(
    csp={
        'default-src': "'self'",
        'script-src': "'self'",
        'style-src': "'self'",
        'img-src': "'self' data:",
        'font-src': "'self'",
        'connect-src': "'self'",
        'frame-src': "'none'",
        'object-src': "'none'",
        'base-uri': "'self'",
        'form-action': "'self'",
    },
    hsts={
        'max-age': 31536000,
        'includeSubDomains': True
    },
    xfo='DENY'
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        secure_headers.framework.fastapi(response)
        
        return response