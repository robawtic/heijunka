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


def check_team_staffing_and_assign_if_needed(explorer, team_name, date_obj=None):
    """
    Check if a team has enough employees to cover all workstations.
    If not, find employees from other teams to add to the short-staffed team.

    Args:
        explorer: HeijunkaDataExplorer instance
        team_name: Name of the team to check
        date_obj: Date to check (defaults to today)

    Returns:
        Tuple of (is_adequately_staffed, assignments_made)
        where assignments_made is a list of tuples (employee_name, workstation_name)
    """
    from datetime import date
    if date_obj is None:
        date_obj = date.today()

    # Find the team
    team = explorer.team_repo.get_by_name(team_name)
    if not team:
        print(f"Team '{team_name}' not found")
        return False, []

    # Get team workstations
    workstations = explorer.get_team_workstations(team_name)
    if not workstations:
        print(f"No workstations found for team '{team_name}'")
        return True, []  # No workstations means no staffing needed

    # Get team members
    team_members = explorer.get_team_members(team_name)
    if not team_members:
        print(f"No members found for team '{team_name}'")
        return False, []

    # Filter out AROs (this would need to be implemented based on your ARO tracking)
    # For now, assume all team members are available
    available_members = team_members

    print(f"Team '{team_name}' has {len(available_members)} available employees and {len(workstations)} workstations")

    # Check if we have enough employees
    if len(available_members) >= len(workstations):
        print(f"Team '{team_name}' has enough employees to cover all workstations")
        return True, []

    # Not enough employees, find employees from other teams
    print(f"Team '{team_name}' needs {len(workstations) - len(available_members)} more employees")

    # Get employees from other teams in the same department
    department = explorer.department_repo.get_by_team_id(team.id)
    if not department:
        print(f"Could not find department for team '{team_name}'")
        return False, []

    # Get all teams in the department
    department_teams = explorer.team_repo.get_by_department_id(department.id)

    # Exclude the current team
    other_teams = [t for t in department_teams if t.id != team.id]

    # Find employees from other teams who can work on this team's workstations
    additional_employees = []
    needed_count = len(workstations) - len(available_members)
    assignments = []

    for other_team in other_teams:
        # Skip if we already have enough employees
        if len(additional_employees) >= needed_count:
            break

        # Get employees from this team
        other_team_members = explorer.get_team_members(other_team.name)

        for employee in other_team_members:
            # Skip if we already have enough employees
            if len(additional_employees) >= needed_count:
                break

            # Check if this employee knows any of our workstations
            for workstation in workstations:
                # Check if employee already knows this workstation
                existing_assignment = explorer.session.query(EmployeeWorkstationModel).filter(
                    EmployeeWorkstationModel.employee_id == employee.id,
                    EmployeeWorkstationModel.station_id == workstation.id
                ).first()

                if existing_assignment:
                    # Employee already knows this workstation
                    additional_employees.append(employee)
                    assignments.append((employee.name, workstation.name))
                    print(f"Found {employee.name} from team {other_team.name} who already knows {workstation.name}")
                    break

    # If we still need more employees, assign them to workstations
    if len(additional_employees) < needed_count:
        print(f"Still need {needed_count - len(additional_employees)} more employees, assigning new workstations")

        for other_team in other_teams:
            # Skip if we already have enough employees
            if len(additional_employees) >= needed_count:
                break

            # Get employees from this team
            other_team_members = explorer.get_team_members(other_team.name)

            for employee in other_team_members:
                # Skip if we already have enough employees
                if len(additional_employees) >= needed_count:
                    break

                # Skip if employee is already in our list
                if employee in additional_employees:
                    continue

                # Assign a workstation to this employee
                for workstation in workstations:
                    # Check if employee already knows this workstation
                    existing_assignment = explorer.session.query(EmployeeWorkstationModel).filter(
                        EmployeeWorkstationModel.employee_id == employee.id,
                        EmployeeWorkstationModel.station_id == workstation.id
                    ).first()

                    if not existing_assignment:
                        # Create new assignment
                        try:
                            new_assignment = EmployeeWorkstationModel(
                                employee_id=employee.id,
                                station_id=workstation.id
                            )
                            explorer.session.add(new_assignment)
                            explorer.session.commit()

                            additional_employees.append(employee)
                            assignments.append((employee.name, workstation.name))
                            print(f"Assigned {workstation.name} to {employee.name} from team {other_team.name}")
                            break
                        except Exception as e:
                            print(f"Error assigning {workstation.name} to {employee.name}: {e}")
                            explorer.session.rollback()

    return len(additional_employees) >= needed_count, assignments

def assign_opu_workstations_to_other_employees(explorer, num_employees=5):
    """
    Assign opu workstations to employees from other teams.

    Args:
        explorer: HeijunkaDataExplorer instance
        num_employees: Number of employees to assign opu workstations to

    Returns:
        List of tuples (employee_name, workstation_name) of assignments made
    """
    # Find the opu team
    opu_team = None
    internal_group = explorer.get_group_teams("internal")
    for team in internal_group:
        if team.name.lower() == "opu":
            opu_team = team
            break

    if not opu_team:
        print("Camsub team not found")
        return []

    # Get opu workstations
    opu_workstations = explorer.get_team_workstations(opu_team.name)
    if not opu_workstations:
        print("No workstations found for opu team")
        return []

    print(f"Found {len(opu_workstations)} workstations for opu team")

    # Get employees from other teams in the powertrain department
    other_employees = []
    powertrain_groups = explorer.get_department_groups("powertrain")

    for group in powertrain_groups:
        teams = explorer.get_group_teams(group.name)
        for team in teams:
            if team.id != opu_team.id:  # Skip opu team
                team_members = explorer.get_team_members(team.name)
                other_employees.extend(team_members)

    if not other_employees:
        print("No employees found in other teams")
        return []

    print(f"Found {len(other_employees)} employees in other teams")

    # Randomly select employees to assign opu workstations to
    import random
    selected_employees = random.sample(other_employees, min(num_employees, len(other_employees)))

    # Assign opu workstations to selected employees
    assignments = []
    session = explorer.session

    for employee in selected_employees:
        # Randomly select a workstation to assign
        workstation = random.choice(opu_workstations)

        # Create the assignment in the database
        try:
            # Check if employee already knows this workstation
            existing_assignment = session.query(EmployeeWorkstationModel).filter(
                EmployeeWorkstationModel.employee_id == employee.id,
                EmployeeWorkstationModel.station_id == workstation.id
            ).first()

            if not existing_assignment:
                # Create new assignment
                new_assignment = EmployeeWorkstationModel(
                    employee_id=employee.id,
                    station_id=workstation.id
                )
                session.add(new_assignment)
                session.commit()

                assignments.append((employee.name, workstation.name))
                print(f"Assigned {workstation.name} to {employee.name}")
            else:
                print(f"{employee.name} already knows {workstation.name}")
        except Exception as e:
            print(f"Error assigning {workstation.name} to {employee.name}: {e}")
            session.rollback()

    return assignments

def main():
    import argparse
    from datetime import datetime

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Heijunka Data Explorer')
    parser.add_argument('--assign-opu', action='store_true', help='Assign opu workstations to employees from other teams')
    parser.add_argument('--check-staffing', type=str, help='Check if a team has enough employees to cover all workstations')
    parser.add_argument('--date', type=str, help='Date to check staffing for (YYYY-MM-DD)')
    parser.add_argument('--num-employees', type=int, default=5, help='Number of employees to assign workstations to')

    args = parser.parse_args()

    connection_string = os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres:Brownie12-@localhost/heijunka")
    explorer = HeijunkaDataExplorer(connection_string)

    try:
        if args.assign_opu:
            print(f"Assigning opu workstations to {args.num_employees} employees from other teams...")
            assignments = assign_opu_workstations_to_other_employees(explorer, num_employees=args.num_employees)
            print(f"Made {len(assignments)} assignments")

            # Print summary of assignments
            if assignments:
                print("\nAssignments made:")
                for employee_name, workstation_name in assignments:
                    print(f"  {employee_name} -> {workstation_name}")
        elif args.check_staffing:
            date_obj = None
            if args.date:
                try:
                    date_obj = datetime.strptime(args.date, "%Y-%m-%d").date()
                except ValueError:
                    print("Invalid date format. Use YYYY-MM-DD")
                    return

            is_staffed, assignments = check_team_staffing_and_assign_if_needed(explorer, args.check_staffing, date_obj)

            if is_staffed:
                print(f"Team '{args.check_staffing}' is adequately staffed")
            else:
                print(f"Team '{args.check_staffing}' is not adequately staffed")

            if assignments:
                print("\nAssignments made:")
                for employee_name, workstation_name in assignments:
                    print(f"  {employee_name} -> {workstation_name}")
        else:
            print("No action specified. Use --assign-opu to assign opu workstations to employees from other teams.")
            print("Or use --check-staffing to check if a team has enough employees to cover all workstations.")
            print("Example: python standalone.py --assign-opu --num-employees 4")
            print("Example: python standalone.py --check-staffing OPU --date 2023-05-01")

    finally:
        explorer.close()


if __name__ == "__main__":
    main()
