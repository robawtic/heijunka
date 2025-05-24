# heijunka/application/commands/generate_schedule_command.py
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

@dataclass
class GenerateScheduleCommand:
    team_id: int
    start_date: date
    periods_per_day: int
    call_ins: List[str] = None
    offline: List[str] = None
    force_complete: bool = False
