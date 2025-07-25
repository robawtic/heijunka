from dataclasses import dataclass
from typing import Optional
from application.shared_kernel.base_interfaces.query import IQuery

@dataclass
class GetApiKeysQuery(IQuery):
    """
    Query to retrieve API keys for a specific user.
    
    This is a lightweight internal query object used for passing data
    between application layers without validation overhead.
    """
    user_id: int
    include_inactive: bool = False