from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List

from domain.events.aro import (
    AROAssignmentCreated, AROAssignmentRemoved, AROAssignmentUpdated
)
from domain.events.base import DomainEvent

@dataclass
class AROAssignment:
    """
    Aggregate root representing an employee's ARO assignment to another team.
    """
    id: int
    employee_id: int
    from_team_id: int
    to_team_id: int
    assignment_date: date
    period: Optional[int] = None  # Can be None for full-day assignments
    _domain_events: List[DomainEvent] = field(default_factory=list, repr=False)
    
    def __post_init__(self):
        """Initialize collections if they are None."""
        if self._domain_events is None:
            self._domain_events = []
        
        # Validate the ARO assignment
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.from_team_id, int) or self.from_team_id <= 0:
            raise ValueError("from_team_id must be a positive integer")
        if not isinstance(self.to_team_id, int) or self.to_team_id <= 0:
            raise ValueError("to_team_id must be a positive integer")
        if not isinstance(self.assignment_date, date):
            raise ValueError("assignment_date must be a date object")
        if self.period is not None and (not isinstance(self.period, int) or not 1 <= self.period <= 5):
            raise ValueError("period must be None or an integer between 1 and 5")
    
    @property
    def domain_events(self) -> List[DomainEvent]:
        """Get a copy of the domain events list."""
        return self._domain_events.copy()
    
    def clear_domain_events(self) -> None:
        """Clear all domain events after they've been processed."""
        self._domain_events.clear()
    
    def register_domain_event(self, event: DomainEvent) -> None:
        """Register a domain event."""
        self._domain_events.append(event)
    
    @classmethod
    def create(cls, employee_id: int, from_team_id: int, to_team_id: int, 
               assignment_date: date, period: Optional[int] = None) -> 'AROAssignment':
        """
        Create a new ARO assignment and raise the appropriate domain event.
        
        Args:
            employee_id: The ID of the employee being assigned
            from_team_id: The ID of the team the employee is coming from
            to_team_id: The ID of the team the employee is going to
            assignment_date: The date of the assignment
            period: Optional period of the day
            
        Returns:
            A new AROAssignment instance
        """
        assignment = cls(
            id=0,  # This will be set by the repository
            employee_id=employee_id,
            from_team_id=from_team_id,
            to_team_id=to_team_id,
            assignment_date=assignment_date,
            period=period
        )
        
        # Register the domain event
        assignment.register_domain_event(AROAssignmentCreated(
            employee_id=employee_id,
            from_team_id=from_team_id,
            to_team_id=to_team_id,
            assignment_date=assignment_date,
            period=period
        ))
        
        return assignment
    
    def update(self, to_team_id: Optional[int] = None, 
               assignment_date: Optional[date] = None, 
               period: Optional[int] = None) -> None:
        """
        Update the ARO assignment and raise the appropriate domain event.
        
        Args:
            to_team_id: Optional new destination team ID
            assignment_date: Optional new assignment date
            period: Optional new period
        """
        updated = False
        
        if to_team_id is not None and to_team_id != self.to_team_id:
            self.to_team_id = to_team_id
            updated = True
            
        if assignment_date is not None and assignment_date != self.assignment_date:
            self.assignment_date = assignment_date
            updated = True
            
        if period != self.period:  # Allow setting period to None
            self.period = period
            updated = True
            
        if updated:
            # Register the domain event
            self.register_domain_event(AROAssignmentUpdated(
                employee_id=self.employee_id,
                from_team_id=self.from_team_id,
                to_team_id=self.to_team_id,
                assignment_date=self.assignment_date,
                period=self.period
            ))
    
    def remove(self) -> None:
        """
        Mark the ARO assignment for removal and raise the appropriate domain event.
        """
        # Register the domain event
        self.register_domain_event(AROAssignmentRemoved(
            employee_id=self.employee_id,
            from_team_id=self.from_team_id,
            to_team_id=self.to_team_id,
            assignment_date=self.assignment_date,
            period=self.period
        ))