import asyncio
import logging
import uuid
from typing import Dict, Any, Callable, Awaitable, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel

logger = logging.getLogger("heijunka_api.tasks")

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskInfo(BaseModel):
    id: str
    status: TaskStatus
    name: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    
    class Config:
        json_schema_extra= {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "completed",
                "name": "generate_schedule",
                "created_at": "2023-06-01T08:30:00",
                "started_at": "2023-06-01T08:30:01",
                "completed_at": "2023-06-01T08:30:10",
                "result": {"schedule_id": 1},
                "error": None
            }
        }

class TaskManager:
    """
    Manager for background tasks with status tracking.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            cls._instance._tasks: Dict[str, TaskInfo] = {}
        return cls._instance
    
    async def create_task(self, name: str, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> str:
        """
        Create and run a new background task.
        
        Args:
            name: Name of the task
            func: Async function to run
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        # Create task info
        task_info = TaskInfo(
            id=task_id,
            status=TaskStatus.PENDING,
            name=name,
            created_at=datetime.now()
        )
        
        self._tasks[task_id] = task_info
        
        # Create and run the task
        asyncio.create_task(self._run_task(task_id, func, *args, **kwargs))
        
        return task_id
    
    async def _run_task(self, task_id: str, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> None:
        """
        Run a task and update its status.
        """
        task_info = self._tasks[task_id]
        task_info.status = TaskStatus.RUNNING
        task_info.started_at = datetime.now()
        
        try:
            logger.info(f"Starting task {task_id} ({task_info.name})")
            result = await func(*args, **kwargs)
            
            task_info.status = TaskStatus.COMPLETED
            task_info.completed_at = datetime.now()
            task_info.result = result
            
            logger.info(f"Task {task_id} ({task_info.name}) completed successfully")
        except Exception as e:
            logger.exception(f"Task {task_id} ({task_info.name}) failed with error: {str(e)}")
            
            task_info.status = TaskStatus.FAILED
            task_info.completed_at = datetime.now()
            task_info.error = str(e)
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """
        Get information about a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task information or None if not found
        """
        return self._tasks.get(task_id)
    
    def get_tasks(self, status: Optional[TaskStatus] = None) -> List[TaskInfo]:
        """
        Get all tasks, optionally filtered by status.
        
        Args:
            status: Filter by task status
            
        Returns:
            List of task information
        """
        if status is None:
            return list(self._tasks.values())
        
        return [task for task in self._tasks.values() if task.status == status]
    
    def clear_completed_tasks(self) -> int:
        """
        Clear completed and failed tasks.
        
        Returns:
            Number of tasks cleared
        """
        completed_task_ids = [
            task_id for task_id, task in self._tasks.items()
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
        ]
        
        for task_id in completed_task_ids:
            del self._tasks[task_id]
        
        return len(completed_task_ids)

# Singleton instance
task_manager = TaskManager()