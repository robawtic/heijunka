from datetime import date
from dataclasses import dataclass
from typing import Optional

@dataclass
class CreateManualAssignmentCommand:
    employee_id: int
    workstation_id: int
    assignment_date: date
    period: int
    schedule_id: Optional[int] = None