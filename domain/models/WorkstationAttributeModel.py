# domain/models/WorkstationAttributeModel.py
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .Base import Base

class WorkstationAttributeModel(Base):
    __tablename__  = 'workstation_attributes'
    __table_args__ = (
        UniqueConstraint('workstation_id', 'attribute_id', name='uq_workstation_attribute'),
    )

    workstation_id = Column(Integer, ForeignKey('workstations.id'), primary_key=True)
    attribute_id   = Column(Integer, ForeignKey('workstation_attribute_definitions.id'), primary_key=True)


    workstation = relationship(
        'WorkstationModel',
        back_populates='attribute_links',
    )
    attribute = relationship(
        'WorkstationAttributeDefinition',
        back_populates='workstation_links',
    )

    def __repr__(self):
        return (
            f"<WorkstationAttributeModel("
            f"workstation_id={self.workstation_id}, "
            f"attribute_id={self.attribute_id})>"
        )
