# domain/contexts/workstation_management/value_objects/line_type.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass(frozen=True)
class LineType:
    """
    Value object representing a type of production line in the manufacturing system.
    
    Line types categorize workstations and help determine which employees
    can work at specific stations based on their qualifications.
    """
    name: str
    description: Optional[str] = None
    required_qualifications: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate the line type."""
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")
        if self.description is not None and not isinstance(self.description, str):
            raise ValueError("description must be a string or None")
        if not isinstance(self.required_qualifications, list):
            raise ValueError("required_qualifications must be a list")
        for qual in self.required_qualifications:
            if not isinstance(qual, str) or not qual:
                raise ValueError("each qualification must be a non-empty string")
    
    def requires_qualification(self, qualification: str) -> bool:
        """
        Check if this line type requires a specific qualification.
        
        Args:
            qualification: The qualification to check
            
        Returns:
            True if required, False otherwise
        """
        return qualification in self.required_qualifications
    
    def with_added_qualification(self, qualification: str) -> 'LineType':
        """
        Create a new LineType with an additional required qualification.
        
        Args:
            qualification: The qualification to add
            
        Returns:
            A new LineType instance with the added qualification
        """
        if qualification in self.required_qualifications:
            return self
        
        new_qualifications = self.required_qualifications.copy()
        new_qualifications.append(qualification)
        
        return LineType(
            name=self.name,
            description=self.description,
            required_qualifications=new_qualifications
        )
    
    def with_removed_qualification(self, qualification: str) -> 'LineType':
        """
        Create a new LineType with a required qualification removed.
        
        Args:
            qualification: The qualification to remove
            
        Returns:
            A new LineType instance with the qualification removed
        """
        if qualification not in self.required_qualifications:
            return self
        
        new_qualifications = self.required_qualifications.copy()
        new_qualifications.remove(qualification)
        
        return LineType(
            name=self.name,
            description=self.description,
            required_qualifications=new_qualifications
        )