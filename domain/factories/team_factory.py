# domain/factories/team_factory.py
from typing import List, Optional
from domain.entities.team import Team
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.entities.team_member import TeamMember

class TeamFactory:
    @staticmethod
    def create_team(
        id: Optional[int] = None,
        name: str = "",
        description: str = "",
        members: List[Employee] = None,
        workstations: List[Workstation] = None,
        team_members: List[TeamMember] = None
    ) -> Team:
        """Create a new Team entity with basic properties."""
        team = Team(
            id=id or 0,
            name=name,
            description=description,
            _members=members or [],
            _workstations=workstations or [],
            _team_members=team_members or []
        )
        
        # Validate the team
        team.validate()
        
        return team
    
    @staticmethod
    def create_team_with_members(
        id: Optional[int] = None,
        name: str = "",
        description: str = "",
        members: List[Employee] = None
    ) -> Team:
        """Create a Team with members."""
        team = TeamFactory.create_team(
            id=id,
            name=name,
            description=description
        )
        
        if members:
            for member in members:
                team.add_member(member)
                
        return team
    
    @staticmethod
    def create_team_with_workstations(
        id: Optional[int] = None,
        name: str = "",
        description: str = "",
        workstations: List[Workstation] = None
    ) -> Team:
        """Create a Team with workstations."""
        team = TeamFactory.create_team(
            id=id,
            name=name,
            description=description
        )
        
        if workstations:
            for workstation in workstations:
                team.add_workstation(workstation)
                
        return team
    
    @staticmethod
    def create_from_model(model) -> Team:
        """Create a Team entity from a database model."""
        # Extract members and workstations from the model
        members = []
        if hasattr(model, 'members') and model.members:
            for member in model.members:
                if hasattr(member, 'employee') and member.employee:
                    # Convert employee model to domain entity
                    from domain.factories.employee_factory import EmployeeFactory
                    employee = EmployeeFactory.create_from_model(member.employee)
                    members.append(employee)
        
        workstations = []
        if hasattr(model, 'workstations') and model.workstations:
            for ws in model.workstations:
                # Convert workstation model to domain entity
                from domain.factories.workstation_factory import WorkstationFactory
                workstation = WorkstationFactory.create_from_model(ws)
                workstations.append(workstation)
        
        # Create team members
        team_members = []
        if hasattr(model, 'members') and model.members:
            for member_model in model.members:
                team_member = TeamMember(
                    team_member_id=member_model.id,
                    team_id=model.id,
                    employee_id=member_model.employee_id,
                    _roles=[role.name for role in member_model.roles] if hasattr(member_model, 'roles') else []
                )
                team_members.append(team_member)
        
        # Create the team
        team = TeamFactory.create_team(
            id=model.id,
            name=model.name,
            description=model.description if hasattr(model, 'description') else "",
            members=members,
            workstations=workstations,
            team_members=team_members
        )
        
        return team