"""
Assignment API routes.

This module contains the API routes for managing assignments in the Heijunka system.

The following methods have been implemented in the work_history_repository:
1. get_by_id - Retrieves a work history entry by its ID
2. create - Creates a new work history entry with all fields
3. update_by_id - Updates an existing work history entry by its ID
4. delete_by_id - Deletes a work history entry by its ID

These methods replace the previous workarounds and provide a more robust implementation.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from infrastructure.api.dependencies import get_db, get_repositories
from infrastructure.api.auth import get_viewer_user, get_operator_user, get_scheduler_user
from infrastructure.api.pagination import PaginationParams, Page
from infrastructure.audit.audit_logger import get_audit_logger, AuditLogger
from presentation.api.models import AssignmentCreate, AssignmentUpdate, AssignmentResponse, ErrorResponse
from typing import List as TypeList
from domain.contexts.scheduling.value_objects.schedule_period import SchedulePeriod
from domain.contexts.assignment.value_objects.work_assignment import WorkAssignment

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
            ).model_dump()
        )

    # Check if workstation exists
    workstation = repositories["workstation_repository"].get_by_id(assignment.workstation_id)
    if not workstation:
        raise HTTPException(
            status_code=404, 
            detail=ErrorResponse(
                status_code=404,
                message=f"Workstation with ID {assignment.workstation_id} not found"
            ).model_dump()
        )

    # Check if employee and workstation are in the same team
    if employee.team_id != workstation.team_id:
        raise HTTPException(
            status_code=400, 
            detail=ErrorResponse(
                status_code=400,
                message="Employee and workstation must be in the same team"
            ).model_dump()
        )

    # Check if employee is qualified for the workstation
    if not employee.can_work(workstation):
        raise HTTPException(
            status_code=400, 
            detail=ErrorResponse(
                status_code=400,
                message=f"Employee {employee.name} is not qualified for workstation {workstation.name}"
            ).model_dump()
        )

    # Create assignment
    period = SchedulePeriod(date=assignment.date, period=assignment.period)
    work_assignment = WorkAssignment(employee=employee, workstation=workstation, period=period)

    # Save to work history using the new create method
    work_history_repo = repositories["work_history_repository"]
    entry = work_history_repo.create(
        employee_id=employee.id,
        workstation_id=workstation.id,
        date_obj=assignment.date,
        period=assignment.period,
        is_temporary=True  # Mark as a temporary assignment
    )

    if not entry:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status_code=500,
                message="Failed to create assignment"
            ).model_dump()
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

    # Return response with the actual ID from the entry
    return AssignmentResponse(
        id=getattr(entry, 'id', 0),  # Use actual ID from the entry
        employee_id=employee.id,
        employee_name=employee.name,
        workstation_id=workstation.id,
        workstation_name=workstation.name,
        date=entry.worked_date,
        period=entry.work_period,
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

    # Get the work history entry from the database
    work_history_repo = repositories["work_history_repository"]

    # Use the new get_by_id method
    entry = work_history_repo.get_by_id(assignment_id)

    if not entry:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                status_code=404,
                message=f"Assignment with ID {assignment_id} not found"
            ).model_dump()
        )

    # Check if employee exists
    employee = repositories["employee_repository"].get_by_id(assignment_update.employee_id)
    if not employee:
        raise HTTPException(
            status_code=404, 
            detail=ErrorResponse(
                status_code=404,
                message=f"Employee with ID {assignment_update.employee_id} not found"
            ).model_dump()
        )

    # Get the workstation from the existing assignment
    workstation = repositories["workstation_repository"].get_by_id(entry.workstation_id)
    if not workstation:
        raise HTTPException(
            status_code=404, 
            detail=ErrorResponse(
                status_code=404,
                message=f"Workstation with ID {entry.workstation_id} not found"
            ).model_dump()
        )

    # Check if employee is qualified for the workstation
    if not employee.can_work(workstation):
        raise HTTPException(
            status_code=400, 
            detail=ErrorResponse(
                status_code=400,
                message=f"Employee {employee.name} is not qualified for workstation {workstation.name}"
            ).model_dump()
        )

    # Get team
    team = repositories["team_repository"].get_by_id(employee.team_id)

    # Update the assignment with the new employee
    updated_entry = work_history_repo.update_by_id(
        id=assignment_id,
        employee_id=employee.id
    )

    if not updated_entry:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status_code=500,
                message="Failed to update assignment"
            ).model_dump()
        )

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
            "date": entry.worked_date.isoformat(),
            "period": entry.work_period,
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
        date=entry.worked_date,
        period=entry.work_period,
        team_id=employee.team_id,
        team_name=team.name,
        created_at=None,  # Placeholder
        updated_at=None   # Placeholder
    )

@router.get("/{assignment_id}", response_model=AssignmentResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_viewer_user)
):
    """
    Get a specific assignment by ID.

    This endpoint retrieves a single assignment by its ID.
    """
    repositories = get_repositories(db)

    # Get the work history entry from the database
    work_history_repo = repositories["work_history_repository"]

    # Use the new get_by_id method
    entry = work_history_repo.get_by_id(assignment_id)

    if not entry:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                status_code=404,
                message=f"Assignment with ID {assignment_id} not found"
            ).model_dump()
        )

    # Get the employee and workstation
    employee = repositories["employee_repository"].get_by_id(entry.employee_id)
    workstation = repositories["workstation_repository"].get_by_id(entry.workstation_id)

    if not employee or not workstation:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                status_code=404,
                message="Employee or workstation not found"
            ).model_dump()
        )

    # Get the team
    team = repositories["team_repository"].get_by_id(employee.team_id)

    # Return the assignment
    return AssignmentResponse(
        id=assignment_id,
        employee_id=employee.id,
        employee_name=employee.name,
        workstation_id=workstation.id,
        workstation_name=workstation.name,
        date=entry.worked_date,
        period=entry.work_period,
        team_id=employee.team_id,
        team_name=team.name,
        created_at=None,  # Placeholder
        updated_at=None   # Placeholder
    )

@router.post("/bulk", response_model=TypeList[AssignmentResponse], status_code=201, responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def create_bulk_assignments(
    assignments: TypeList[AssignmentCreate],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_operator_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Create multiple assignments at once.

    This endpoint allows operators to create multiple assignments in a single request.
    """
    repositories = get_repositories(db)
    assignment_repo = repositories["assignment_repository"]

    # Validate all assignments before creating any
    for i, assignment in enumerate(assignments):
        # Check if employee exists
        employee = repositories["employee_repository"].get_by_id(assignment.employee_id)
        if not employee:
            raise HTTPException(
                status_code=404, 
                detail=ErrorResponse(
                    status_code=404,
                    message=f"Employee with ID {assignment.employee_id} not found in assignment {i+1}"
                ).model_dump()
            )

        # Check if workstation exists
        workstation = repositories["workstation_repository"].get_by_id(assignment.workstation_id)
        if not workstation:
            raise HTTPException(
                status_code=404, 
                detail=ErrorResponse(
                    status_code=404,
                    message=f"Workstation with ID {assignment.workstation_id} not found in assignment {i+1}"
                ).model_dump()
            )

        # Check if employee and workstation are in the same team
        if employee.team_id != workstation.team_id:
            raise HTTPException(
                status_code=400, 
                detail=ErrorResponse(
                    status_code=400,
                    message=f"Employee and workstation must be in the same team in assignment {i+1}"
                ).model_dump()
            )

        # Check if employee is qualified for the workstation
        if not employee.can_work(workstation):
            raise HTTPException(
                status_code=400, 
                detail=ErrorResponse(
                    status_code=400,
                    message=f"Employee {employee.name} is not qualified for workstation {workstation.name} in assignment {i+1}"
                ).model_dump()
            )

    # Create all assignments
    work_history_repo = repositories["work_history_repository"]
    created_assignments = []
    for assignment in assignments:
        employee = repositories["employee_repository"].get_by_id(assignment.employee_id)
        workstation = repositories["workstation_repository"].get_by_id(assignment.workstation_id)
        team = repositories["team_repository"].get_by_id(employee.team_id)

        # Create the assignment using the new create method
        entry = work_history_repo.create(
            employee_id=employee.id,
            workstation_id=workstation.id,
            date_obj=assignment.date,
            period=assignment.period,
            is_temporary=True  # Mark as a temporary assignment
        )

        if not entry:
            # If any assignment fails, we should roll back all previous assignments
            # But since we don't have a transaction mechanism in this example, we'll just return an error
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    status_code=500,
                    message="Failed to create assignments"
                ).model_dump()
            )

        # Log the action
        audit_logger.log_action(
            user=current_user,
            action="create",
            resource_type="assignment",
            resource_id=None,  # We don't have the ID yet
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

        # Add to the list of created assignments with the actual ID
        created_assignments.append(
            AssignmentResponse(
                id=getattr(entry, 'id', 0),  # Use the actual ID from the entry
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
        )

    return created_assignments

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

    # Get the work history entry from the database
    work_history_repo = repositories["work_history_repository"]

    # Use the new get_by_id method
    entry = work_history_repo.get_by_id(assignment_id)

    if not entry:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                status_code=404,
                message=f"Assignment with ID {assignment_id} not found"
            ).model_dump()
        )

    # Delete the assignment using the new delete_by_id method
    success = work_history_repo.delete_by_id(assignment_id)

    if not success:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                status_code=500,
                message="Failed to delete assignment"
            ).model_dump()
        )

    # Log the action
    audit_logger.log_action(
        user=current_user,
        action="delete",
        resource_type="assignment",
        resource_id=assignment_id,
        details={"assignment_id": assignment_id}
    )

    return None
