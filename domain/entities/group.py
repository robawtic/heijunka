# heijunka/domain/entities/group.py
from dataclasses import dataclass
from typing import List, Optional
from datetime import date


@dataclass
class Group:
    id: int
    name: str
    department_id: Optional[int] = None
