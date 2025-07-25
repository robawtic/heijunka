from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from .Base import Base


class WorkstationModel(Base):
    __tablename__ = 'workstations'
    __table_args__ = (
        UniqueConstraint('name', 'team_id', name='uq_workstations_name_team_id'),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)

    # Relationships
    employees = relationship('EmployeeWorkstationModel', back_populates='workstation')
    work_history = relationship('EmployeeWorkHistoryModel', back_populates='station')
    team = relationship('TeamModel', back_populates='workstations')
    employee_skills = relationship('EmployeeStationSkillModel', back_populates='station')

    attribute_links = relationship(
        'WorkstationAttributeModel',
        back_populates='workstation',
        cascade='all, delete-orphan',
    )
    attributes = relationship(
        'WorkstationAttributeDefinition',
        secondary='workstation_attributes',
        back_populates='workstations',
        viewonly=True,
    )

    @hybrid_property
    def is_loading(self) -> bool:
        """Check if this workstation is a loading job based on its attributes."""
        return any(attr.name == 'loading' for attr in self.attributes)

    @hybrid_property
    def is_heavy(self) -> bool:
        """Check if this workstation is a heavy job based on its attributes."""
        return any(attr.name == 'heavy' for attr in self.attributes)
