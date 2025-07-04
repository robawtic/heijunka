# domain/contexts/assignment/value_objects/assignment_criteria.py
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import date

@dataclass(frozen=True)
class AssignmentCriteria:
    """
    Value object representing criteria and constraints for assignment optimization.
    
    This encapsulates the business rules and preferences that guide how
    employees are assigned to workstations during schedule generation.
    """
    
    # Basic assignment constraints
    max_consecutive_days: Optional[int] = None
    min_rest_days: Optional[int] = None
    preferred_workstations: Optional[List[int]] = None
    excluded_workstations: Optional[List[int]] = None
    
    # Skill and experience requirements
    required_skill_level: Optional[int] = None
    min_experience_days: Optional[int] = None
    certification_required: bool = False
    
    # Workload balancing
    max_assignments_per_period: Optional[int] = None
    prefer_balanced_workload: bool = True
    avoid_heavy_consecutive_assignments: bool = True
    
    # Team and collaboration preferences
    preferred_team_members: Optional[List[int]] = None
    avoid_team_members: Optional[List[int]] = None
    maintain_team_continuity: bool = False
    
    # Time-based constraints
    assignment_date: Optional[date] = None
    preferred_periods: Optional[List[int]] = None
    excluded_periods: Optional[List[int]] = None
    
    # Priority and optimization weights
    priority_weight: float = 1.0
    efficiency_weight: float = 1.0
    fairness_weight: float = 1.0
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate assignment criteria constraints."""
        if self.max_consecutive_days is not None and self.max_consecutive_days < 1:
            raise ValueError("max_consecutive_days must be at least 1")
        
        if self.min_rest_days is not None and self.min_rest_days < 0:
            raise ValueError("min_rest_days cannot be negative")
        
        if self.required_skill_level is not None and not (1 <= self.required_skill_level <= 5):
            raise ValueError("required_skill_level must be between 1 and 5")
        
        if self.min_experience_days is not None and self.min_experience_days < 0:
            raise ValueError("min_experience_days cannot be negative")
        
        if self.max_assignments_per_period is not None and self.max_assignments_per_period < 1:
            raise ValueError("max_assignments_per_period must be at least 1")
        
        if self.preferred_periods:
            for period in self.preferred_periods:
                if not (1 <= period <= 5):
                    raise ValueError("preferred_periods must contain values between 1 and 5")
        
        if self.excluded_periods:
            for period in self.excluded_periods:
                if not (1 <= period <= 5):
                    raise ValueError("excluded_periods must contain values between 1 and 5")
        
        if not (0.0 <= self.priority_weight <= 10.0):
            raise ValueError("priority_weight must be between 0.0 and 10.0")
        
        if not (0.0 <= self.efficiency_weight <= 10.0):
            raise ValueError("efficiency_weight must be between 0.0 and 10.0")
        
        if not (0.0 <= self.fairness_weight <= 10.0):
            raise ValueError("fairness_weight must be between 0.0 and 10.0")
    
    def is_workstation_allowed(self, workstation_id: int) -> bool:
        """Check if a workstation is allowed based on criteria."""
        if self.excluded_workstations and workstation_id in self.excluded_workstations:
            return False
        
        if self.preferred_workstations and workstation_id not in self.preferred_workstations:
            return False
        
        return True
    
    def is_period_allowed(self, period: int) -> bool:
        """Check if a period is allowed based on criteria."""
        if self.excluded_periods and period in self.excluded_periods:
            return False
        
        if self.preferred_periods and period not in self.preferred_periods:
            return False
        
        return True
    
    def get_optimization_score(self) -> float:
        """Calculate a combined optimization score based on weights."""
        return (self.priority_weight + self.efficiency_weight + self.fairness_weight) / 3.0