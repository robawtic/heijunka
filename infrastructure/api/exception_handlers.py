from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from jose.exceptions import JWTError

from infrastructure.exceptions import RepositoryError
from presentation.api.models import ErrorResponse, ErrorDetail

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors from FastAPI's request validation.
    """
    details = []
    for error in exc.errors():
        details.append(ErrorDetail(
            loc=error.get("loc", []),
            msg=error.get("msg", ""),
            type=error.get("type", "")
        ))
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Validation Error",
            details=details
        ).dict()
    )

async def repository_exception_handler(request: Request, exc: RepositoryError):
    """
    Handle custom repository exceptions.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=str(exc),
            details={"code": exc.code} if exc.code else None
        ).dict()
    )

async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    Handle SQLAlchemy database exceptions.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Database Error",
            details={"error": str(exc)}
        ).dict()
    )

async def jwt_exception_handler(request: Request, exc: JWTError):
    """
    Handle JWT authentication exceptions.
    """
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=ErrorResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Authentication Error",
            details={"error": str(exc)}
        ).dict(),
        headers={"WWW-Authenticate": "Bearer"}
    )

async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle any unhandled exceptions.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Internal Server Error",
            details={"error": str(exc)}
        ).dict()
    )