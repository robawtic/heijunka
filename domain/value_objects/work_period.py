# domain/value_objects/work_period.py
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class WorkPeriod:
    date: date
    period: int

    def __post_init__(self):
        if not 1 <= self.period <= 5:
            raise ValueError("period must be between 1 and 5")

    def __str__(self):
        return f"Date {self.date}, Period {self.period}"