# domain/models/WorkstationAttributeDefinition.py
from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.orm  import relationship
from .Base                       import Base

class WorkstationAttributeDefinition(Base):
    __tablename__  = 'workstation_attribute_definitions'
    __table_args__ = ( UniqueConstraint('name',name='uq_ws_attr_name'), )

    id          = Column(Integer, primary_key=True)
    name        = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)


    workstation_links = relationship(
        'WorkstationAttributeModel',
        back_populates='attribute',
        cascade='all, delete-orphan',
    )

    workstations = relationship(
        'WorkstationModel',
        secondary='workstation_attributes',
        back_populates='attributes',
        viewonly=True,
    )

    def __repr__(self):
        return f"<WorkstationAttributeDefinition(name='{self.name}')>"