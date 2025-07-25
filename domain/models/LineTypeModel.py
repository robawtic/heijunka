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
    # Note: workstations relationship removed as WorkstationModel no longer has line_type_id

    def __repr__(self):
        return f"<LineType(id={self.id}, name='{self.name}')>"

    @classmethod
    def from_value_object(cls, value_object, id=None):
        """
        Create a LineTypeModel from a LineType value object.

        Args:
            value_object: The LineType value object
            id: Optional ID for the model (used when creating a new record)

        Returns:
            A new LineTypeModel instance
        """
        return cls(
            id=id,
            name=value_object.name,
            description=value_object.description
        )

    def to_value_object(self):
        """
        Convert this model to a LineType value object.

        Returns:
            A LineType value object
        """
        from domain.contexts.workstation_management.value_objects.line_type import LineType
        return LineType(
            name=self.name,
            description=self.description
        )
