from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from domain.models import EmployeeModel, TeamModel, RoleModel, TeamMemberModel, WorkstationModel, EmployeeWorkstationModel, GroupModel, LineTypeModel
from domain.models.DepartmentModel import DepartmentModel
from datetime import date, timedelta
from itertools import cycle
from domain.models.WatcherHeartbeat import WatcherHeartbeatModel
from domain.models.Base import Base
from domain.models.db import engine, Session


def get_test_date():
    return date(2024, 1, 1)


def reset_database():
    # Drop all tables
    print("Dropping all tables...")
    Base.metadata.drop_all(engine)

    # Recreate all tables
    print("Recreating all tables...")
    Base.metadata.create_all(engine)
    print("Database reset complete.")


# Function to seed initial data
def seed_data(session):
    # Add initial roles
    roles = ['Group Leader', 'Team Leader', 'Backup', 'Associate', 'Temp']  # Add other roles as needed
    for role_name in roles:
        role = session.query(RoleModel).filter_by(name=role_name).first()
        if not role:
            role = RoleModel(name=role_name)
            session.add(role)
    session.commit()

    # Add initial departments
    departments_data = ['Powertrain', 'Trim', 'Paint', 'Body', 'Materials', 'IPC']
    departments = {}
    for dept_name in departments_data:
        department = session.query(DepartmentModel).filter_by(name=dept_name).first()
        if not department:
            department = DepartmentModel(name=dept_name)
            session.add(department)
            session.flush()  # Flush to get the department id
            departments[dept_name] = department
    session.commit()

    # Add initial groups and assign them to departments
    groups_data = [
        {'name': 'Short Block', 'department': 'Powertrain'},
        {'name': 'Internal', 'department': 'Powertrain'},
        {'name': 'Test Bench', 'department': 'Powertrain'}
    ]
    for group_data in groups_data:
        group = session.query(GroupModel).filter_by(name=group_data['name']).first()
        if not group:
            department = departments.get(group_data['department'])
            group = GroupModel(
                name=group_data['name'],
                department_id=department.id if department else None
            )
            session.add(group)
    session.commit()

    # Add employees and assign them to the headsub team
    employees_data = [
        {"name": "Taylor", "known_stations": ""},
        {"name": "Ray", "known_stations": "H010,H080/H090,H100,H110/H120,BW070,H170,M050"},
        {"name": "Antonio", "known_stations": "Parts Wash,H010,H080/H090,H100,H110/H120,H170,BW010,BW070,M050,M090",
         "is_trainer": True},
        {"name": "Brian", "known_stations": "H010,H080/H090,H100,H110/H120,H170,BW010,BW070,M050,M090", "is_trainer": True},
        {"name": "Rachael", "known_stations": "H010,H080/H090,H100,H110/H120,H170,BW010,BW070,M050"},
        {"name": "Matt", "known_stations": "Parts Wash,H010,H080/H090,H100,H110/H120,H170,BW010,BW070,M050,M090",
         "is_trainer": True},
        {"name": "Kaden", "known_stations": "H010,H080/H090,H100,H110/H120,H170,BW010,BW070,M050,M090"},
        {"name": "Aaron", "known_stations": "Parts Wash,H010,H080/H090,H100,H110/H120,H170,BW010,BW070,M050,M090",
         "is_trainer": True},
        {"name": "Fab", "known_stations": "H010,H080/H090,H100,H110/H120,H170,BW010,BW070,M050,M090",
         "is_trainer": True},
        {"name": "Luke", "known_stations": "H010,H080/H090,H100,H110/H120,H170,BW010,BW070,M050,M090"},
        {"name": "Taje", "known_stations": "H010,H080/H090,H100,H110/H120,H170,BW010,BW070,M050,M090"},
        {"name": "Chyla", "known_stations": "H010,H080/H090,H100,H110/H120,H170,BW010,M050,M090"},
    ]

    # Add line types if they don't exist
    mainline = session.query(LineTypeModel).filter_by(name="Mainline").first()
    if not mainline:
        mainline = LineTypeModel(name="Mainline", description="Main assembly line")
        session.add(mainline)

    sub_assembly = session.query(LineTypeModel).filter_by(name="Sub-Assembly").first()
    if not sub_assembly:
        sub_assembly = LineTypeModel(name="Sub-Assembly", description="Sub-assembly line")
        session.add(sub_assembly)

    session.commit()

    # Add Workstations
    workstations_data = [
        {"name": "Parts Wash", "line_type": "Sub-Assembly", "is_loading_job": False,
         "is_heavy_job": False, "is_key_skill_job": False},
        {"name": "H010", "line_type": "Sub-Assembly", "is_loading_job": True,
         "is_heavy_job": False, "is_key_skill_job": False},
        {"name": "H080/H090", "line_type": "Sub-Assembly", "is_loading_job": False,
         "is_heavy_job": False, "is_key_skill_job": False},
        {"name": "H100", "line_type": "Sub-Assembly", "is_loading_job": False,
         "is_heavy_job": False, "is_key_skill_job": False},
        {"name": "H110/H120", "line_type": "Sub-Assembly", "is_loading_job": False,
         "is_heavy_job": False, "is_key_skill_job": False},
        {"name": "H170", "line_type": "Sub-Assembly", "is_loading_job": True,
         "is_heavy_job": True, "is_key_skill_job": False},
        {"name": "BW010", "line_type": "Mainline", "is_loading_job": True,
         "is_heavy_job": True, "is_key_skill_job": False},
        {"name": "BW070", "line_type": "Mainline", "is_loading_job": False,
         "is_heavy_job": False, "is_key_skill_job": False},
        {"name": "M050", "line_type": "Mainline", "is_loading_job": True,
         "is_heavy_job": True, "is_key_skill_job": False},
        {"name": "M090", "line_type": "Mainline", "is_loading_job": True,
         "is_heavy_job": True, "is_key_skill_job": False}
    ]

    # Create Employee entries
    employees = {}
    for employee_data in employees_data:
        employee = EmployeeModel(
            name=employee_data["name"],
            team_id=1,  # Default team ID, will be updated later
            is_active=True
        )
        session.add(employee)
        session.commit()  # Commit to get the employee id
        employees[employee.name] = employee

    # Fetch the desired group for headsub team (for example, Short Block)
    group = session.query(GroupModel).filter_by(name="Short Block").first()

    # Ensure group exists
    if group:
        # Create the headsub team with group_id
        headsub_team = TeamModel(name="headsub", group_id=group.id)  # Assign the group_id
        session.add(headsub_team)
        session.commit()  # Commit to get the team_id
        print(f"Added 'headsub' team to group '{group.name}' with group_id {group.id}.")
    else:
        print("Group 'Short Block' not found. Unable to create headsub team.")
        return

    # Fetch all relevant roles at once
    leader_role = session.query(RoleModel).filter_by(name="Team Leader").first()
    backup_role = session.query(RoleModel).filter_by(name="Backup").first()
    associate_role = session.query(RoleModel).filter_by(name="Associate").first()

    # Assign all employees to the headsub team, including Taylor and Matt with their specific roles
    for employee_name, employee in employees.items():
        # Update employee's team_id
        employee.team_id = headsub_team.id

        # Create the TeamMember entry
        team_member = TeamMemberModel(team_id=headsub_team.id, employee_id=employee.id)

        # Assign roles based on the employee's status
        if employee_name == "Taylor":
            team_member.roles.append(leader_role)
        elif employee_name == "Luke":
            team_member.roles.append(backup_role)

        # Assign the Associate role to all employees, including Taylor and Matt
        team_member.roles.append(associate_role)

        # Add the team member to the session
        session.add(team_member)

    # Commit all the changes to save the team and its members
    session.commit()

    print(f"Assigned all employees to the {headsub_team.name} team with appropriate roles.")

    # Add workstations
    workstations = {}
    for ws_data in workstations_data:
        # Get the line type ID
        line_type = session.query(LineTypeModel).filter_by(name=ws_data["line_type"]).first()

        workstation = WorkstationModel(
            name=ws_data["name"],
            line_type_id=line_type.id,
            is_loading_job=ws_data["is_loading_job"],
            is_heavy_job=ws_data["is_heavy_job"],
            is_key_skill_job=ws_data["is_key_skill_job"],
            team_id=headsub_team.id  # Assign to headsub team
        )
        session.add(workstation)
        session.commit()  # Commit to get the workstation id
        workstations[ws_data["name"]] = workstation

    # Create WatcherHeartbeat table if it doesn't exist
    from sqlalchemy import inspect
    inspector = inspect(engine)
    if not inspector.has_table(WatcherHeartbeatModel.__tablename__):
        WatcherHeartbeatModel.__table__.create(bind=engine)

    session.commit()

    # Define your test date and cycle of fake dates
    fake_dates = cycle([get_test_date() + timedelta(days=i) for i in range(5)])

    # Add EmployeeWorkstation entries using the universal test date
    for employee_data in employees_data:
        employee = employees[employee_data["name"]]
        known_stations = employee_data.get("known_stations", "").split(',')

        if known_stations == ['']:
            known_stations = []  # Handle case where no stations are known

        for station_name in known_stations:
            workstation = workstations.get(station_name)

            if workstation:
                last_worked_date = next(fake_dates)  # Use the next fake date

                # Create and add the EmployeeWorkstation entry
                employee_workstation = EmployeeWorkstationModel(
                    employee_id=employee.id,
                    station_id=workstation.id,
                    last_worked_date=last_worked_date
                )
                session.add(employee_workstation)
    session.commit()
    print(f"Added {len(employees_data)} employees to the {headsub_team.name} team.")


if __name__ == "__main__":
    # Reset and seed the database
    reset_database()
    # Create a session
    session = Session()
    # Seed the database
    seed_data(session)
    print("Database seeding complete.")
