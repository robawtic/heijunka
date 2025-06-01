# domain/models/EmployeeModel.py
from typing import List, TYPE_CHECKING

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship

from domain.models.Base import Base

if TYPE_CHECKING:
    from domain.entities.employee import Employee

class EmployeeModel(Base):
    __tablename__ = 'employees'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    team_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)

    workstations = relationship('EmployeeWorkstationModel', back_populates='employee')
    work_history = relationship('EmployeeWorkHistoryModel', back_populates='employee')
    availability = relationship('EmployeeAvailabilityModel', back_populates='employee')
    teams = relationship('TeamMemberModel', back_populates='employee')
    station_skills = relationship('EmployeeStationSkillModel', back_populates='employee')

    def to_domain(self) -> 'Employee':
        """Convert this model to a domain entity using the factory."""
        from domain.factories.employee_factory import EmployeeFactory
        return EmployeeFactory.create_from_model(self)

    def _get_roles(self) -> List[str]:
        """Get a list of role names for this employee across all teams."""
        return [role.name
                for team_member in self.teams
                for role in team_member.roles]

    def _get_qualifications(self) -> List[str]:
        return [ws.workstation.name
                for ws in self.workstations]
