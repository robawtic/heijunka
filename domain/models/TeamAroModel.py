from enum import Enum
from sqlalchemy import Column, Integer, Enum as SqlEnum, ForeignKey
from sqlalchemy.orm import relationship
from .Base import Base

class AroTeamStatus(Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'

class TeamAroModel(Base):
    __tablename__ = 'team_aros'

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'))
    team_id = Column(Integer, ForeignKey('teams.id'))  # The team an employee can ARO for
    status = Column(SqlEnum(AroTeamStatus), nullable=False)

    # Relationships
    employee = relationship('EmployeeModel', back_populates='team_aros')
    team = relationship('TeamModel', back_populates='team_aros')

    def to_domain(self) -> 'TeamAro':
        return TeamAro(
            id=self.id,
            employee_id=self.employee_id,
            team_id=self.team_id,
            status=self.status.value if isinstance(self.status, AroTeamStatus) else self.status
        )
