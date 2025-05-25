from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class DomainEvent:
    """Base class for all domain events"""
    occurred_on: datetime = field(default_factory=datetime.utcnow, init=False)

    def __post_init__(self):
        if self.occurred_on is None:
            self.occurred_on = datetime.utcnow()