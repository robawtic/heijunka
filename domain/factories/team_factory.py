# domain/factories/team_factory.py
from typing import List, Optional, Any
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
        members: Optional[List[Employee]] = None,
        workstations: Optional[List[Workstation]] = None,
        team_members: Optional[List[TeamMember]] = None
    ) -> Team:
        """
        Create a new Team entity with basic properties.

        Args:
            id: Optional team ID (None for new teams)
            name: Team name
            description: Team description
            members: Optional list of Employee entities
            workstations: Optional list of Workstation entities
            team_members: Optional list of TeamMember entities

        Returns:
            A new Team entity

        Raises:
            ValueError: If validation fails (e.g., empty name)
        """
        # Validate inputs before creating the team
        if name and not isinstance(name, str):
            raise ValueError("Name must be a string")

        if description and not isinstance(description, str):
            raise ValueError("Description must be a string")

        # Create a basic team without members or workstations
        team = Team(
            id=id or 0,
            name=name,
            description=description,
            _members=[],
            _workstations=[],
            _team_members=[]
        )

        # Add members if provided
        if members:
            for member in members:
                team.add_member(member)

        # Add workstations if provided
        if workstations:
            for workstation in workstations:
                team.add_workstation(workstation)

        # Add team members if provided
        if team_members:
            for team_member in team_members:
                # We need to create a new TeamMember and add it to the team
                # Since there's no direct method to add a TeamMember, we'll need to
                # find or create the corresponding Employee and add it to the team
                employee = team.get_member_by_id(team_member.employee_id)
                if not employee:
                    # If the employee isn't already a member, we can't add the TeamMember
                    # This is a limitation of the current design
                    continue

                # Add roles from the TeamMember to the employee in this team
                for role in team_member.roles:
                    team.assign_role_to_member(team_member.employee_id, role)

        # Validate the team
        team.validate()

        return team

    @staticmethod
    def create_team_with_members(
        id: Optional[int] = None,
        name: str = "",
        description: str = "",
        members: Optional[List[Employee]] = None
    ) -> Team:
        """
        Create a Team with members.

        Args:
            id: Optional team ID
            name: Team name
            description: Team description
            members: Optional list of Employee entities to add to the team

        Returns:
            A new Team entity with the specified members

        Raises:
            ValueError: If validation fails
        """
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
        workstations: Optional[List[Workstation]] = None
    ) -> Team:
        """
        Create a Team with workstations.

        Args:
            id: Optional team ID
            name: Team name
            description: Team description
            workstations: Optional list of Workstation entities to add to the team

        Returns:
            A new Team entity with the specified workstations

        Raises:
            ValueError: If validation fails
        """
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
    def create_from_model(model: Any) -> Team:
        """
        Create a Team entity from a database model.

        Args:
            model: The database model to convert

        Returns:
            A new Team entity populated with data from the model

        Raises:
            ValueError: If validation fails
        """
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

        # Create the team first
        team = TeamFactory.create_team(
            id=model.id,
            name=model.name,
            description=model.description if hasattr(model, 'description') else "",
            members=members,
            workstations=workstations
        )

        # Add roles to team members
        if hasattr(model, 'members') and model.members:
            for member_model in model.members:
                if hasattr(member_model, 'roles') and member_model.roles:
                    for role in member_model.roles:
                        team.assign_role_to_member(member_model.employee_id, role.name)

        return team
