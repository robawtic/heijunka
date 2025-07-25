from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

from application.shared.interfaces.command_handler import ICommand

@dataclass
class UpdateUserCommand(ICommand):
    """
    Command to update an existing user's profile and roles.

    Used to encapsulate changes to a user's state in a safe and structured way.
    """
    user_id: int
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: Optional[List[str]] = field(default_factory=list)
    updated_at: Optional[datetime] = None
