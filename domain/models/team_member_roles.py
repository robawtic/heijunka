# models/team_member_roles.py

from sqlalchemy import Table, Column, Integer, ForeignKey
from .Base import Base

# Simple association table for many-to-many relationship between TeamMember and RoleModel
team_member_roles = Table(
    'team_member_roles', Base.metadata,
    Column('team_member_id', Integer, ForeignKey('team_members.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)


