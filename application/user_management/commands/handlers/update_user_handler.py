from application.shared.interfaces.command_handler import ICommandHandler
from application.shared.exceptions.command_validation_error import CommandExecutionError, CommandValidationError

from domain.contexts.user_management.repositories.interfaces.user_repository import UserRepositoryInterface
from domain.contexts.shared.entities import Role
from application.user_management.commands.update_user_command import UpdateUserCommand

class UpdateUserHandler(ICommandHandler[UpdateUserCommand, bool]):
    """
    Handles updates to a user's profile and roles, enforcing domain constraints
    and ensuring proper persistence.
    """

    def __init__(self, user_repository: UserRepositoryInterface):
        self._user_repository = user_repository

    async def handle(self, cmd: UpdateUserCommand) -> bool:
        user = await self._user_repository.get_by_id(cmd.user_id)
        if not user:
            raise CommandValidationError(f"User {cmd.user_id} not found")

        # update simple fields...
        if cmd.roles is not None:
            user.change_roles(cmd.roles)

        try:
            return await self._user_repository.save(user)
        except Exception as e:
            raise CommandExecutionError(
                f"Failed to update user '{user.username}'",
                command_type="UpdateUserCommand",
                inner_exception=e
            )

