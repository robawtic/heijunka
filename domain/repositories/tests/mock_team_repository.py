from typing import Optional, List

from domain.entities.team import Team
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.repositories.interfaces.team_repository import TeamRepositoryInterface


class MockTeamRepository(TeamRepositoryInterface):
    """
    Mock implementation of the team repository for testing.
    """
    
    def __init__(self):
        self.teams = {}  # Dictionary of teams by ID
        
    def get_by_id(self, entity_id: int) -> Optional[Team]:
        """Retrieve a team by ID."""
        return self.teams.get(entity_id)
    
    def list_all(self) -> List[Team]:
        """Retrieve all teams."""
        return list(self.teams.values())
    
    def add(self, entity: Team) -> Team:
        """Add a new team."""
        self.teams[entity.id] = entity
        return entity
    
    def update(self, entity: Team) -> Team:
        """Update an existing team."""
        self.teams[entity.id] = entity
        return entity
    
    def delete(self, entity_id: int) -> bool:
        """Delete a team by ID."""
        if entity_id in self.teams:
            del self.teams[entity_id]
            return True
        return False
    
    def get_by_name(self, team_name: str) -> Optional[Team]:
        """Retrieve a team by its name."""
        for team in self.teams.values():
            if team.name == team_name:
                return team
        return None
    
    def add_member(self, team_id: int, employee: Employee) -> bool:
        """Add an employee to a team."""
        team = self.teams.get(team_id)
        if not team:
            return False
            
        # Check if the employee is already a member of the team
        for member in team.members:
            if member.id == employee.id:
                return True  # Already a member
                
        # Add the employee to the team
        team.members.append(employee)
        return True
    
    def remove_member(self, team_id: int, employee_id: int) -> bool:
        """Remove an employee from a team."""
        team = self.teams.get(team_id)
        if not team:
            return False
            
        # Find the employee in the team
        for i, member in enumerate(team.members):
            if member.id == employee_id:
                # Remove the employee from the team
                team.members.pop(i)
                return True
                
        return False  # Employee not found in team
    
    def add_workstation(self, team_id: int, workstation: Workstation) -> bool:
        """Add a workstation to a team."""
        team = self.teams.get(team_id)
        if not team:
            return False
            
        # Check if the workstation is already assigned to the team
        for ws in team.workstations:
            if ws.id == workstation.id:
                return True  # Already assigned
                
        # Add the workstation to the team
        team.workstations.append(workstation)
        # Update the workstation's id
        workstation.team_id = team_id
        return True
    
    def remove_workstation(self, team_id: int, workstation_id: int) -> bool:
        """Remove a workstation from a team."""
        team = self.teams.get(team_id)
        if not team:
            return False
            
        # Find the workstation in the team
        for i, ws in enumerate(team.workstations):
            if ws.id == workstation_id:
                # Remove the workstation from the team
                workstation = team.workstations.pop(i)
                # Update the workstation's id
                workstation.id = None
                return True
                
        return False  # Workstation not found in team
    
    def get_members(self, team_id: int) -> List[Employee]:
        """Get all members of a team."""
        team = self.teams.get(team_id)
        if not team:
            return []
            
        return team.members
    
    def get_workstations(self, team_id: int) -> List[Workstation]:
        """Get all workstations of a team."""
        team = self.teams.get(team_id)
        if not team:
            return []
            
        return team.workstations