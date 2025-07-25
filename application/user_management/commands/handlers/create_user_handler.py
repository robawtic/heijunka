from application.shared.interfaces.command_handler import ICommandHandler
from application.shared.exceptions.command_validation_error import CommandExecutionError
from domain.contexts.user_management.repositories.interfaces.user_repository import UserRepositoryInterface
from domain.contexts.user_management.entities.user import User
from domain.contexts.shared.entities import Role
from application.user_management.commands.create_user_command import CreateUserCommand


class CreateUserHandler(ICommandHandler[CreateUserCommand, int]):
    """
    Handler for creating users, integrating with the UserRepositoryInterface.
    This implements the CQRS handler pattern with proper dependency injection
    and async support.
    """

    def __init__(self, user_repository: UserRepositoryInterface):
        """
        Initialize handler with repository dependency.

        Args:
            user_repository (UserRepositoryInterface): Repository for user persistence.
        """
        self._user_repository = user_repository

    async def handle(self, command: CreateUserCommand) -> int:
        """
        Handle user creation command.

        Args:
            command (CreateUserCommand): Command containing user data.

        Returns:
            int: The ID of the created user.

        Raises:
            CommandExecutionError: If user creation fails.
        """
        user = User(
            username=command.username,
            email=command.email,
            first_name=command.first_name,
            last_name=command.last_name,
            is_active=True
        )

        user.set_password(command.password)

        for role_name in command.roles:
            user.add_role(Role(name=role_name))

        try:
            user_id = await self._user_repository.save(user)
            return user_id
        except Exception as e:
            raise CommandExecutionError(
                f"Failed to create user '{command.username}'",
                command_type="CreateUserCommand",
                inner_exception=e
            )
