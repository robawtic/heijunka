from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .Base import Base

class DepartmentModel(Base):
    __tablename__ = 'departments'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    
    # Relationships
    groups = relationship('GroupModel', back_populates='department')
    
    def __repr__(self):
        return f"<Department(id={self.id}, name='{self.name}')>"