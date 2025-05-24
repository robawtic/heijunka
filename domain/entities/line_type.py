# heijunka/domain/entities/line_type.py
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LineType:
    """
    Represents a type of production line in the manufacturing system.
    
    Line types categorize workstations and help determine which employees
    can work at specific stations based on their qualifications.
    """
    id: int
    name: str
    description: Optional[str] = None
    required_qualifications: List[str] = None
    
    def __post_init__(self):
        if self.required_qualifications is None:
            self.required_qualifications = []
    
    def add_required_qualification(self, qualification: str) -> bool:
        """
        Add a required qualification for this line type.
        
        Args:
            qualification: The qualification to add
            
        Returns:
            True if added, False if already exists
        """
        if qualification in self.required_qualifications:
            return False
        self.required_qualifications.append(qualification)
        return True
    
    def remove_required_qualification(self, qualification: str) -> bool:
        """
        Remove a required qualification for this line type.
        
        Args:
            qualification: The qualification to remove
            
        Returns:
            True if removed, False if not found
        """
        if qualification not in self.required_qualifications:
            return False
        self.required_qualifications.remove(qualification)
        return True
    
    def requires_qualification(self, qualification: str) -> bool:
        """
        Check if this line type requires a specific qualification.
        
        Args:
            qualification: The qualification to check
            
        Returns:
            True if required, False otherwise
        """
        return qualification in self.required_qualifications