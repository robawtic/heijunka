from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi_cache.decorator import cache
from fastapi_cache import FastAPICache

from infrastructure.api.dependencies import get_db, get_repositories
from infrastructure.api.auth import get_current_user
from presentation.api.models import TeamCreate, TeamUpdate, TeamResponse
from infrastructure.config.settings import settings

router = APIRouter()

@router.get("/", response_model=List[TeamResponse])
@cache(expire=settings.cache_ttl_seconds)
async def get_teams(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all teams."""
    repositories = get_repositories(db)
    team_repo = repositories["team_repository"]
    teams = team_repo.get_all()

    # Apply pagination
    teams = teams[skip:skip+limit]

    # Convert to response model
    result = []
    for team in teams:
        # Use optimized query to get team with counts
        team_with_counts = team_repo.get_with_counts(team.id)
        if team_with_counts:
            result.append(
                TeamResponse(
                    id=team.id,
                    name=team.name,
                    description=team.description,
                    employee_count=team_with_counts['employee_count'],
                    workstation_count=team_with_counts['workstation_count'],
                    created_at=team.created_at,
                    updated_at=team.updated_at
                )
            )

    return result

@router.post("/", response_model=TeamResponse, status_code=201)
async def create_team(
    team: TeamCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new team."""
    repositories = get_repositories(db)

    # Check if team with the same name already exists
    existing_team = repositories["team_repository"].get_by_name(team.name)
    if existing_team:
        raise HTTPException(status_code=400, detail=f"Team with name '{team.name}' already exists")

    # Create team
    new_team = repositories["team_repository"].create(
        name=team.name,
        description=team.description
    )

    # Invalidate cache for teams list
    await FastAPICache.clear(namespace="heijunka-cache:")

    # Return response
    return TeamResponse(
        id=new_team.id,
        name=new_team.name,
        description=new_team.description,
        employee_count=0,
        workstation_count=0,
        created_at=new_team.created_at,
        updated_at=new_team.updated_at
    )

@router.get("/{team_id}", response_model=TeamResponse)
@cache(expire=settings.cache_ttl_seconds)
async def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific team by ID."""
    repositories = get_repositories(db)
    team_repo = repositories["team_repository"]

    # Use optimized query to get team with counts
    result = team_repo.get_with_counts(team_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Team with ID {team_id} not found")

    team = result['team']

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        employee_count=result['employee_count'],
        workstation_count=result['workstation_count'],
        created_at=team.created_at,
        updated_at=team.updated_at
    )

@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    team_update: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a team."""
    repositories = get_repositories(db)

    # Check if team exists
    existing_team = repositories["team_repository"].get_by_id(team_id)
    if not existing_team:
        raise HTTPException(status_code=404, detail=f"Team with ID {team_id} not found")

    # Check if team with the same name already exists (if name is being updated)
    if team_update.name is not None and team_update.name != existing_team.name:
        team_with_same_name = repositories["team_repository"].get_by_name(team_update.name)
        if team_with_same_name:
            raise HTTPException(status_code=400, detail=f"Team with name '{team_update.name}' already exists")

    # Update team
    update_data = team_update.dict(exclude_unset=True)
    updated_team = repositories["team_repository"].update(team_id, update_data)

    # Invalidate cache for teams list
    await FastAPICache.clear(namespace="heijunka-cache:")

    # Get team with counts
    team_with_counts = repositories["team_repository"].get_with_counts(team_id)

    # Return response
    return TeamResponse(
        id=updated_team.id,
        name=updated_team.name,
        description=updated_team.description,
        employee_count=team_with_counts['employee_count'],
        workstation_count=team_with_counts['workstation_count'],
        created_at=updated_team.created_at,
        updated_at=updated_team.updated_at
    )

@router.delete("/{team_id}", status_code=204)
async def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a team."""
    repositories = get_repositories(db)

    # Check if team exists
    existing_team = repositories["team_repository"].get_by_id(team_id)
    if not existing_team:
        raise HTTPException(status_code=404, detail=f"Team with ID {team_id} not found")

    # Check if team has employees or workstations
    employees = repositories["employee_repository"].get_by_team_id(team_id)
    workstations = repositories["workstation_repository"].get_by_team_id(team_id)

    if employees:
        raise HTTPException(status_code=400, detail=f"Cannot delete team with ID {team_id} because it has {len(employees)} employees")

    if workstations:
        raise HTTPException(status_code=400, detail=f"Cannot delete team with ID {team_id} because it has {len(workstations)} workstations")

    # Delete team
    repositories["team_repository"].delete(team_id)

    # Invalidate cache for teams list
    await FastAPICache.clear(namespace="heijunka-cache:")
