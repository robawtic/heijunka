from pydantic import BaseModel
from datetime import datetime

class GenerateScheduleDto(BaseModel):
    """DTO for schedule generation requests from the presentation layer."""
    start_date: datetime
    team_id: int