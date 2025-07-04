from sqlalchemy import Column, Integer, String, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from domain.models.Base import Base
from domain.models.team_member_roles import team_member_roles
from domain.contexts.user_management.value_objects.role import Role

class RoleModel(Base):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Add a unique constraint on the name column
    __table_args__ = (UniqueConstraint('name', name='_role_name_uc'),)

    # Back-reference to TeamMember
    team_members = relationship('TeamMemberModel', secondary=team_member_roles, back_populates='roles')

    # Helper Methods
    @classmethod
    def role_exists(cls, role_name, session):
        """Checks if a role with the given name exists."""
        return session.query(cls).filter_by(name=role_name).first() is not None

    @classmethod
    def add_role(cls, role_name, session):
        """Adds a new role to the database if it doesn't already exist."""
        if not cls.role_exists(role_name, session):
            new_role = cls(name=role_name)
            session.add(new_role)
            session.commit()
            print(f"RoleModel '{role_name}' has been added.")
        else:
            print(f"RoleModel '{role_name}' already exists.")

    @classmethod
    def edit_role(cls, old_role_name, new_role_name, session):
        """Edits the name of an existing role."""
        role = session.query(cls).filter_by(name=old_role_name).first()
        if role:
            if not cls.role_exists(new_role_name, session):
                role.name = new_role_name
                session.commit()
                print(f"RoleModel '{old_role_name}' has been renamed to '{new_role_name}'.")
            else:
                print(f"RoleModel '{new_role_name}' already exists. Choose a different name.")
        else:
            print(f"RoleModel '{old_role_name}' not found.")

    @classmethod
    def remove_role(cls, role_name, session):
        """Removes a role from the database."""
        role = session.query(cls).filter_by(name=role_name).first()
        if role:
            session.delete(role)
            session.commit()
            print(f"RoleModel '{role_name}' has been removed.")
        else:
            print(f"RoleModel '{role_name}' does not exist.")

    def get_team_members(self):
        """Returns a list of all team members assigned to this role."""
        return self.team_members if self.team_members else None

    def to_domain(self) -> Role:
        """
        Converts the RoleModel instance to a domain Role entity.
        """
        return Role(
            id=self.id,
            name=self.name,
            description=self.description,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    def __repr__(self):
        return f"<RoleModel(name={self.name})>"
