from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from application.shared.dto.base_dto import BaseRequest
from .create_user_command import CreateUserCommand

class CreateUserRequest(BaseRequest):
    """
    Pydantic model for user creation request validation.
    
    This DTO handles boundary validation and converts to internal command objects.
    Rich field descriptions automatically generate comprehensive API documentation.
    """
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50,
        description="Unique username for the user (3-50 characters)",
        examples=["john_doe"]
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Secure password meeting complexity requirements",
        examples=["SecurePass123!"]
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Valid email address for notifications and login",
        examples=["john.doe@company.com"]
    )
    first_name: Optional[str] = Field(
        None, 
        max_length=100,
        description="User's first name",
        examples=["John"]
    )
    last_name: Optional[str] = Field(
        None, 
        max_length=100,
        description="User's last name", 
        examples=["Doe"]
    )
    roles: List[str] = Field(
        default_factory=list,
        description="List of role names to assign to the user",
        examples=[["user", "employee"]]
    )
    
    def to_command(self) -> CreateUserCommand:
        """
        Convert validated DTO to internal command.
        
        This method centralizes the mapping logic and isolates field name changes.
        """
        return CreateUserCommand(
            username=self.username,
            email=self.email,
            password=self.password,
            first_name=self.first_name,
            last_name=self.last_name,
            roles=self.roles
        )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "username": "john_doe",
                    "email": "john.doe@company.com",
                    "password": "SecurePass123!",
                    "first_name": "John",
                    "last_name": "Doe",
                    "roles": ["user", "employee"]
                }
            ]
        }