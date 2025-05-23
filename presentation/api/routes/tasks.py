from fastapi import APIRouter, Depends, HTTPException, Path
from typing import List, Optional

from infrastructure.api.auth import get_admin_user, get_scheduler_user, get_viewer_user
from infrastructure.tasks.task_manager import task_manager, TaskInfo, TaskStatus
from presentation.api.models import ErrorResponse

router = APIRouter()

@router.get("/", response_model=List[TaskInfo], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def get_tasks(
    status: Optional[TaskStatus] = None,
    current_user: dict = Depends(get_viewer_user)
):
    """
    Get all background tasks, optionally filtered by status.
    
    - **status**: Filter by task status (pending, running, completed, failed)
    """
    return task_manager.get_tasks(status)

@router.get("/{task_id}", response_model=TaskInfo, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def get_task(
    task_id: str = Path(..., description="Task ID"),
    current_user: dict = Depends(get_viewer_user)
):
    """
    Get information about a specific background task.
    
    - **task_id**: Task ID
    """
    task = task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    return task

@router.delete("/completed", responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def clear_completed_tasks(
    current_user: dict = Depends(get_admin_user)
):
    """
    Clear completed and failed tasks. Requires admin role.
    """
    count = task_manager.clear_completed_tasks()
    return {"message": f"Cleared {count} completed tasks"}