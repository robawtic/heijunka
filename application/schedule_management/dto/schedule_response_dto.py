from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any

class ScheduleResponseDto(BaseModel):
    """DTO for schedule responses to presentation layer."""
    schedule_id: int
    start_date: datetime
    end_date: datetime
    status: str
    created_at: datetime
    assignments_count: int
    workstations_count: int
    employees_count: int
    optimization_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }