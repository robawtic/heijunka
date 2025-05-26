from secure import Secure
from secure.headers import ContentSecurityPolicy, StrictTransportSecurity, XFrameOptions
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

# Initialize Secure with security headers
csp = ContentSecurityPolicy().default_src("'self'").script_src("'self'").style_src("'self'").img_src("'self'", "data:").font_src("'self'").connect_src("'self'").frame_src("'none'").object_src("'none'").base_uri("'self'").form_action("'self'")

hsts = StrictTransportSecurity().max_age(31536000).include_subdomains()

xfo = XFrameOptions().deny()

secure_headers = Secure(
    csp=csp,
    hsts=hsts,
    xfo=xfo
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
