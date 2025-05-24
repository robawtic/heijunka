from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date
import asyncio
from fastapi_cache.decorator import cache

from infrastructure.api.dependencies import get_db, get_repositories, get_schedule_service
from infrastructure.api.auth import get_scheduler_user, get_operator_user, get_viewer_user
from infrastructure.api.pagination import PaginationParams, Page
from infrastructure.tasks.task_manager import task_manager, TaskStatus
from infrastructure.config.settings import settings
from presentation.api.models import ScheduleCreate, ScheduleUpdate, ScheduleResponse, AssignmentInfo, PeriodInfo, ErrorResponse, ManualAssignmentCreate
from application.commands.generate_schedule_command import GenerateScheduleCommand
from application.commands.generate_schedule_handler import GenerateScheduleHandler

router = APIRouter()

async def generate_schedule_async(
    schedule_data: Dict[str, Any],
    db: Session
) -> Dict[str, Any]:
    """
    Async function to generate a schedule.

    Args:
        schedule_data: Schedule data
        db: Database session

    Returns:
        Dictionary with schedule ID and assignments
    """
    # This would normally be a blocking operation, so we run it in a thread pool
    repositories = get_repositories(db)
    schedule_service = get_schedule_service()

    # Create handler
    handler = GenerateScheduleHandler(
        employee_repository=repositories["employee_repository"],
        workstation_repository=repositories["workstation_repository"],
        team_repository=repositories["team_repository"],
        assignment_repository=repositories["assignment_repository"],
        schedule_service=schedule_service,
        session=db
    )

    # Create command
    command = GenerateScheduleCommand(
        team_id=schedule_data["team_id"],
        start_date=schedule_data["start_date"],
        days=schedule_data["days"],
        periods_per_day=schedule_data["periods_per_day"],
        call_ins=schedule_data.get("call_ins"),
        offline=schedule_data.get("offline"),
        force_complete=schedule_data.get("force_complete", False)
    )

    # Run the blocking operation in a thread pool
    loop = asyncio.get_event_loop()
    assignments = await loop.run_in_executor(
        None, 
        lambda: handler.handle(command)
    )

    # In a real implementation, you would update the schedule in the database
    # For now, we'll just return the schedule ID and assignments
    return {
        "schedule_id": schedule_data.get("id", 1),  # Placeholder
        "assignments": assignments
    }

@router.post("/", response_model=ScheduleResponse, status_code=202, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def create_schedule(
    schedule: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_scheduler_user)
):
    """
    Generate a new schedule asynchronously.

    The schedule generation will be performed in the background. The response includes a task_id
    that can be used to check the status of the generation process.
    """
    repositories = get_repositories(db)

    # Check if team exists
    team = repositories["team_repository"].get_by_id(schedule.team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team with ID {schedule.team_id} not found")

    # Create a new schedule record in the database
    schedule_repo = repositories["schedule_repository"]
    new_schedule = schedule_repo.create(
        team_id=schedule.team_id,
        start_date=schedule.start_date,
        days=schedule.days,
        periods_per_day=schedule.periods_per_day,
        call_ins=schedule.call_ins,
        offline=schedule.offline,
        force_complete=schedule.force_complete
    )

    # Convert Pydantic model to dict for the task
    schedule_data = schedule.dict()
    schedule_data["id"] = new_schedule.id

    # Create a background task
    task_id = await task_manager.create_task(
        name="generate_schedule",
        func=generate_schedule_async,
        schedule_data=schedule_data,
        db=db
    )

    # Update the schedule with the task ID
    schedule_repo.update(new_schedule.id, task_id=task_id)

    # Return response immediately
    return ScheduleResponse(
        id=new_schedule.id,
        team_id=schedule.team_id,
        team_name=team.name,
        start_date=schedule.start_date,
        days=schedule.days,
        periods_per_day=schedule.periods_per_day,
        call_ins=schedule.call_ins,
        offline=schedule.offline,
        force_complete=schedule.force_complete,
        assignments=[],  # Empty for now, will be populated by the background task
        status="pending",
        created_at=new_schedule.created_at,
        updated_at=new_schedule.updated_at,
        task_id=task_id  # Include the task ID in the response
    )

@router.get("/task/{task_id}", response_model=ScheduleResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def get_schedule_by_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_viewer_user)
):
    """
    Get a schedule by its task ID.

    This endpoint is useful for checking the status of a schedule generation task.
    """
    # Get the task
    task = task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")

    # Get the repositories
    repositories = get_repositories(db)
    schedule_repo = repositories["schedule_repository"]

    # Get the schedule from the database
    schedule = schedule_repo.get_by_task_id(task_id)
    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule with task ID {task_id} not found")

    team = repositories["team_repository"].get_by_id(schedule.team_id)

    # Get assignments for this schedule
    assignment_repo = repositories["assignment_repository"]
    assignments_data = assignment_repo.get_by_schedule_id(schedule.id)

    # Convert assignments to response format
    assignments = []
    for assignment in assignments_data:
        employee = repositories["employee_repository"].get_by_id(assignment.employee_id)
        workstation = repositories["workstation_repository"].get_by_id(assignment.workstation_id)

        assignments.append(
            AssignmentInfo(
                employee_id=employee.id,
                employee_name=employee.name,
                workstation_id=workstation.id,
                workstation_name=workstation.name,
                period=PeriodInfo(
                    date=assignment.assignment_date,
                    period=assignment.period
                )
            )
        )

    # Map task status to schedule status
    status_map = {
        TaskStatus.PENDING: "pending",
        TaskStatus.RUNNING: "running",
        TaskStatus.COMPLETED: "completed",
        TaskStatus.FAILED: "failed"
    }

    # Create error message if task failed
    error_message = task.error if task.status == TaskStatus.FAILED else None

    return ScheduleResponse(
        id=schedule.id,
        team_id=schedule.team_id,
        team_name=team.name,
        start_date=schedule.start_date,
        days=schedule.days,
        periods_per_day=schedule.periods_per_day,
        call_ins=schedule.call_ins,
        offline=schedule.offline,
        force_complete=schedule.force_complete,
        assignments=assignments,
        status=status_map.get(task.status, "unknown"),
        error_message=error_message,
        task_id=task_id,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at
    )

@router.get("/{schedule_id}", response_model=ScheduleResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def get_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_viewer_user)
):
    """Get a specific schedule."""
    repositories = get_repositories(db)
    schedule_repo = repositories["schedule_repository"]

    # Get the schedule from the database
    schedule = schedule_repo.get_by_id(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule with ID {schedule_id} not found")

    team = repositories["team_repository"].get_by_id(schedule.team_id)

    # Get assignments for this schedule
    assignment_repo = repositories["assignment_repository"]
    assignments_data = assignment_repo.get_by_schedule_id(schedule.id)

    # Convert assignments to response format
    assignments = []
    for assignment in assignments_data:
        employee = repositories["employee_repository"].get_by_id(assignment.employee_id)
        workstation = repositories["workstation_repository"].get_by_id(assignment.workstation_id)

        assignments.append(
            AssignmentInfo(
                employee_id=employee.id,
                employee_name=employee.name,
                workstation_id=workstation.id,
                workstation_name=workstation.name,
                period=PeriodInfo(
                    date=assignment.assignment_date,
                    period=assignment.period
                )
            )
        )

    return ScheduleResponse(
        id=schedule.id,
        team_id=schedule.team_id,
        team_name=team.name,
        start_date=schedule.start_date,
        days=schedule.days,
        periods_per_day=schedule.periods_per_day,
        call_ins=schedule.call_ins,
        offline=schedule.offline,
        force_complete=schedule.force_complete,
        assignments=assignments,
        status=schedule.status,
        error_message=schedule.error_message,
        task_id=schedule.task_id,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at
    )

@router.post("/assignments/manual", response_model=AssignmentInfo, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
async def create_manual_assignment(
    assignment: ManualAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_operator_user)
):
    """
    Create a manual assignment for an employee at a workstation.

    This endpoint allows operators to manually assign an employee to a workstation for a specific period.
    The assignment is marked as temporary and not generated by the scheduler.

    ## Permissions
    - Requires at least operator role

    ## Request Body
    - **employee_id**: ID of the employee to assign
    - **workstation_id**: ID of the workstation to assign to
    - **date**: Date of the assignment
    - **period**: Work period of the day (1-4 typically)
    - **schedule_id**: Optional ID of the schedule this assignment belongs to

    ## Response
    - Returns the created assignment information
    """
    repositories = get_repositories(db)

    # Verify the employee exists
    employee = repositories["employee_repository"].get_by_id(assignment.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee with ID {assignment.employee_id} not found")

    # Verify the workstation exists
    workstation = repositories["workstation_repository"].get_by_id(assignment.workstation_id)
    if not workstation:
        raise HTTPException(status_code=404, detail=f"Workstation with ID {assignment.workstation_id} not found")

    # Verify the schedule exists if provided
    if assignment.schedule_id:
        schedule = repositories["schedule_repository"].get_by_id(assignment.schedule_id)
        if not schedule:
            raise HTTPException(status_code=404, detail=f"Schedule with ID {assignment.schedule_id} not found")

    # Create the manual assignment
    assignment_repo = repositories["assignment_repository"]
    success = assignment_repo.create_temporary_assignment(
        employee_id=assignment.employee_id,
        workstation_id=assignment.workstation_id,
        date=assignment.date,
        period=assignment.period,
        schedule_id=assignment.schedule_id
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to create manual assignment")

    # Return the assignment information
    return AssignmentInfo(
        employee_id=employee.id,
        employee_name=employee.name,
        workstation_id=workstation.id,
        workstation_name=workstation.name,
        period=PeriodInfo(
            date=assignment.date,
            period=assignment.period
        )
    )

@router.get("/", response_model=Page[ScheduleResponse], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
@cache(expire=settings.cache_ttl_seconds)
async def get_schedules(
    team_id: Optional[int] = Query(None, description="Filter schedules by team ID"),
    start_date: Optional[date] = Query(None, description="Filter schedules by start date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Filter schedules by end date (inclusive)"),
    status: Optional[str] = Query(None, description="Filter by schedule status (pending, running, completed, failed)"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_viewer_user)
):
    """
    Get all schedules with filtering, sorting, and pagination.

    This endpoint returns a paginated list of schedules that match the specified filters.
    The results can be sorted by various fields and directions.

    ## Permissions
    - Requires at least viewer role

    ## Filters
    - **team_id**: Filter by team ID
    - **start_date**: Filter by start date (inclusive)
    - **end_date**: Filter by end date (inclusive)
    - **status**: Filter by schedule status (pending, running, completed, failed)

    ## Pagination
    - **page**: Page number (starts at 1)
    - **size**: Items per page (default: 50, max: 100)

    ## Sorting
    - **sort_by**: Sort field(s), format: field:direction (e.g., created_at:desc,team_name:asc)

    ## Response
    - Returns a paginated list of schedules with metadata
    - Each schedule includes its assignments
    """
    repositories = get_repositories(db)
    schedule_repo = repositories["schedule_repository"]

    # Get total count for pagination
    total = schedule_repo.count(
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
        status=status
    )

    # Get schedules with filtering and pagination
    schedules = schedule_repo.get_all(
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        skip=pagination.skip,
        limit=pagination.limit
    )

    # Convert schedules to response format
    items = []
    for schedule in schedules:
        team = repositories["team_repository"].get_by_id(schedule.team_id)

        # Get assignments for this schedule
        assignment_repo = repositories["assignment_repository"]
        assignments_data = assignment_repo.get_by_schedule_id(schedule.id)

        # Convert assignments to response format
        assignments = []
        for assignment in assignments_data:
            employee = repositories["employee_repository"].get_by_id(assignment.employee_id)
            workstation = repositories["workstation_repository"].get_by_id(assignment.workstation_id)

            assignments.append(
                AssignmentInfo(
                    employee_id=employee.id,
                    employee_name=employee.name,
                    workstation_id=workstation.id,
                    workstation_name=workstation.name,
                    period=PeriodInfo(
                        date=assignment.assignment_date,
                        period=assignment.period
                    )
                )
            )

        items.append(
            ScheduleResponse(
                id=schedule.id,
                team_id=schedule.team_id,
                team_name=team.name,
                start_date=schedule.start_date,
                days=schedule.days,
                periods_per_day=schedule.periods_per_day,
                call_ins=schedule.call_ins,
                offline=schedule.offline,
                force_complete=schedule.force_complete,
                assignments=assignments,
                status=schedule.status,
                error_message=schedule.error_message,
                task_id=schedule.task_id,
                created_at=schedule.created_at,
                updated_at=schedule.updated_at
            )
        )

    # Return paginated response
    return Page.create(items=items, total=total, params=pagination)
