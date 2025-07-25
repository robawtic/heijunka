from typing import List

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .Base import Base
from .RoleModel import RoleModel
from .TeamMemberModel import TeamMemberModel
from domain.contexts.employee_management.entities.group import Group

class GroupModel(Base):
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)

    # Relationships
    department = relationship('DepartmentModel', back_populates='groups')
    teams = relationship('TeamModel', back_populates='group')

    def to_domain(self) -> 'Group':
        return Group(
            id=self.id,
            name=self.name,
            department_id=self.department_id
        )
