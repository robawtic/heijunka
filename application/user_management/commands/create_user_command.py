from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

from application.shared.interfaces.command_handler import ICommand

@dataclass
class CreateUserCommand(ICommand):
    """
    Command to create a new user in the system.

    This is a lightweight internal command object used for passing data
    between application layers without validation overhead.
    """
    username: str
    password: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None