from dataclasses import dataclass
from typing import Optional
from application.shared_kernel.base_interfaces.query import IQuery

@dataclass
class GetUserQuery(IQuery):
    """
    Query to retrieve a single user by ID, username, or email.
    
    This is a lightweight internal query object used for passing data
    between application layers without validation overhead.
    """
    user_id: Optional[int] = None
    username: Optional[str] = None
    email: Optional[str] = None
    
    def __post_init__(self):
        """Validate that at least one identifier is provided."""
        if not any([self.user_id, self.username, self.email]):
            raise ValueError("At least one identifier (user_id, username, or email) must be provided")