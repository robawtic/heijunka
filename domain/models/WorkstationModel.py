from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey
from sqlalchemy.orm import relationship

from domain.models.EmployeeWorkstationModel import EmployeeWorkstationModel
from .Base import Base
from .LineType import LineType  # Import the LineType enum
from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel  # Import the EmployeeWorkHistory model

class WorkstationModel(Base):
    __tablename__ = 'workstations'
    __table_args__ = {'extend_existing': True}


    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    line_type_id = Column(Integer, ForeignKey('line_types.id'), nullable=False)
    is_loading_job = Column(Boolean, nullable=False, default=False)
    is_heavy_job = Column(Boolean, nullable=False, default=False)
    is_key_skill_job = Column(Boolean, nullable=False, default=False)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)

    # Relationships
    line_type = relationship('LineTypeModel', back_populates='workstations')
    employees = relationship('EmployeeWorkstationModel', back_populates='workstation')
    work_history = relationship('EmployeeWorkHistoryModel', back_populates='station')
    team = relationship('TeamModel', back_populates='workstations')
    employee_skills = relationship('EmployeeStationSkillModel', back_populates='station')
