from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .Base import Base
from domain.entities.team import Team


class TeamModel(Base):
    __tablename__ = 'teams'
    __table_args__ = {'extend_existing': True}  # Add this to prevent table redefinition errors

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    group = relationship('GroupModel', back_populates='teams', lazy='joined')
    members = relationship('TeamMemberModel', back_populates='team', lazy='joined')
    workstations = relationship('WorkstationModel', back_populates='team', lazy='joined')

    def to_domain(self) -> Team:
        """Convert TeamModel to Team domain entity"""
        from domain.entities.employee import Employee
        from domain.entities.workstation import Workstation
        from domain.entities.team_member import TeamMember

        # Create team members
        team_members = []
        for member_model in self.members:
            employee = member_model.employee.to_domain() if member_model.employee else None
            team_member = TeamMember(
                team_member_id=member_model.id,
                team_id=self.id,
                employee_id=member_model.employee_id,
                employee=employee,
                roles=[role.name for role in member_model.roles] if hasattr(member_model, 'roles') else []
            )
            team_members.append(team_member)

        # Create workstations
        workstations = [
            Workstation(
                id=ws.id,
                name=ws.name,
                line_type=str(ws.line_type),
                is_loading_job=ws.is_loading_job,
                is_heavy_job=ws.is_heavy_job,
                is_key_skill_job=ws.is_key_skill_job,
                team_id=ws.team_id
            ) for ws in self.workstations
        ]

        return Team(
            id=self.id,
            name=self.name,
            description=self.description,
            _team_members=team_members,
            _workstations=workstations
        )

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}')>"
