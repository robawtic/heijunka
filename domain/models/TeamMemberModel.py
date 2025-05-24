from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .Base import Base
from .team_member_roles import team_member_roles


class TeamMemberModel(Base):
    __tablename__ = 'team_members'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)

    # Relationships
    team = relationship('TeamModel', back_populates='members')
    employee = relationship('EmployeeModel', back_populates='teams')
    roles = relationship('RoleModel', secondary=team_member_roles, back_populates='team_members')

    # Unique constraint to prevent duplicate team member entries
    __table_args__ = (
        UniqueConstraint('team_id', 'employee_id', name='_team_member_uc'),
    )