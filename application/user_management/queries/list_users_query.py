from dataclasses import dataclass
from typing import Optional, List
from application.shared_kernel.base_interfaces.query import IQuery

@dataclass
class ListUsersQuery(IQuery):
    """
    Query to retrieve a list of users with optional filtering and pagination.
    
    This is a lightweight internal query object used for passing data
    between application layers without validation overhead.
    :param page: Which page of results to return (1-based index).
    :param page_size: How many results per page.
    :param is_active: Filter users by active status if provided.
    :param role_name: Only include users with this role if provided.
    :param search_term: Text to search across username, email, first/last name.
    """
    page: int = 1
    page_size: int = 10
    is_active: Optional[bool] = None
    role_name: Optional[str] = None
    search_term: Optional[str] = None  # Search in username, email, first_name, last_name