# heijunka/domain/value_objects/schedule_constraint.py
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict


class ConstraintType(Enum):
    HARD = "hard"
    SOFT = "soft"


@dataclass(frozen=True)
class ScheduleConstraint:
    name: str
    type: ConstraintType
    rule_function: Callable
    weight: int = 1  # For soft constraints
    parameters: Dict[str, Any] = None

    def __post_init__(self):
        if self.parameters is None:
            object.__setattr__(self, 'parameters', {})