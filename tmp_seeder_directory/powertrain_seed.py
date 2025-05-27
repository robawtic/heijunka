# powertrain_seed.py
# This script seeds the database with Powertrain department data
# It uses the Faker package to generate realistic employee names
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from domain.models import EmployeeModel, TeamModel, RoleModel, TeamMemberModel, WorkstationModel, \
    EmployeeWorkstationModel, GroupModel, LineTypeModel
from domain.models.DepartmentModel import DepartmentModel
from datetime import date, timedelta
from itertools import cycle
from domain.models.WatcherHeartbeat import WatcherHeartbeatModel
from domain.models.Base import Base
from domain.models.db import engine, Session
import random
from faker import Faker
import json
import os
from datetime import datetime
from utilities.secure_logging import redact_log_message


def get_test_date():
    return date(2024, 1, 1)


def load_json_data(file_path):
    """
    Load data from a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        The loaded JSON data as a Python object
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(redact_log_message(f"Warning: File not found: {file_path}", file_paths=[file_path]))
        return None
    except json.JSONDecodeError:
        print(redact_log_message(f"Warning: Invalid JSON in file: {file_path}", file_paths=[file_path]))
        return None


def load_team_data(team_name):
    """
    Load all data for a specific team.

    Args:
        team_name: Name of the team

    Returns:
        Dictionary containing the team's workstations and employees data
    """
    base_path = os.path.join("tmp_seeder_directory", "groups", "shortblock", "teams", team_name)

    workstations_path = os.path.join(base_path, "workstations.json")
    employees_path = os.path.join(base_path, "employees.json")

    workstations_data = load_json_data(workstations_path)
    employees_data = load_json_data(employees_path)

    return {
        "workstations": workstations_data["workstations"] if workstations_data else [],
        "employees": employees_data["employees"] if employees_data else []
    }


def seed_powertrain_data(session):
    # Create a Faker instance for generating realistic names
    fake = Faker()

    # Check if roles exist, if not create them
    roles = ['Group Leader', 'Team Leader', 'Backup', 'Associate', 'Temp']
    role_objects = {}
    for role_name in roles:
        role = session.query(RoleModel).filter_by(name=role_name).first()
        if not role:
            role = RoleModel(name=role_name)
            session.add(role)
        role_objects[role_name] = role
    session.commit()

    # Check if Powertrain department exists, if not create it
    powertrain_dept = session.query(DepartmentModel).filter_by(name='Powertrain').first()
    if not powertrain_dept:
        powertrain_dept = DepartmentModel(name='Powertrain')
        session.add(powertrain_dept)
        session.commit()

    # Check if line types exist, if not create them
    line_types = {
        "Mainline": "Main assembly line",
        "Sub-Assembly": "Sub-assembly line",
        "Test": "Testing station"
    }
    line_type_objects = {}
    for name, description in line_types.items():
        line_type = session.query(LineTypeModel).filter_by(name=name).first()
        if not line_type:
            line_type = LineTypeModel(name=name, description=description)
            session.add(line_type)
        line_type_objects[name] = line_type
    session.commit()

    # Define Powertrain groups
    powertrain_groups = [
        'Shortblock',
        'Internal',
        'Final',
        'Docking'
    ]

    # Create groups if they don't exist
    group_objects = {}
    for group_name in powertrain_groups:
        group = session.query(GroupModel).filter_by(name=group_name).first()
        if not group:
            group = GroupModel(
                name=group_name,
                department_id=powertrain_dept.id
            )
            session.add(group)
            session.commit()
        group_objects[group_name] = group

    # Define teams for each group
    teams_by_group = {
        'Shortblock': ['shortblock', 'headsub', 'camsub'],
        'Internal': ['valve-adjus', 'oil-pan-upper', 'chain-guard'],
        'Final': ['final-1', 'final-2', 'test-bench'],
        'Docking': ['docking-1', 'docking-2', 'docking-3']
    }

    # Create teams if they don't exist
    team_objects = {}
    for group_name, team_names in teams_by_group.items():
        group = group_objects[group_name]
        for team_name in team_names:
            team = session.query(TeamModel).filter_by(name=team_name).first()
            if not team:
                team = TeamModel(name=team_name, group_id=group.id)
                session.add(team)
                session.commit()
            team_objects[team_name] = team

    # Define workstations for each team using the JSON data files
    workstation_objects = {}

    # Load workstation data for Shortblock group teams
    shortblock_teams = ['shortblock', 'headsub', 'camsub']

    for team_name in shortblock_teams:
        print(f"Loading workstation data for {team_name} team...")
        team_data = load_team_data(team_name)
        team = team_objects[team_name]

        # Create workstations from the JSON data
        for ws_data in team_data["workstations"]:
            workstation = session.query(WorkstationModel).filter_by(name=ws_data["name"], team_id=team.id).first()
            if not workstation:
                line_type = line_type_objects[ws_data["line_type"]]
                workstation = WorkstationModel(
                    name=ws_data["name"],
                    line_type_id=line_type.id,
                    is_loading_job=ws_data["is_loading_job"],
                    is_heavy_job=ws_data["is_heavy_job"],
                    is_key_skill_job=ws_data["is_key_skill_job"],
                    team_id=team.id
                )
                session.add(workstation)
                session.commit()
                print(redact_log_message(f"  Created workstation: {ws_data['name']}", workstation_names=[ws_data['name']]))
            workstation_objects[(team_name, ws_data["name"])] = workstation

    # Create generic workstations for other teams
    for group_name, team_names in teams_by_group.items():
        if group_name == 'Shortblock':
            continue  # Already handled above

        for team_name in team_names:
            team = team_objects[team_name]
            # Create 3-5 workstations per team
            num_stations = random.randint(3, 5)
            for i in range(1, num_stations + 1):
                station_name = f"{team_name.upper()[:2]}{i:03d}"
                workstation = session.query(WorkstationModel).filter_by(name=station_name, team_id=team.id).first()
                if not workstation:
                    # Randomly assign properties
                    is_loading = random.choice([True, False])
                    is_heavy = is_loading and random.choice([True, False])
                    is_key_skill = random.choice([True, False])
                    line_type_name = random.choice(list(line_types.keys()))

                    workstation = WorkstationModel(
                        name=station_name,
                        line_type_id=line_type_objects[line_type_name].id,
                        is_loading_job=is_loading,
                        is_heavy_job=is_heavy,
                        is_key_skill_job=is_key_skill,
                        team_id=team.id
                    )
                    session.add(workstation)
                    session.commit()
                workstation_objects[(team_name, station_name)] = workstation

    # Create employees for each team using the JSON data files
    employee_objects = {}

    # For Shortblock group teams, use the JSON data
    for team_name in shortblock_teams:
        print(f"Loading employee data for {team_name} team...")
        team_data = load_team_data(team_name)
        team = team_objects[team_name]

        # Create employees from the JSON data
        for i, emp_data in enumerate(team_data["employees"], 1):
            employee_name = emp_data["name"]
            employee = session.query(EmployeeModel).filter_by(name=employee_name).first()
            if not employee:
                employee = EmployeeModel(
                    name=employee_name,
                    team_id=team.id,
                    is_active=emp_data.get("is_active", True)
                )
                session.add(employee)
                session.commit()
                print(redact_log_message(f"  Created employee: {employee_name}", employee_names=[employee_name]))
            employee_objects[(team_name, i)] = employee

            # Create TeamMember entry
            team_member = session.query(TeamMemberModel).filter_by(team_id=team.id, employee_id=employee.id).first()
            if not team_member:
                team_member = TeamMemberModel(team_id=team.id, employee_id=employee.id)

                # Assign roles based on the JSON data
                role = emp_data.get("role", "Associate")
                if role == "Team Leader":
                    team_member.roles.append(role_objects['Team Leader'])
                elif role == "Backup":
                    team_member.roles.append(role_objects['Backup'])

                # All employees are associates
                team_member.roles.append(role_objects['Associate'])

                session.add(team_member)
                session.commit()

    # For other teams, generate random employees
    for group_name, team_names in teams_by_group.items():
        if group_name == 'Shortblock':
            continue  # Already handled above

        for team_name in team_names:
            team = team_objects[team_name]
            # Number of employees for this team
            num_employees = random.randint(3, 6)

            # Create employees
            for i in range(1, num_employees + 1):
                # Generate a unique name
                employee_name = fake.name()  # Generate a realistic full name
                employee = session.query(EmployeeModel).filter_by(name=employee_name).first()
                if not employee:
                    employee = EmployeeModel(
                        name=employee_name,
                        team_id=team.id,
                        is_active=True
                    )
                    session.add(employee)
                    session.commit()
                employee_objects[(team_name, i)] = employee

                # Create TeamMember entry
                team_member = session.query(TeamMemberModel).filter_by(team_id=team.id, employee_id=employee.id).first()
                if not team_member:
                    team_member = TeamMemberModel(team_id=team.id, employee_id=employee.id)

                    # Assign roles
                    if i == 1:
                        # First employee is team leader
                        team_member.roles.append(role_objects['Team Leader'])
                    elif i == 2:
                        # Second employee is backup
                        team_member.roles.append(role_objects['Backup'])

                    # All employees are associates
                    team_member.roles.append(role_objects['Associate'])

                    session.add(team_member)
                    session.commit()

    # Assign workstations to employees
    fake_dates = cycle([get_test_date() + timedelta(days=i) for i in range(5)])

    # For Shortblock group teams, use the JSON data for workstation assignments
    for team_name in shortblock_teams:
        print(f"Assigning workstations for {team_name} team...")
        team_data = load_team_data(team_name)
        team = team_objects[team_name]

        # Get all workstations for this team
        team_workstations = {ws.name: ws for (t, _), ws in workstation_objects.items() if t == team_name}

        # For each employee, assign them to the workstations they know
        for i, emp_data in enumerate(team_data["employees"], 1):
            employee = employee_objects.get((team_name, i))
            if not employee:
                continue

            # Get the known stations from the JSON data
            known_station_names = emp_data.get("known_stations", [])

            # Create EmployeeWorkstation entries
            for station_name in known_station_names:
                workstation = team_workstations.get(station_name)
                if not workstation:
                    print(f"  Warning: Workstation {station_name} not found for {team_name} team")
                    continue

                employee_workstation = session.query(EmployeeWorkstationModel).filter_by(
                    employee_id=employee.id,
                    station_id=workstation.id
                ).first()

                if not employee_workstation:
                    last_worked_date = next(fake_dates)
                    employee_workstation = EmployeeWorkstationModel(
                        employee_id=employee.id,
                        station_id=workstation.id,
                        last_worked_date=last_worked_date
                    )
                    session.add(employee_workstation)
                    print(f"  Assigned {emp_data['name']} to {station_name}")

    # For other teams, randomly assign workstations
    for group_name, team_names in teams_by_group.items():
        if group_name == 'Shortblock':
            continue  # Already handled above

        for team_name in team_names:
            team = team_objects[team_name]

            # Get all workstations for this team
            team_workstations = [ws for (t, _), ws in workstation_objects.items() if t == team_name]

            # Get all employees for this team
            team_employees = [emp for (t, _), emp in employee_objects.items() if t == team_name]

            # For each employee, assign them to know 70-100% of the workstations
            for employee in team_employees:
                # Determine how many workstations this employee knows
                num_known = random.randint(max(1, int(len(team_workstations) * 0.7)), len(team_workstations))

                # Randomly select workstations
                known_workstations = random.sample(team_workstations, num_known)

                # Create EmployeeWorkstation entries
                for workstation in known_workstations:
                    employee_workstation = session.query(EmployeeWorkstationModel).filter_by(
                        employee_id=employee.id,
                        station_id=workstation.id
                    ).first()

                    if not employee_workstation:
                        last_worked_date = next(fake_dates)
                        employee_workstation = EmployeeWorkstationModel(
                            employee_id=employee.id,
                            station_id=workstation.id,
                            last_worked_date=last_worked_date
                        )
                        session.add(employee_workstation)

    session.commit()
    print("Powertrain department data seeded successfully.")


if __name__ == "__main__":
    # Create a session
    session = Session()
    # Seed the Powertrain department data
    seed_powertrain_data(session)
    print("Database seeding complete.")
