from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .Base import Base
from domain.contexts.employee_management.entities.team import Team


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
    team_aros = relationship('TeamAroModel', back_populates='team', lazy='select', viewonly=True)

    def to_domain(self) -> Team:
        """Convert TeamModel to Team domain entity"""
        from domain.contexts.employee_management.entities.employee import Employee
        from domain.contexts.workstation_management.entities.workstation import Workstation
        from domain.contexts.employee_management.entities.team_member import TeamMember

        # Create team members
        team_members = []
        for member_model in self.members:
            employee = member_model.employee.to_domain() if member_model.employee else None
            team_member = TeamMember(
                team_member_id=member_model.id,
                team_id=self.id,
                employee_id=member_model.employee_id,
                employee=employee,
                roles=[role.to_domain() for role in member_model.roles] if hasattr(member_model, 'roles') else []
            )
            team_members.append(team_member)

        # Create workstations
        workstations = []
        for ws in self.workstations:
            # Extract attributes from the new attribute system
            attribute_names = [attr.name for attr in ws.attributes] if ws.attributes else []

            # Map attributes back to the expected format
            line_type = "Mainline"  # default
            if "mainline" in attribute_names:
                line_type = "Mainline"
            elif "subline" in attribute_names:
                line_type = "Sub-Assembly"

            is_loading_job = "loading" in attribute_names
            is_heavy_job = "heavy" in attribute_names
            is_key_skill_job = "skill_level_3" in attribute_names  # Assuming skill_level_3 = key skill

            # Create workstation with the new attribute system
            attributes = []
            if is_loading_job:
                attributes.append("loading")
            if is_heavy_job:
                attributes.append("heavy")
            if is_key_skill_job:
                attributes.append("skill_level_3")  # Assuming key skill = advanced skill

            workstation = Workstation(
                id=ws.id,
                name=ws.name,
                line_type=line_type,
                team_id=ws.team_id,
                _attributes=attributes
            )
            workstations.append(workstation)

        return Team(
            id=self.id,
            name=self.name,
            description=self.description,
            _team_members=team_members,
            _workstations=workstations
        )

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}')>"
