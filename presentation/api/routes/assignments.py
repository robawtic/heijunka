from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from infrastructure.api.dependencies import get_db, get_repositories
from infrastructure.api.auth import get_viewer_user, get_operator_user, get_scheduler_user
from infrastructure.api.pagination import PaginationParams, Page
from infrastructure.audit.audit_logger import get_audit_logger, AuditLogger
from presentation.api.models import AssignmentCreate, AssignmentUpdate, AssignmentResponse, ErrorResponse
from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment

router = APIRouter()

@router.get("/", response_model=Page[AssignmentResponse], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def get_assignments(
    team_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    workstation_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    period: Optional[int] = None,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_viewer_user)
):
    """
    Get all assignments with filtering, sorting, and pagination.

    - **team_id**: Filter by team ID
    - **employee_id**: Filter by employee ID
    - **workstation_id**: Filter by workstation ID
    - **start_date**: Filter by start date (inclusive)
    - **end_date**: Filter by end date (inclusive)
    - **period**: Filter by work period
    - **page**: Page number (starts at 1)
    - **size**: Items per page (default: 50, max: 100)
    - **sort_by**: Sort field(s), format: field:direction (e.g., date:desc,employee_name:asc)
    """
    repositories = get_repositories(db)

    # Get work history entries with filtering at the database level
    work_history, total = repositories["work_history_repository"].get_filtered(
        team_id=team_id,
        employee_id=employee_id,
        workstation_id=workstation_id,
        start_date=start_date,
        end_date=end_date,
        period=period,
        skip=pagination.skip,
        limit=pagination.limit
    )

    # Convert work history entries to assignments
    assignments = []
    for entry in work_history:
        employee = repositories["employee_repository"].get_by_id(entry.employee_id)
        workstation = repositories["workstation_repository"].get_by_id(entry.workstation_id)

        if employee and workstation:
            period_obj = SchedulePeriod(date=entry.worked_date, period=entry.work_period)
            assignment = WorkAssignment(employee=employee, workstation=workstation, period=period_obj)
            assignments.append(assignment)

    # Convert to response model
    items = [
        AssignmentResponse(
            id=i+1,  # Placeholder ID
            employee_id=a.employee.id,
            employee_name=a.employee.name,
            workstation_id=a.workstation.id,
            workstation_name=a.workstation.name,
            date=a.period.date,
            period=a.period.period,
            team_id=a.employee.team_id,
            team_name=repositories["team_repository"].get_by_id(a.employee.team_id).name,
            created_at=None,  # Placeholder
            updated_at=None   # Placeholder
        )
        for i, a in enumerate(assignments)
    ]

    # Return paginated response
    return Page.create(items=items, total=total, params=pagination)

@router.post("/", response_model=AssignmentResponse, status_code=201, responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def create_assignment(
    assignment: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_operator_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Create a new assignment (manual override).

    This endpoint allows operators to manually assign an employee to a workstation for a specific date and period.
    """
    repositories = get_repositories(db)

    # Check if employee exists
    employee = repositories["employee_repository"].get_by_id(assignment.employee_id)
    if not employee:
        raise HTTPException(
            status_code=404, 
            detail=ErrorResponse(
                status_code=404,
                message=f"Employee with ID {assignment.employee_id} not found"
            ).dict()
        )

    # Check if workstation exists
    workstation = repositories["workstation_repository"].get_by_id(assignment.workstation_id)
    if not workstation:
        raise HTTPException(
            status_code=404, 
            detail=ErrorResponse(
                status_code=404,
                message=f"Workstation with ID {assignment.workstation_id} not found"
            ).dict()
        )

    # Check if employee and workstation are in the same team
    if employee.team_id != workstation.team_id:
        raise HTTPException(
            status_code=400, 
            detail=ErrorResponse(
                status_code=400,
                message="Employee and workstation must be in the same team"
            ).dict()
        )

    # Check if employee is qualified for the workstation
    if not employee.can_work(workstation):
        raise HTTPException(
            status_code=400, 
            detail=ErrorResponse(
                status_code=400,
                message=f"Employee {employee.name} is not qualified for workstation {workstation.name}"
            ).dict()
        )

    # Create assignment
    period = SchedulePeriod(date=assignment.date, period=assignment.period)
    work_assignment = WorkAssignment(employee=employee, workstation=workstation, period=period)

    # Save to work history
    entry = repositories["work_history_repository"].create(
        employee_id=employee.id,
        workstation_id=workstation.id,
        worked_date=assignment.date,
        work_period=assignment.period,
        is_temporary=False
    )

    # Get team
    team = repositories["team_repository"].get_by_id(employee.team_id)

    # Log the action
    audit_logger.log_action(
        user=current_user,
        action="create",
        resource_type="assignment",
        resource_id=entry.id if hasattr(entry, 'id') else None,
        details={
            "employee_id": employee.id,
            "employee_name": employee.name,
            "workstation_id": workstation.id,
            "workstation_name": workstation.name,
            "date": assignment.date.isoformat(),
            "period": assignment.period,
            "team_id": team.id,
            "team_name": team.name
        }
    )

    # Return response
    return AssignmentResponse(
        id=entry.id if hasattr(entry, 'id') else 1,  # Use actual ID if available
        employee_id=employee.id,
        employee_name=employee.name,
        workstation_id=workstation.id,
        workstation_name=workstation.name,
        date=assignment.date,
        period=assignment.period,
        team_id=employee.team_id,
        team_name=team.name,
        created_at=None,  # Placeholder
        updated_at=None   # Placeholder
    )

@router.put("/{assignment_id}", response_model=AssignmentResponse, responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def update_assignment(
    assignment_id: int,
    assignment_update: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_operator_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Update an assignment.

    This endpoint allows operators to update an existing assignment, typically to change the assigned employee.
    """
    repositories = get_repositories(db)

    # In a real implementation, you would retrieve the assignment from the database
    # This is a placeholder implementation - in a real app, we would check if the assignment exists

    # Check if employee exists
    employee = repositories["employee_repository"].get_by_id(assignment_update.employee_id)
    if not employee:
        raise HTTPException(
            status_code=404, 
            detail=ErrorResponse(
                status_code=404,
                message=f"Employee with ID {assignment_update.employee_id} not found"
            ).dict()
        )

    # Get workstation (placeholder)
    # In a real implementation, you would get this from the existing assignment
    workstation_id = 1  # Placeholder
    workstation = repositories["workstation_repository"].get_by_id(workstation_id)
    if not workstation:
        raise HTTPException(
            status_code=404, 
            detail=ErrorResponse(
                status_code=404,
                message=f"Workstation with ID {workstation_id} not found"
            ).dict()
        )

    # Check if employee is qualified for the workstation
    if not employee.can_work(workstation):
        raise HTTPException(
            status_code=400, 
            detail=ErrorResponse(
                status_code=400,
                message=f"Employee {employee.name} is not qualified for workstation {workstation.name}"
            ).dict()
        )

    # Get team
    team = repositories["team_repository"].get_by_id(employee.team_id)

    # In a real implementation, you would update the assignment in the database
    # For now, we'll just log the action

    # Log the action
    audit_logger.log_action(
        user=current_user,
        action="update",
        resource_type="assignment",
        resource_id=assignment_id,
        details={
            "employee_id": employee.id,
            "employee_name": employee.name,
            "workstation_id": workstation.id,
            "workstation_name": workstation.name,
            "team_id": team.id,
            "team_name": team.name
        }
    )

    # Return response
    return AssignmentResponse(
        id=assignment_id,
        employee_id=employee.id,
        employee_name=employee.name,
        workstation_id=workstation.id,
        workstation_name=workstation.name,
        date=date.today(),  # Placeholder
        period=1,           # Placeholder
        team_id=employee.team_id,
        team_name=team.name,
        created_at=None,  # Placeholder
        updated_at=None   # Placeholder
    )

@router.delete("/{assignment_id}", status_code=204, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_scheduler_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Delete an assignment.

    This endpoint allows schedulers to delete an existing assignment. This is a sensitive operation
    that should only be performed by users with scheduler privileges.
    """
    repositories = get_repositories(db)

    # In a real implementation, you would retrieve the assignment from the database
    # and check if it exists before deleting it

    # For now, we'll just log the action
    audit_logger.log_action(
        user=current_user,
        action="delete",
        resource_type="assignment",
        resource_id=assignment_id,
        details={"assignment_id": assignment_id}
    )

    # In a real implementation, you would delete the assignment from the database
    # This is a placeholder implementation
    return None
