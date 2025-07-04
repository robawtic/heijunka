# domain/contexts/workstation_management/value_objects/workstation_capacity.py
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass(frozen=True)
class WorkstationCapacity:
    """
    Value object representing the capacity and utilization of a workstation.
    
    This encapsulates information about how many employees a workstation can
    accommodate, current utilization, and capacity constraints.
    """
    
    # Basic capacity information
    max_employees: int
    min_employees: int = 1
    optimal_employees: int = 1
    
    # Current utilization
    current_employees: int = 0
    
    # Capacity constraints
    requires_team_lead: bool = False
    requires_certified_operator: bool = False
    max_trainees: int = 0
    
    # Shift and time-based capacity
    shift_capacity_multiplier: float = 1.0
    peak_hours_capacity: Optional[int] = None
    
    # Additional metadata
    capacity_notes: Optional[str] = None
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate workstation capacity constraints."""
        if self.max_employees < 1:
            raise ValueError("max_employees must be at least 1")
        
        if self.min_employees < 1:
            raise ValueError("min_employees must be at least 1")
        
        if self.min_employees > self.max_employees:
            raise ValueError("min_employees cannot be greater than max_employees")
        
        if self.optimal_employees < self.min_employees or self.optimal_employees > self.max_employees:
            raise ValueError("optimal_employees must be between min_employees and max_employees")
        
        if self.current_employees < 0:
            raise ValueError("current_employees cannot be negative")
        
        if self.max_trainees < 0:
            raise ValueError("max_trainees cannot be negative")
        
        if not (0.1 <= self.shift_capacity_multiplier <= 3.0):
            raise ValueError("shift_capacity_multiplier must be between 0.1 and 3.0")
        
        if self.peak_hours_capacity is not None and self.peak_hours_capacity < self.min_employees:
            raise ValueError("peak_hours_capacity cannot be less than min_employees")
    
    def is_at_capacity(self) -> bool:
        """Check if the workstation is at maximum capacity."""
        return self.current_employees >= self.max_employees
    
    def is_understaffed(self) -> bool:
        """Check if the workstation is below minimum staffing."""
        return self.current_employees < self.min_employees
    
    def is_optimally_staffed(self) -> bool:
        """Check if the workstation is at optimal staffing level."""
        return self.current_employees == self.optimal_employees
    
    def can_accommodate_additional(self, additional_employees: int = 1) -> bool:
        """
        Check if the workstation can accommodate additional employees.
        
        Args:
            additional_employees: Number of additional employees to check
            
        Returns:
            True if can accommodate, False otherwise
        """
        return (self.current_employees + additional_employees) <= self.max_employees
    
    def get_available_capacity(self) -> int:
        """Get the number of additional employees that can be accommodated."""
        return max(0, self.max_employees - self.current_employees)
    
    def get_capacity_utilization(self) -> float:
        """
        Get the current capacity utilization as a percentage.
        
        Returns:
            Utilization percentage (0.0 to 1.0)
        """
        if self.max_employees == 0:
            return 0.0
        return min(1.0, self.current_employees / self.max_employees)
    
    def get_optimal_utilization(self) -> float:
        """
        Get the optimal capacity utilization as a percentage.
        
        Returns:
            Optimal utilization percentage (0.0 to 1.0)
        """
        if self.max_employees == 0:
            return 0.0
        return self.optimal_employees / self.max_employees
    
    def needs_additional_staff(self) -> int:
        """
        Calculate how many additional staff are needed to reach optimal capacity.
        
        Returns:
            Number of additional staff needed (0 if already optimal or overstaffed)
        """
        return max(0, self.optimal_employees - self.current_employees)
    
    def with_updated_current_employees(self, new_count: int) -> 'WorkstationCapacity':
        """
        Create a new WorkstationCapacity with updated current employee count.
        
        Args:
            new_count: New current employee count
            
        Returns:
            New WorkstationCapacity instance
        """
        return WorkstationCapacity(
            max_employees=self.max_employees,
            min_employees=self.min_employees,
            optimal_employees=self.optimal_employees,
            current_employees=new_count,
            requires_team_lead=self.requires_team_lead,
            requires_certified_operator=self.requires_certified_operator,
            max_trainees=self.max_trainees,
            shift_capacity_multiplier=self.shift_capacity_multiplier,
            peak_hours_capacity=self.peak_hours_capacity,
            capacity_notes=self.capacity_notes,
            last_updated=datetime.now()
        )
    
    def with_updated_capacity(self, max_employees: Optional[int] = None,
                            min_employees: Optional[int] = None,
                            optimal_employees: Optional[int] = None) -> 'WorkstationCapacity':
        """
        Create a new WorkstationCapacity with updated capacity limits.
        
        Args:
            max_employees: New maximum employees (optional)
            min_employees: New minimum employees (optional)
            optimal_employees: New optimal employees (optional)
            
        Returns:
            New WorkstationCapacity instance
        """
        return WorkstationCapacity(
            max_employees=max_employees if max_employees is not None else self.max_employees,
            min_employees=min_employees if min_employees is not None else self.min_employees,
            optimal_employees=optimal_employees if optimal_employees is not None else self.optimal_employees,
            current_employees=self.current_employees,
            requires_team_lead=self.requires_team_lead,
            requires_certified_operator=self.requires_certified_operator,
            max_trainees=self.max_trainees,
            shift_capacity_multiplier=self.shift_capacity_multiplier,
            peak_hours_capacity=self.peak_hours_capacity,
            capacity_notes=self.capacity_notes,
            last_updated=datetime.now()
        )
    
    def get_capacity_status(self) -> Dict[str, Any]:
        """
        Get a comprehensive status report of the workstation capacity.
        
        Returns:
            Dictionary containing capacity status information
        """
        return {
            "is_at_capacity": self.is_at_capacity(),
            "is_understaffed": self.is_understaffed(),
            "is_optimally_staffed": self.is_optimally_staffed(),
            "available_capacity": self.get_available_capacity(),
            "utilization_percentage": round(self.get_capacity_utilization() * 100, 1),
            "optimal_utilization_percentage": round(self.get_optimal_utilization() * 100, 1),
            "additional_staff_needed": self.needs_additional_staff(),
            "current_vs_optimal": self.current_employees - self.optimal_employees,
            "capacity_range": f"{self.min_employees}-{self.max_employees}",
            "status": self._get_status_description()
        }
    
    def _get_status_description(self) -> str:
        """Get a human-readable status description."""
        if self.is_understaffed():
            return "Understaffed"
        elif self.is_at_capacity():
            return "At Capacity"
        elif self.is_optimally_staffed():
            return "Optimally Staffed"
        elif self.current_employees > self.optimal_employees:
            return "Overstaffed"
        else:
            return "Below Optimal"