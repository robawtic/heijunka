from typing import Any, Callable, Awaitable
from pydantic import BaseModel, ValidationError
from .behavior_interface import IBehavior
from application.shared.interfaces.command_handler import ICommand
from application.shared.interfaces.query_handler import IQuery
from application.shared.exceptions.command_validation_error import CommandValidationError
from application.shared.exceptions.query_execution_error import QueryExecutionError, QueryValidationError

class ValidationBehavior(IBehavior):
    """Cross-cutting validation behavior using Pydantic."""

    async def execute(
        self,
        request: Any,
        next_handler: Callable[[Any], Awaitable[Any]]
    ) -> Any:
        """Execute handler with validation."""
        # Validate request if it's a Pydantic model
        if isinstance(request, BaseModel):
            try:
                # Pydantic validation happens automatically on instantiation
                # But we can add custom validation here
                await self._validate_business_rules(request)
            except ValidationError as e:
                # Use proper type checking instead of string matching
                if isinstance(request, ICommand):
                    raise CommandValidationError(
                        f"Validation failed for {type(request).__name__}",
                        command_type=type(request).__name__,
                        validation_errors=e.errors()
                    )
                elif isinstance(request, IQuery):
                    raise QueryValidationError(
                        f"Validation failed for {type(request).__name__}",
                        query_type=type(request).__name__,
                        validation_errors=e.errors()
                    )
                else:
                    # Fallback for requests that don't implement ICommand or IQuery
                    raise ValidationError(e.errors())

        return await next_handler(request)

    async def _validate_business_rules(self, request: Any) -> None:
        """Validate business rules specific to the request."""
        # Custom business validation logic can be added here
        pass
