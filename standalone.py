# standalone_script.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import models
from domain.models.DepartmentModel import DepartmentModel
from domain.models.GroupModel import GroupModel
from domain.models.TeamModel import TeamModel
from domain.models.EmployeeModel import EmployeeModel
from domain.models.WorkstationModel import WorkstationModel
from domain.models.EmployeeWorkstationModel import EmployeeWorkstationModel
from domain.models.TeamMemberModel import TeamMemberModel
from domain.models.Base import Base

# Import repositories
from domain.repositories.implementations.sqlalchemy_department_repository import SqlAlchemyDepartmentRepository
from domain.repositories.implementations.sqlalchemy_group_repository import SqlAlchemyGroupRepository
from domain.repositories.implementations.sqlalchemy_team_repository import SqlAlchemyTeamRepository
from domain.repositories.implementations.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository


class HeijunkaDataExplorer:
    def __init__(self, connection_string):
        """Initialize the data explorer with a database connection."""
        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        # Initialize repositories
        self.department_repo = SqlAlchemyDepartmentRepository(self.session)
        self.group_repo = SqlAlchemyGroupRepository(self.session)
        self.team_repo = SqlAlchemyTeamRepository(self.session)
        self.employee_repo = SqlAlchemyEmployeeRepository(self.session)

    def get_department_groups(self, department_name=None):
        """Get all groups in a department or all groups if department_name is None."""
        if department_name:
            department = self.department_repo.get_by_name(department_name)
            if department:
                return department.groups
            return []
        else:
            # Get all departments with their groups
            departments = self.department_repo.get_all_with_groups()
            all_groups = []
            for dept in departments:
                all_groups.extend(dept.groups)
            return all_groups

    def get_group_teams(self, group_name=None):
        """Get all teams in a group or all teams if group_name is None."""
        if group_name:
            group = self.group_repo.get_by_name(group_name)
            if group:
                # Query teams directly from the database where group_id matches
                return self.session.query(TeamModel).filter(TeamModel.group_id == group.id).all()
            return []
        else:
            # Query all teams
            return self.session.query(TeamModel).all()

    def get_team_members(self, team_name=None):
        """Get all members of a team or all team members if team_name is None."""
        if team_name:
            team = self.team_repo.get_by_name(team_name)
            if team:
                return self.team_repo.get_members(team.id)
            return []
        else:
            # Query all team members
            return self.session.query(TeamMemberModel).all()

    def get_team_workstations(self, team_name=None):
        """Get all workstations of a team or all workstations if team_name is None."""
        if team_name:
            team = self.team_repo.get_by_name(team_name)
            if team:
                return self.team_repo.get_workstations(team.id)
            return []
        else:
            # Query all workstations
            return self.session.query(WorkstationModel).all()

    def get_employee(self, employee_name=None):
        """Get an employee by name or all employees if employee_name is None."""
        if employee_name:
            return self.employee_repo.get_by_name(employee_name)
        else:
            # Query all employees
            return self.session.query(EmployeeModel).all()

    def get_employee_metadata(self, employee_name):
        """Get an employee's primary team and workstations they know."""
        employee = self.get_employee(employee_name)
        if not employee:
            return None

        # Get employee's primary team (assuming it's the first team in the list)
        primary_team = None
        if employee.teams and len(employee.teams) > 0:
            team_member = employee.teams[0]
            primary_team = team_member.team

        # Get workstations the employee knows
        known_workstations = []
        for ws in employee.workstations:
            known_workstations.append(ws.workstation)

        return {
            "employee": employee,
            "primary_team": primary_team,
            "known_workstations": known_workstations
        }

    def close(self):
        """Close the database session."""
        self.session.close()


def main():
    # Get database connection string from environment variables
    connection_string = os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres:Brownie12-@localhost/heijunka")
    print(f"Using database connection: {connection_string}")

    explorer = HeijunkaDataExplorer(connection_string)

    try:
        # Example usage
        print("Departments and their groups:")
        departments = explorer.session.query(DepartmentModel).all()
        for dept in departments:
            print(f"Department: {dept.name}")
            groups = explorer.get_department_groups(dept.name)
            for group in groups:
                print(f"  Group: {group.name}")
                teams = explorer.get_group_teams(group.name)
                for team in teams:
                    print(f"    Team: {team.name}")

                    print(f"      Members:")
                    members = explorer.get_team_members(team.name)
                    for member in members:
                        # member is already an Employee object
                        print(f"        {member.name}")

                    print(f"      Workstations:")
                    workstations = explorer.get_team_workstations(team.name)
                    for ws in workstations:
                        print(f"        {ws.name}")

        # Example of getting employee metadata
        employee_name = "Angela Page"  # Replace with an actual employee name
        employee_data = explorer.get_employee_metadata(employee_name)
        if employee_data:
            print(f"\nEmployee: {employee_data['employee'].name}")
            if employee_data['primary_team']:
                print(f"Primary Team: {employee_data['primary_team'].name}")
            print("Known Workstations:")
            for ws in employee_data['known_workstations']:
                print(f"  {ws.name}")

    finally:
        explorer.close()


if __name__ == "__main__":
    main()
