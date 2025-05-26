from pydantic import BaseModel, Field, EmailStr, validator, constr
from typing import List, Optional, Dict, Any, Union
from datetime import date, datetime
from enum import Enum
import re

# User models
class UserBase(BaseModel):
    username: constr(min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$') = Field(
        ..., 
        description="Username (3-50 chars, alphanumeric, underscore, hyphen only)"
    )
    email: Optional[EmailStr] = Field(
        None, 
        description="Email address"
    )

    # Validate username to prevent injection attacks
    @validator('username')
    def username_must_be_valid(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username contains invalid characters')
        return v

class UserCreate(UserBase):
    password: constr(min_length=8, max_length=64) = Field(
        ..., 
        description="Password (min 8 chars)"
    )
    roles: List[str] = Field(
        default_factory=list,
        description="User roles"
    )

    # Validate password strength
    @validator('password')
    def password_strength(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError('Password must contain at least one special character')
        return v

    # Validate roles
    @validator('roles', each_item=True)
    def validate_roles(cls, v):
        valid_roles = ['admin', 'scheduler', 'operator', 'viewer']
        if v not in valid_roles:
            raise ValueError(f'Invalid role: {v}. Must be one of {valid_roles}')
        return v

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[constr(min_length=8, max_length=64)] = None
    is_active: Optional[bool] = None
    roles: Optional[List[str]] = None

    # Reuse password validator if password is provided
    @validator('password')
    def password_strength(cls, v):
        if v is None:
            return v
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError('Password must contain at least one special character')
        return v

    # Validate roles if provided
    @validator('roles', each_item=True)
    def validate_roles(cls, v):
        valid_roles = ['admin', 'scheduler', 'operator', 'viewer']
        if v not in valid_roles:
            raise ValueError(f'Invalid role: {v}. Must be one of {valid_roles}')
        return v

class UserResponse(BaseResponse, UserBase):
    id: int
    is_active: bool
    roles: List[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "johndoe",
                "email": "john.doe@example.com",
                "is_active": True,
                "roles": ["operator", "viewer"],
                "created_at": "2023-01-15T10:30:00",
                "updated_at": "2023-01-15T10:30:00",
                "last_login": "2023-01-15T10:30:00"
            }
        }

class UserMeResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    roles: List[str]
    is_active: bool
    last_login: Optional[datetime]

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "johndoe",
                "email": "john.doe@example.com",
                "is_active": True,
                "roles": ["operator", "viewer"],
                "last_login": "2023-01-15T10:30:00"
            }
        }

# Enhanced login models
class TokenRequest(BaseModel):
    username: constr(min_length=3, max_length=50) = Field(..., description="Username")
    password: constr(min_length=1) = Field(..., description="Password")

    # Sanitize inputs
    @validator('username')
    def sanitize_username(cls, v):
        return re.sub(r'[<>\'";]', '', v)

    @validator('password')
    def sanitize_password(cls, v):
        return re.sub(r'[<>\'";]', '', v)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    csrf_token: Optional[str] = None

class CSRFTokenResponse(BaseModel):
    """
    Response model for CSRF token endpoint.

    This is used by the frontend to get a CSRF token for subsequent requests.
    """
    csrf_token: str

# Error response models
class ErrorDetail(BaseModel):
    loc: Optional[List[str]] = None
    msg: str
    type: str

    class Config:
        json_schema_extra= {
            "example": {
                "loc": ["body", "name"],
                "msg": "field required",
                "type": "value_error.missing"
            }
        }

class ErrorResponse(BaseModel):
    status_code: int
    message: str
    details: Optional[Union[List[ErrorDetail], Dict[str, Any]]] = None

    class Config:
        json_schema_extra= {
            "example": {
                "status_code": 400,
                "message": "Bad Request",
                "details": [
                    {
                        "loc": ["body", "name"],
                        "msg": "field required",
                        "type": "value_error.missing"
                    }
                ]
            }
        }

# Base models
class BaseResponse(BaseModel):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Employee models
class EmployeeBase(BaseModel):
    name: str
    roles: List[str] = []
    qualifications: List[str] = []
    is_active: bool = True

    class Config:
        json_schema_extra= {
            "example": {
                "name": "John Doe",
                "roles": ["operator", "trainer"],
                "qualifications": ["assembly", "testing"],
                "is_active": True
            }
        }

class EmployeeCreate(EmployeeBase):
    team_id: int

    class Config:
        json_schema_extra= {
            "example": {
                "name": "John Doe",
                "roles": ["operator", "trainer"],
                "qualifications": ["assembly", "testing"],
                "is_active": True,
                "team_id": 1
            }
        }

class EmployeeUpdate(EmployeeBase):
    name: Optional[str] = None
    team_id: Optional[int] = None

    class Config:
        json_schema_extra= {
            "example": {
                "name": "John Smith",
                "roles": ["operator", "supervisor"],
                "qualifications": ["assembly", "testing", "quality"],
                "is_active": True,
                "team_id": 2
            }
        }

class EmployeeResponse(BaseResponse, EmployeeBase):
    team_id: int
    team_name: str

    class Config:
        json_schema_extra= {
            "example": {
                "id": 1,
                "name": "John Doe",
                "roles": ["operator", "trainer"],
                "qualifications": ["assembly", "testing"],
                "is_active": True,
                "team_id": 1,
                "team_name": "Assembly Team",
                "created_at": "2023-01-15T10:30:00",
                "updated_at": "2023-01-15T10:30:00"
            }
        }

# Workstation models
class WorkstationBase(BaseModel):
    name: str
    required_qualifications: List[str] = []
    is_active: bool = True

    class Config:
        json_schema_extra= {
            "example": {
                "name": "Assembly Station 1",
                "required_qualifications": ["assembly", "soldering"],
                "is_active": True
            }
        }

class WorkstationCreate(WorkstationBase):
    team_id: int

    class Config:
        json_schema_extra= {
            "example": {
                "name": "Assembly Station 1",
                "required_qualifications": ["assembly", "soldering"],
                "is_active": True,
                "team_id": 1
            }
        }

class WorkstationUpdate(WorkstationBase):
    name: Optional[str] = None
    team_id: Optional[int] = None

    class Config:
        json_schema_extra= {
            "example": {
                "name": "Assembly Station 1A",
                "required_qualifications": ["assembly", "soldering", "inspection"],
                "is_active": True,
                "team_id": 1
            }
        }

class WorkstationResponse(BaseResponse, WorkstationBase):
    team_id: int
    team_name: str

    class Config:
        json_schema_extra= {
            "example": {
                "id": 1,
                "name": "Assembly Station 1",
                "required_qualifications": ["assembly", "soldering"],
                "is_active": True,
                "team_id": 1,
                "team_name": "Assembly Team",
                "created_at": "2023-01-15T10:30:00",
                "updated_at": "2023-01-15T10:30:00"
            }
        }

# Team models
class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None

    class Config:
        json_schema_extra= {
            "example": {
                "name": "Assembly Team",
                "description": "Team responsible for product assembly"
            }
        }

class TeamCreate(TeamBase):
    pass

    class Config:
        json_schema_extra= {
            "example": {
                "name": "Assembly Team",
                "description": "Team responsible for product assembly"
            }
        }

class TeamUpdate(TeamBase):
    name: Optional[str] = None

    class Config:
        json_schema_extra= {
            "example": {
                "name": "Assembly Team Alpha",
                "description": "Team responsible for high-precision product assembly"
            }
        }

class TeamResponse(BaseResponse, TeamBase):
    employee_count: int
    workstation_count: int

    class Config:
        json_schema_extra= {
            "example": {
                "id": 1,
                "name": "Assembly Team",
                "description": "Team responsible for product assembly",
                "employee_count": 12,
                "workstation_count": 8,
                "created_at": "2023-01-15T10:30:00",
                "updated_at": "2023-01-15T10:30:00"
            }
        }

# Schedule models
class ScheduleBase(BaseModel):
    team_id: int
    start_date: date
    periods_per_day: int = 4
    call_ins: Optional[List[str]] = None
    offline: Optional[List[str]] = None
    force_complete: bool = False

    class Config:
        json_schema_extra= {
            "example": {
                "team_id": 1,
                "start_date": "2023-06-01",
                "periods_per_day": 4,
                "call_ins": ["John Doe", "Jane Smith"],
                "offline": ["Assembly Station 3"],
                "force_complete": False
            }
        }

class ScheduleCreate(ScheduleBase):
    """
    Model for creating a new schedule.

    - team_id: ID of the team for which to create the schedule
    - start_date: First date of the schedule
    - periods_per_day: Number of work periods per day (default: 4)
    - call_ins: List of employee names who are calling in (optional)
    - offline: List of workstation names that are offline (optional)
    - force_complete: Whether to force completion even if not all constraints can be satisfied (default: False)
    """
    pass

    class Config:
        json_schema_extra= {
            "example": {
                "team_id": 1,
                "start_date": "2023-06-01",
                "periods_per_day": 4,
                "call_ins": ["John Doe", "Jane Smith"],
                "offline": ["Assembly Station 3"],
                "force_complete": False
            }
        }

class ScheduleUpdate(BaseModel):
    call_ins: Optional[List[str]] = None
    offline: Optional[List[str]] = None
    force_complete: Optional[bool] = None

    class Config:
        json_schema_extra= {
            "example": {
                "call_ins": ["John Doe", "Jane Smith", "Bob Johnson"],
                "offline": ["Assembly Station 3", "Assembly Station 5"],
                "force_complete": True
            }
        }

class PeriodInfo(BaseModel):
    date: date
    period: int

    class Config:
        json_schema_extra= {
            "example": {
                "date": "2023-06-01",
                "period": 2
            }
        }

class AssignmentInfo(BaseModel):
    employee_id: int
    employee_name: str
    workstation_id: int
    workstation_name: str
    period: PeriodInfo

    class Config:
        json_schema_extra= {
            "example": {
                "employee_id": 1,
                "employee_name": "John Doe",
                "workstation_id": 3,
                "workstation_name": "Assembly Station 3",
                "period": {
                    "date": "2023-06-01",
                    "period": 2
                }
            }
        }

class ScheduleResponse(BaseResponse, ScheduleBase):
    """
    Model for schedule response.

    - id: Unique identifier for the schedule
    - team_id: ID of the team for which the schedule was created
    - team_name: Name of the team
    - start_date: First date of the schedule
    - periods_per_day: Number of work periods per day
    - call_ins: List of employee names who called in
    - offline: List of workstation names that were offline
    - force_complete: Whether completion was forced even if not all constraints could be satisfied
    - assignments: List of work assignments in the schedule
    - status: Current status of the schedule (pending, running, completed, failed)
    - error_message: Error message if the schedule generation failed
    - task_id: ID of the background task that generated the schedule
    - created_at: When the schedule was created
    - updated_at: When the schedule was last updated
    """
    team_name: str
    assignments: List[AssignmentInfo]
    status: str = "completed"
    error_message: Optional[str] = None
    task_id: Optional[str] = None

    class Config:
        json_schema_extra= {
            "example": {
                "id": 1,
                "team_id": 1,
                "team_name": "Assembly Team",
                "start_date": "2023-06-01",
                "periods_per_day": 4,
                "call_ins": ["John Doe", "Jane Smith"],
                "offline": ["Assembly Station 3"],
                "force_complete": False,
                "assignments": [
                    {
                        "employee_id": 1,
                        "employee_name": "John Doe",
                        "workstation_id": 3,
                        "workstation_name": "Assembly Station 3",
                        "period": {
                            "date": "2023-06-01",
                            "period": 2
                        }
                    },
                    {
                        "employee_id": 2,
                        "employee_name": "Jane Smith",
                        "workstation_id": 4,
                        "workstation_name": "Assembly Station 4",
                        "period": {
                            "date": "2023-06-01",
                            "period": 2
                        }
                    },
                    {
                        "employee_id": 3,
                        "employee_name": "Bob Johnson",
                        "workstation_id": 5,
                        "workstation_name": "Quality Control",
                        "period": {
                            "date": "2023-06-01",
                            "period": 3
                        }
                    }
                ],
                "status": "completed",
                "error_message": None,
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "created_at": "2023-06-01T08:30:00",
                "updated_at": "2023-06-01T08:35:00"
            }
        }

# Assignment models
class AssignmentBase(BaseModel):
    employee_id: int
    workstation_id: int
    date: date
    period: int

    class Config:
        json_schema_extra= {
            "example": {
                "employee_id": 1,
                "workstation_id": 3,
                "date": "2023-06-01",
                "period": 2
            }
        }

class AssignmentCreate(AssignmentBase):
    pass

    class Config:
        json_schema_extra= {
            "example": {
                "employee_id": 1,
                "workstation_id": 3,
                "date": "2023-06-01",
                "period": 2
            }
        }

class ManualAssignmentCreate(AssignmentBase):
    """
    Model for creating a manual assignment.

    - employee_id: ID of the employee to assign
    - workstation_id: ID of the workstation to assign to
    - date: Date of the assignment
    - period: Work period of the day (1-4 typically)
    - schedule_id: Optional ID of the schedule this assignment belongs to
    """
    schedule_id: Optional[int] = None

    class Config:
        json_schema_extra= {
            "example": {
                "employee_id": 1,
                "workstation_id": 3,
                "date": "2023-06-01",
                "period": 2,
                "schedule_id": 5
            }
        }

class AssignmentUpdate(BaseModel):
    employee_id: Optional[int] = None

    class Config:
        json_schema_extra= {
            "example": {
                "employee_id": 2
            }
        }

class AssignmentResponse(BaseResponse, AssignmentBase):
    employee_name: str
    workstation_name: str
    team_id: int
    team_name: str

    class Config:
        json_schema_extra= {
            "example": {
                "id": 1,
                "employee_id": 1,
                "employee_name": "John Doe",
                "workstation_id": 3,
                "workstation_name": "Assembly Station 3",
                "date": "2023-06-01",
                "period": 2,
                "team_id": 1,
                "team_name": "Assembly Team",
                "created_at": "2023-06-01T08:30:00",
                "updated_at": "2023-06-01T08:30:00"
            }
        }

# Status models
class SystemStatus(BaseModel):
    status: str
    version: str
    database_connection: bool
    uptime: str

    class Config:
        json_schema_extra= {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "database_connection": True,
                "uptime": "2d 3h 45m 12s"
            }
        }
