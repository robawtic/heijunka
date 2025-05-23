from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from infrastructure.api.dependencies import get_db, get_repositories
from infrastructure.api.auth import get_current_user
from presentation.api.models import EmployeeCreate, EmployeeUpdate, EmployeeResponse

router = APIRouter()

@router.get("/", response_model=List[EmployeeResponse])
async def get_employees(
    team_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    role: Optional[str] = None,
    qualification: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all employees with optional filtering."""
    repositories = get_repositories(db)
    employees = repositories["employee_repository"].get_all()
    
    # Apply filters
    if team_id is not None:
        employees = [e for e in employees if e.team_id == team_id]
    if is_active is not None:
        employees = [e for e in employees if e.is_active == is_active]
    if role is not None:
        employees = [e for e in employees if role in e.roles]
    if qualification is not None:
        employees = [e for e in employees if qualification in e.qualifications]
    
    # Apply pagination
    employees = employees[skip:skip+limit]
    
    # Convert to response model
    return [
        EmployeeResponse(
            id=e.id,
            name=e.name,
            roles=e.roles,
            qualifications=e.qualifications,
            is_active=e.is_active,
            team_id=e.team_id,
            team_name=repositories["team_repository"].get_by_id(e.team_id).name,
            created_at=e.created_at,
            updated_at=e.updated_at
        )
        for e in employees
    ]

@router.post("/", response_model=EmployeeResponse, status_code=201)
async def create_employee(
    employee: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new employee."""
    repositories = get_repositories(db)
    
    # Check if team exists
    team = repositories["team_repository"].get_by_id(employee.team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team with ID {employee.team_id} not found")
    
    # Create employee
    new_employee = repositories["employee_repository"].create(
        name=employee.name,
        team_id=employee.team_id,
        roles=employee.roles,
        qualifications=employee.qualifications,
        is_active=employee.is_active
    )
    
    # Return response
    return EmployeeResponse(
        id=new_employee.id,
        name=new_employee.name,
        roles=new_employee.roles,
        qualifications=new_employee.qualifications,
        is_active=new_employee.is_active,
        team_id=new_employee.team_id,
        team_name=team.name,
        created_at=new_employee.created_at,
        updated_at=new_employee.updated_at
    )

@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific employee by ID."""
    repositories = get_repositories(db)
    employee = repositories["employee_repository"].get_by_id(employee_id)
    
    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee with ID {employee_id} not found")
    
    team = repositories["team_repository"].get_by_id(employee.team_id)
    
    return EmployeeResponse(
        id=employee.id,
        name=employee.name,
        roles=employee.roles,
        qualifications=employee.qualifications,
        is_active=employee.is_active,
        team_id=employee.team_id,
        team_name=team.name,
        created_at=employee.created_at,
        updated_at=employee.updated_at
    )

@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    employee_update: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update an employee."""
    repositories = get_repositories(db)
    
    # Check if employee exists
    existing_employee = repositories["employee_repository"].get_by_id(employee_id)
    if not existing_employee:
        raise HTTPException(status_code=404, detail=f"Employee with ID {employee_id} not found")
    
    # Check if team exists if team_id is provided
    team = None
    if employee_update.team_id is not None:
        team = repositories["team_repository"].get_by_id(employee_update.team_id)
        if not team:
            raise HTTPException(status_code=404, detail=f"Team with ID {employee_update.team_id} not found")
    
    # Update employee
    update_data = employee_update.dict(exclude_unset=True)
    updated_employee = repositories["employee_repository"].update(employee_id, update_data)
    
    # Get team name
    if team is None:
        team = repositories["team_repository"].get_by_id(updated_employee.team_id)
    
    # Return response
    return EmployeeResponse(
        id=updated_employee.id,
        name=updated_employee.name,
        roles=updated_employee.roles,
        qualifications=updated_employee.qualifications,
        is_active=updated_employee.is_active,
        team_id=updated_employee.team_id,
        team_name=team.name,
        created_at=updated_employee.created_at,
        updated_at=updated_employee.updated_at
    )

@router.delete("/{employee_id}", status_code=204)
async def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete an employee."""
    repositories = get_repositories(db)
    
    # Check if employee exists
    existing_employee = repositories["employee_repository"].get_by_id(employee_id)
    if not existing_employee:
        raise HTTPException(status_code=404, detail=f"Employee with ID {employee_id} not found")
    
    # Delete employee
    repositories["employee_repository"].delete(employee_id)