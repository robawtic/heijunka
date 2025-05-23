# heijunka/domain/models/LineTypeModel.py
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from domain.models.Base import Base


class LineTypeModel(Base):
    """
    SQLAlchemy model for the line_types table.
    
    This model represents different types of production lines in the manufacturing system.
    Line types categorize workstations and help determine which employees
    can work at specific stations based on their qualifications.
    """
    __tablename__ = 'line_types'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Relationships
    workstations = relationship("WorkstationModel", back_populates="line_type")
    
    def __repr__(self):
        return f"<LineType(id={self.id}, name='{self.name}')>"
    
    @classmethod
    def from_entity(cls, entity):
        """
        Create a LineTypeModel from a LineType entity.
        
        Args:
            entity: The LineType entity
            
        Returns:
            A new LineTypeModel instance
        """
        return cls(
            id=entity.id if entity.id != 0 else None,
            name=entity.name,
            description=entity.description
        )
    
    def to_entity(self):
        """
        Convert this model to a LineType entity.
        
        Returns:
            A LineType entity
        """
        from domain.entities.line_type import LineType
        return LineType(
            id=self.id,
            name=self.name,
            description=self.description
        )