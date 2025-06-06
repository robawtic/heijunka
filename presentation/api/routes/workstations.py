from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from infrastructure.api.dependencies import get_db, get_repositories
from infrastructure.api.auth import get_current_user
from presentation.api.models import WorkstationCreate, WorkstationUpdate, WorkstationResponse

router = APIRouter()

@router.get("/", response_model=List[WorkstationResponse])
async def get_workstations(
    team_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    required_qualification: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all workstations with optional filtering."""
    repositories = get_repositories(db)
    workstations = repositories["workstation_repository"].get_all()
    
    # Apply filtersFF
    if team_id is not None:
        workstations = [w for w in workstations if w.team_id == team_id]
    if is_active is not None:
        workstations = [w for w in workstations if w.is_active == is_active]
    if required_qualification is not None:
        workstations = [w for w in workstations if required_qualification in w.required_qualifications]
    
    # Apply pagination
    workstations = workstations[skip:skip+limit]
    
    # Convert to response model
    return [
        WorkstationResponse(
            id=w.id,
            name=w.name,
            required_qualifications=w.required_qualifications,
            is_active=w.is_active,
            team_id=w.team_id,
            team_name=repositories["team_repository"].get_by_id(w.team_id).name,
            created_at=w.created_at,
            updated_at=w.updated_at
        )
        for w in workstations
    ]

@router.post("/", response_model=WorkstationResponse, status_code=201)
async def create_workstation(
    workstation: WorkstationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new workstation."""
    repositories = get_repositories(db)
    
    # Check if team exists
    team = repositories["team_repository"].get_by_id(workstation.team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team with ID {workstation.team_id} not found")
    
    # Create workstation
    new_workstation = repositories["workstation_repository"].create(
        name=workstation.name,
        team_id=workstation.team_id,
        required_qualifications=workstation.required_qualifications,
        is_active=workstation.is_active
    )
    
    # Return response
    return WorkstationResponse(
        id=new_workstation.id,
        name=new_workstation.name,
        required_qualifications=new_workstation.required_qualifications,
        is_active=new_workstation.is_active,
        team_id=new_workstation.team_id,
        team_name=team.name,
        created_at=new_workstation.created_at,
        updated_at=new_workstation.updated_at
    )

@router.get("/{workstation_id}", response_model=WorkstationResponse)
async def get_workstation(
    workstation_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific workstation by ID."""
    repositories = get_repositories(db)
    workstation = repositories["workstation_repository"].get_by_id(workstation_id)
    
    if not workstation:
        raise HTTPException(status_code=404, detail=f"Workstation with ID {workstation_id} not found")
    
    team = repositories["team_repository"].get_by_id(workstation.team_id)
    
    return WorkstationResponse(
        id=workstation.id,
        name=workstation.name,
        required_qualifications=workstation.required_qualifications,
        is_active=workstation.is_active,
        team_id=workstation.team_id,
        team_name=team.name,
        created_at=workstation.created_at,
        updated_at=workstation.updated_at
    )

@router.put("/{workstation_id}", response_model=WorkstationResponse)
async def update_workstation(
    workstation_id: int,
    workstation_update: WorkstationUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a workstation."""
    repositories = get_repositories(db)
    
    # Check if workstation exists
    existing_workstation = repositories["workstation_repository"].get_by_id(workstation_id)
    if not existing_workstation:
        raise HTTPException(status_code=404, detail=f"Workstation with ID {workstation_id} not found")
    
    # Check if team exists if team_id is provided
    team = None
    if workstation_update.team_id is not None:
        team = repositories["team_repository"].get_by_id(workstation_update.team_id)
        if not team:
            raise HTTPException(status_code=404, detail=f"Team with ID {workstation_update.team_id} not found")
    
    # Update workstation
    update_data = workstation_update.dict(exclude_unset=True)
    updated_workstation = repositories["workstation_repository"].update(workstation_id, update_data)
    
    # Get team name
    if team is None:
        team = repositories["team_repository"].get_by_id(updated_workstation.team_id)
    
    # Return response
    return WorkstationResponse(
        id=updated_workstation.id,
        name=updated_workstation.name,
        required_qualifications=updated_workstation.required_qualifications,
        is_active=updated_workstation.is_active,
        team_id=updated_workstation.team_id,
        team_name=team.name,
        created_at=updated_workstation.created_at,
        updated_at=updated_workstation.updated_at
    )

@router.delete("/{workstation_id}", status_code=204)
async def delete_workstation(
    workstation_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a workstation."""
    repositories = get_repositories(db)
    
    # Check if workstation exists
    existing_workstation = repositories["workstation_repository"].get_by_id(workstation_id)
    if not existing_workstation:
        raise HTTPException(status_code=404, detail=f"Workstation with ID {workstation_id} not found")
    
    # Delete workstation
    repositories["workstation_repository"].delete(workstation_id)