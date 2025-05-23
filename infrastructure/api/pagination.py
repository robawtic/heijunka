from typing import Generic, TypeVar, List, Optional, Dict, Any
from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar('T')

class PaginationParams:
    """
    Pagination parameters that can be used as a dependency in FastAPI endpoints.
    """
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(50, ge=1, le=100, description="Items per page"),
        sort_by: Optional[str] = Query(None, description="Sort field(s), format: field:direction (e.g., created_at:desc,name:asc)")
    ):
        self.page = page
        self.size = size
        self.sort_by = sort_by
        
    @property
    def skip(self) -> int:
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> int:
        return self.size
    
    def get_sort_params(self) -> List[Dict[str, str]]:
        """
        Parse sort_by string into a list of dictionaries with field and direction.
        Example: "created_at:desc,name:asc" -> [{"field": "created_at", "direction": "desc"}, {"field": "name", "direction": "asc"}]
        """
        if not self.sort_by:
            return []
        
        sort_params = []
        for sort_item in self.sort_by.split(','):
            if ':' in sort_item:
                field, direction = sort_item.split(':', 1)
                if direction.lower() not in ('asc', 'desc'):
                    direction = 'asc'
                sort_params.append({"field": field.strip(), "direction": direction.lower()})
            else:
                sort_params.append({"field": sort_item.strip(), "direction": "asc"})
        
        return sort_params

class PageMetadata(BaseModel):
    """
    Metadata for paginated results.
    """
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Items per page")
    total: int = Field(..., description="Total number of items")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")
    
    class Config:
        json_schema_extra= {
            "example": {
                "page": 1,
                "size": 50,
                "total": 100,
                "pages": 2,
                "has_next": True,
                "has_prev": False
            }
        }

class Page(BaseModel, Generic[T]):
    """
    A paginated response with items and metadata.
    """
    items: List[T]
    metadata: PageMetadata
    
    @classmethod
    def create(cls, items: List[T], total: int, params: PaginationParams) -> 'Page[T]':
        """
        Create a Page instance from a list of items, total count, and pagination parameters.
        """
        pages = (total + params.size - 1) // params.size if params.size > 0 else 0
        
        return cls(
            items=items,
            metadata=PageMetadata(
                page=params.page,
                size=params.size,
                total=total,
                pages=pages,
                has_next=params.page < pages,
                has_prev=params.page > 1
            )
        )