# heijunka/domain/entities/workstation.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class Workstation:
    id: int
    name: str
    line_type: str
    is_loading_job: bool = False
    is_heavy_job: bool = False
    is_key_skill_job: bool = False
    team_id: Optional[int] = None

    def is_heavy(self) -> bool:
        """Returns True if this workstation is a heavy job."""
        return self.is_heavy_job

    def is_loading(self) -> bool:
        """Returns True if this workstation is a loading job."""
        return self.is_loading_job

    def requires_key_skill(self) -> bool:
        """Returns True if this workstation requires key skill."""
        return self.is_key_skill_job