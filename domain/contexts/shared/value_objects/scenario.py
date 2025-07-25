# domain/value_objects/scenario.py
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Dict, Any

@dataclass
class Scenario:
    """Represents a scheduling scenario with specific parameters."""
    name: str
    team_id: int
    start_date: date
    periods_per_day: int = 4
    call_ins: Optional[List[str]] = None
    offline: Optional[List[str]] = None
    force_complete: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.call_ins is None:
            self.call_ins = []
        if self.offline is None:
            self.offline = []
    
    def __str__(self):
        return f"Scenario '{self.name}' for team {self.team_id} starting {self.start_date}"