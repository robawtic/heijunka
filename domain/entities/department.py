# heijunka/domain/entities/department.py
from dataclasses import dataclass
from typing import List, Optional
from datetime import date


@dataclass
class Department:
    id: int
    name: str
    description: Optional[str] = None