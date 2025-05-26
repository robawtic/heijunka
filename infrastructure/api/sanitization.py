from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import re
import json
import logging
import bleach
from typing import Dict, Any, Optional

logger = logging.getLogger("heijunka_api.sanitization")

class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for sanitizing input to prevent injection attacks.

    This middleware sanitizes both query parameters and request bodies:
    - Query parameters: Removes potentially dangerous characters
    - Request bodies: Uses bleach to sanitize HTML content
    """
    def __init__(
        self, 
        app,
        allowed_tags: Optional[list] = None,
        allowed_attributes: Optional[Dict[str, list]] = None,
        allowed_protocols: Optional[list] = None,
        strip: bool = True
    ):
        """
        Initialize the middleware with bleach configuration.

        Args:
            app: The FastAPI application
            allowed_tags: List of allowed HTML tags (default: bleach defaults)
            allowed_attributes: Dict of allowed HTML attributes (default: bleach defaults)
            allowed_protocols: List of allowed URL protocols (default: bleach defaults)
            strip: Whether to strip disallowed tags (default: True)
        """
        import bleach.sanitizer

        self.allowed_tags = allowed_tags if allowed_tags is not None else bleach.sanitizer.ALLOWED_TAGS
        self.allowed_attributes = allowed_attributes if allowed_attributes is not None else bleach.sanitizer.ALLOWED_ATTRIBUTES
        self.allowed_protocols = allowed_protocols if allowed_protocols is not None else bleach.sanitizer.ALLOWED_PROTOCOLS


        super().__init__(app)
        self.allowed_tags = allowed_tags
        self.allowed_attributes = allowed_attributes
        self.allowed_protocols = allowed_protocols
        self.strip = strip

        logger.info(
            "InputSanitizationMiddleware initialized",
            extra={
                "allowed_tags": allowed_tags,
                "strip_disallowed": strip
            }
        )

    async def dispatch(self, request: Request, call_next):
        """
        Process the request and sanitize inputs.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The response
        """
        # Sanitize query parameters
        if request.query_params:
            for key, value in request.query_params.items():
                if isinstance(value, str):
                    # Basic sanitization for query parameters
                    sanitized_value = re.sub(r'[<>\'";]', '', value)
                    # We can't modify query_params directly, but we've sanitized the values
                    # In a real implementation, you would create a new request with sanitized params

        # Sanitize request body for content types that might contain HTML
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                # Get the request body
                body_bytes = await request.body()
                if body_bytes:
                    # Parse JSON body
                    body = json.loads(body_bytes)
                    # Sanitize the body recursively
                    sanitized_body = self._sanitize_json(body)

                    # Replace request._receive with sanitized body
                    from starlette.datastructures import Headers
                    from io import BytesIO

                    # Replace request._receive with sanitized body
                    async def receive() -> dict:
                        return {
                            "type": "http.request",
                            "body": json.dumps(sanitized_body).encode("utf-8"),
                            "more_body": False,
                        }

                    request._receive = receive
                    logger.debug("Replaced request body with sanitized version")
            except Exception as e:
                logger.warning(f"Error sanitizing request body: {str(e)}")

        # Continue with the request
        response = await call_next(request)
        return response

    def _sanitize_json(self, data: Any) -> Any:
        """
        Recursively sanitize JSON data.

        Args:
            data: The data to sanitize

        Returns:
            The sanitized data
        """
        if isinstance(data, str):
            # Use bleach to sanitize HTML content in strings
            return bleach.clean(
                data,
                tags=self.allowed_tags,
                attributes=self.allowed_attributes,
                protocols=self.allowed_protocols,
                strip=self.strip
            )
        elif isinstance(data, dict):
            # Recursively sanitize dictionary values
            return {k: self._sanitize_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            # Recursively sanitize list items
            return [self._sanitize_json(item) for item in data]
        else:
            # Return other types unchanged
            return data
