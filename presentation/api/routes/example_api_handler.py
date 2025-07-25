"""
Example API handler for schedule generation using the new ScheduleService.generate_schedule_flow method.

This is a simplified example that shows how an API handler could use the same
ScheduleService.generate_schedule_flow method that the CLI handler uses.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import date

from infrastructure.api.dependencies import get_db, get_repositories, get_schedule_service
from infrastructure.api.auth import get_scheduler_user
from presentation.api.models import ScheduleCreate, ScheduleResponse, AssignmentInfo, PeriodInfo

# Create a router for this example
example_router = APIRouter()

class ScheduleGenerateRequest:
    """Request model for schedule generation."""
    team: Optional[str] = None
    group: Optional[str] = None
    department: Optional[str] = None
    start_date: date
    periods: int = 4
    call_ins: List[str] = []
    offline: List[str] = []
    force_complete: bool = True

@example_router.post("/generate", response_model=Dict[str, Any])
async def api_generate_schedule(
    request: ScheduleGenerateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_scheduler_user)
):
    """
    Generate a schedule using the ScheduleService.generate_schedule_flow method.

    This is a simplified example that shows how an API handler could use the same
    ScheduleService.generate_schedule_flow method that the CLI handler uses.

    Args:
        request: The schedule generation request
        db: Database session
        current_user: The authenticated user

    Returns:
        A dictionary containing the generated schedule and performance metrics
    """
    # Get repositories and services
    repositories = get_repositories(db)
    schedule_service = get_schedule_service()

    # Call the schedule service to handle all orchestration
    result = schedule_service.generate_schedule_flow_legacy(
        args=request,
        session=db,
        employee_repository=repositories["employee_repository"],
        workstation_repository=repositories["workstation_repository"],
        team_repository=repositories["team_repository"],
        assignment_repository=repositories["assignment_repository"],
        work_history_repository=repositories["work_history_repository"],
        aro_repository=repositories["aro_repository"],
        aro_service=repositories["aro_service"],
        aro_graph_service=repositories["aro_graph_service"],
        schedule_repository=repositories["schedule_repository"]
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    # Convert assignments to response format
    assignments = []
    for assignment in result["assignments"]:
        assignments.append({
            "employee_id": assignment.employee.id,
            "employee_name": assignment.employee.name,
            "workstation_id": assignment.workstation.id,
            "workstation_name": assignment.workstation.name,
            "period": {
                "date": assignment.period.date,
                "period": assignment.period.period
            }
        })

    # Return a response with the generated schedule and performance metrics
    return {
        "success": True,
        "assignments": assignments,
        "teams": [team.name for team in result["teams"]],
        "metrics": result["metrics"]
    }
