# infrastructure/security/csrf.py
from fastapi import Request, Response, Depends, HTTPException
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import InvalidCsrfToken
from typing import Callable, TypeVar, cast, Optional
from contextlib import contextmanager
import logging

T = TypeVar('T')
logger = logging.getLogger("heijunka_api.security")

class CSRFSecurity:
    """
    A class to encapsulate CSRF security functionality.

    This class provides methods for validating CSRF tokens and setting CSRF cookies.
    It can be used as a dependency in FastAPI routes.

    Example usage:

    # Create a dependency
    csrf_security = Depends(CSRFSecurity)

    # Use in a route (callable syntax)
    @router.post("/endpoint", dependencies=[Depends(CSRFSecurity())])
    async def create_resource(...):
        ...

    # Use in a route (validate method)
    @router.post("/endpoint", dependencies=[Depends(CSRFSecurity().validate)])
    async def create_resource(...):
        ...

    # Set a cookie in a route
    @router.get("/endpoint")
    async def get_resource(response: Response, csrf: CSRFSecurity = Depends()):
        csrf.set_cookie(response)
        ...

    # Use with context manager
    @router.post("/endpoint")
    async def create_resource(response: Response, csrf: CSRFSecurity = Depends()):
        with csrf_protected(response, csrf):
            # Your code here - CSRF is validated before and cookie is set after
            ...
    """

    def __init__(self, csrf_protect: CsrfProtect = Depends()):
        """
        Initialize the CSRFSecurity instance.

        Args:
            csrf_protect: The CsrfProtect instance to use
        """
        self.csrf = csrf_protect

    def __call__(self):
        """
        Make the class callable to support decorator-style usage.

        This allows using the class directly in dependencies:
        @router.post("/endpoint", dependencies=[Depends(CSRFSecurity())])

        Returns:
            The validate method
        """
        return self.validate

    def validate(self):
        """
        Validate the CSRF token in the request.

        Raises:
            HTTPException: If the CSRF token is invalid
        """
        try:
            self.csrf.validate_csrf_in_cookies()
            logger.debug("CSRF token validated successfully")
        except InvalidCsrfToken:
            logger.warning("Invalid CSRF token detected")
            raise HTTPException(status_code=403, detail="Invalid CSRF token")

    def set_cookie(self, response: Response):
        """
        Set a CSRF cookie in the response.

        Args:
            response: The response to set the cookie in
        """
        token = self.csrf.generate_csrf()
        self.csrf.set_csrf_cookie(response, token)
        logger.debug("CSRF cookie set in response")


@contextmanager
def csrf_protected(response: Response, csrf: CSRFSecurity):
    """
    Context manager for CSRF protection lifecycle.

    This context manager validates the CSRF token before executing the code block,
    and sets a new CSRF cookie in the response after the code block completes.

    Args:
        response: The HTTP response to set the cookie in
        csrf: The CSRFSecurity instance

    Example:
        @router.post("/endpoint")
        async def create_resource(response: Response, csrf: CSRFSecurity = Depends()):
            with csrf_protected(response, csrf):
                # Your code here - CSRF is validated before and cookie is set after
                ...

    Raises:
        HTTPException: If the CSRF token is invalid
    """
    # Validate CSRF token before executing the code block
    csrf.validate()
    try:
        # Yield control back to the caller
        yield
    finally:
        # Set a new CSRF cookie in the response after the code block completes
        csrf.set_cookie(response)


# Refactored top-level functions to use the CSRFSecurity class for consistency

def set_csrf_cookie(response: Response, csrf_protect: CsrfProtect = Depends()):
    """
    Set a CSRF cookie in the response.

    This function is a wrapper around CSRFSecurity.set_cookie for backward compatibility.

    Args:
        response: The response to set the cookie in
        csrf_protect: The CsrfProtect instance to use
    """
    csrf = CSRFSecurity(csrf_protect)
    csrf.set_cookie(response)


def verify_csrf_token(request: Request, csrf_protect: CsrfProtect = Depends()):
    """
    Validate the CSRF token in the request, unless the request is from an API client.

    This function is a wrapper around CSRFSecurity.validate for backward compatibility.
    It exempts API clients from CSRF validation.

    Args:
        request: The HTTP request
        csrf_protect: The CsrfProtect instance to use

    Raises:
        HTTPException: If the CSRF token is invalid
    """
    # Import here to avoid circular imports
    from infrastructure.security.api_key import is_api_client

    # Skip CSRF validation for API clients
    if is_api_client(request):
        logger.debug("Skipping CSRF validation for API client")
        return

    # Validate CSRF token for browser clients
    csrf = CSRFSecurity(csrf_protect)
    csrf.validate()
