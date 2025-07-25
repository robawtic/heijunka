from typing import Optional
from application.shared.interfaces.query_handler import IQueryHandler
from application.shared_kernel.common_exceptions.system_error import SystemError
from domain.contexts.user_management.repositories.interfaces.user_repository import UserRepositoryInterface
from application.user_management.queries.get_user_query import GetUserQuery
from application.user_management.queries.dto.user_response import GetUserResponse, UserDto

class GetUserHandler(IQueryHandler[GetUserQuery, GetUserResponse]):
    """
    Handler for retrieving a single user by ID, username, or email.
    This implements the CQRS query handler pattern with proper dependency injection
    and async support.
    """

    def __init__(self, user_repository: UserRepositoryInterface):
        """
        Initialize handler with repository dependency.

        Args:
            user_repository (UserRepositoryInterface): Repository for user queries.
        """
        self._user_repository = user_repository

    async def handle(self, query: GetUserQuery) -> GetUserResponse:
        """
        Handle user retrieval query.

        Args:
            query (GetUserQuery): Query containing user identifier.

        Returns:
            GetUserResponse: Response containing user data or None if not found.

        Raises:
            SystemError: If user retrieval fails.
        """
        try:
            user = None
            
            # Try to get user by ID first (most efficient)
            if query.user_id:
                user = await self._user_repository.get_by_id(query.user_id)
            # Then try by username
            elif query.username:
                user = await self._user_repository.get_by_username(query.username)
            # Finally try by email
            elif query.email:
                user = await self._user_repository.get_by_email(query.email)
            
            if user is None:
                return GetUserResponse(
                    success=True,
                    message="User not found",
                    user=None
                )
            
            # Convert domain entity to DTO
            user_dto = UserDto(
                id=user.id,
                username=user.username,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                roles=[role.name for role in user.roles],
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_login_at=user.last_login_at
            )
            
            return GetUserResponse(
                success=True,
                message="User retrieved successfully",
                user=user_dto
            )
            
        except Exception as e:
            raise SystemError(
                f"Failed to retrieve user: {str(e)}",
                error_code="USER_RETRIEVAL_ERROR"
            )