from typing import List, Optional, Dict
from domain.entities.team_member import TeamMember
from domain.repositories.interfaces.team_member_repository import TeamMemberRepositoryInterface


class MockTeamMemberRepository(TeamMemberRepositoryInterface):
    """
    Mock implementation of the team member repository for testing.
    """

    def __init__(self):
        self.team_members = {}  # Dictionary of team members by ID
        self.team_members_by_team = {}  # Dictionary of team members by team ID
        self.team_members_by_employee = {}  # Dictionary of team members by employee ID

    def get_by_id(self, entity_id: int) -> Optional[TeamMember]:
        """Retrieve a team member by ID."""
        return self.team_members.get(entity_id)

    def list_all(self) -> List[TeamMember]:
        """Retrieve all team members."""
        return list(self.team_members.values())

    def add(self, entity: TeamMember) -> TeamMember:
        """Add a new team member."""
        self.team_members[entity.team_member_id] = entity
        
        # Update the team index
        if entity.team_id not in self.team_members_by_team:
            self.team_members_by_team[entity.team_id] = []
        self.team_members_by_team[entity.team_id].append(entity)
        
        # Update the employee index
        if entity.employee_id not in self.team_members_by_employee:
            self.team_members_by_employee[entity.employee_id] = []
        self.team_members_by_employee[entity.employee_id].append(entity)
        
        return entity

    def update(self, entity: TeamMember) -> TeamMember:
        """Update an existing team member."""
        old_entity = self.team_members.get(entity.team_member_id)
        if old_entity:
            # Remove from old indexes if team or employee changed
            if old_entity.team_id != entity.team_id:
                self.team_members_by_team[old_entity.team_id].remove(old_entity)
            if old_entity.employee_id != entity.employee_id:
                self.team_members_by_employee[old_entity.employee_id].remove(old_entity)
        
        # Update the main dictionary
        self.team_members[entity.team_member_id] = entity
        
        # Update the team index
        if entity.team_id not in self.team_members_by_team:
            self.team_members_by_team[entity.team_id] = []
        if old_entity and old_entity.team_id == entity.team_id:
            # Replace in the same position
            idx = self.team_members_by_team[entity.team_id].index(old_entity)
            self.team_members_by_team[entity.team_id][idx] = entity
        else:
            # Add to the list
            self.team_members_by_team[entity.team_id].append(entity)
        
        # Update the employee index
        if entity.employee_id not in self.team_members_by_employee:
            self.team_members_by_employee[entity.employee_id] = []
        if old_entity and old_entity.employee_id == entity.employee_id:
            # Replace in the same position
            idx = self.team_members_by_employee[entity.employee_id].index(old_entity)
            self.team_members_by_employee[entity.employee_id][idx] = entity
        else:
            # Add to the list
            self.team_members_by_employee[entity.employee_id].append(entity)
        
        return entity

    def delete(self, entity_id: int) -> bool:
        """Delete a team member by ID."""
        entity = self.team_members.get(entity_id)
        if not entity:
            return False
        
        # Remove from indexes
        if entity.team_id in self.team_members_by_team:
            self.team_members_by_team[entity.team_id].remove(entity)
        if entity.employee_id in self.team_members_by_employee:
            self.team_members_by_employee[entity.employee_id].remove(entity)
        
        # Remove from main dictionary
        del self.team_members[entity_id]
        return True

    def get_by_team_id(self, team_id: int) -> List[TeamMember]:
        """Retrieve all team members for a specific team."""
        return self.team_members_by_team.get(team_id, [])

    def get_by_employee_id(self, employee_id: int) -> List[TeamMember]:
        """Retrieve all team memberships for a specific employee."""
        return self.team_members_by_employee.get(employee_id, [])

    def add_role(self, team_member_id: int, role_name: str) -> bool:
        """Add a role to a team member."""
        team_member = self.team_members.get(team_member_id)
        if not team_member:
            return False
        
        return team_member.add_role(role_name)

    def remove_role(self, team_member_id: int, role_name: str) -> bool:
        """Remove a role from a team member."""
        team_member = self.team_members.get(team_member_id)
        if not team_member:
            return False
        
        return team_member.remove_role(role_name)

    def get_roles(self, team_member_id: int) -> List[str]:
        """Get all roles assigned to a team member."""
        team_member = self.team_members.get(team_member_id)
        if not team_member:
            return []
        
        return team_member.roles.copy()

    def get_by_team_and_employee(self, team_id: int, employee_id: int) -> Optional[TeamMember]:
        """Retrieve a team member by team ID and employee ID."""
        team_members = self.get_by_team_id(team_id)
        for team_member in team_members:
            if team_member.employee_id == employee_id:
                return team_member
        return None