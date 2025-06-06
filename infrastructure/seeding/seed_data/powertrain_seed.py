# infrastructure/seeding/powertrain_seed.py

import json
import os
import random
import math
from pathlib import Path
from typing import List, Dict

from faker import Faker
from sqlalchemy.orm import Session

from domain.models.DepartmentModel import DepartmentModel
from domain.models.GroupModel import GroupModel
from domain.models.TeamModel import TeamModel
from domain.models.WorkstationModel import WorkstationModel
from domain.models.EmployeeModel import EmployeeModel
from domain.models.TeamMemberModel import TeamMemberModel
from domain.models.EmployeeWorkstationModel import EmployeeWorkstationModel
from domain.models.TeamAroModel import TeamAroModel, AroTeamStatus
from domain.models.RoleModel import RoleModel
from domain.models.LineTypeModel import LineTypeModel
from domain.models.db import Session as SessionFactory

from utilities.secure_logging import redact_log_message

fake = Faker()


def load_json_data(file_path: Path):
    """
    Load a JSON file and return its contents as a Python object.
    If the file is missing or invalid, logs a warning and returns None.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(redact_log_message(f"Warning: File not found: {file_path}", file_paths=[str(file_path)]))
        return None
    except json.JSONDecodeError:
        print(redact_log_message(f"Warning: Invalid JSON in file: {file_path}", file_paths=[str(file_path)]))
        return None


def pick_aros_for_team(team_id: int, candidates: List[int], workstations_by_team: Dict[int, List[int]], coverage_pct: float) -> List[int]:
    """
    Select a subset of employees from other teams to serve as AROs for a given team.

    Args:
        team_id: The target team we want ARO coverage for.
        candidates: A list of employee IDs from other teams (i.e. not the same team_id).
        workstations_by_team: A dictionary mapping team IDs to lists of workstation IDs.
        coverage_pct: A float representing the fraction of total workstations to cover.

    Returns:
        A list of selected employee_id values that will serve as AROs for this team_id.
    """
    if team_id not in workstations_by_team or not workstations_by_team[team_id]:
        return []

    num_jobs = len(workstations_by_team[team_id])
    target_aros = max(3, math.ceil(num_jobs * coverage_pct))

    # If there aren't enough candidates, take as many as possible
    if len(candidates) <= target_aros:
        return candidates

    # Randomly sample target_aros distinct IDs from candidates
    return random.sample(candidates, target_aros)


def seed_powertrain_data(session: Session):
    """
    Seeds the database with Powertrain department data,
    loading from JSON files generated under infrastructure/seeding/seed_data/departments/powertrain.
    """
    # Dictionaries to store IDs for ARO seeding
    teams_by_name = {}  # {team_name: team_id}
    employees_by_team = {}  # {team_id: [employee_id, ...]}
    workstations_by_team = {}  # {team_id: [workstation_id, ...]}
    # 1) Ensure core roles exist
    role_names = ['Group Leader', 'Team Leader', 'Backup', 'Associate']
    role_objs = {}
    for rn in role_names:
        role = session.query(RoleModel).filter_by(name=rn).first()
        if not role:
            role = RoleModel(name=rn)
            session.add(role)
        role_objs[rn] = role
    session.commit()

    # 2) Ensure line types exist (assuming these appear in workstation JSONs)
    line_types = {
        "Mainline": "Main assembly line",
        "Sub-Assembly": "Sub-assembly line",
        "Test": "Testing station"
    }
    lt_objs = {}
    for lt_name, lt_desc in line_types.items():
        lt = session.query(LineTypeModel).filter_by(name=lt_name).first()
        if not lt:
            lt = LineTypeModel(name=lt_name, description=lt_desc)
            session.add(lt)
        lt_objs[lt_name] = lt
    session.commit()

    # 3) Load department.json
    project_root = Path(__file__).resolve().parent.parent.parent  # infrastructure/seeding/seed_data → infrastructure
    powertrain_dir = project_root / "seeding" / "seed_data" / "departments" / "powertrain"
    dept_json = load_json_data(powertrain_dir / "department.json")
    if not dept_json:
        print("❌ Cannot find department.json for Powertrain. Aborting seed.")
        return

    # 4) Create or fetch DepartmentModel
    dept_name = dept_json.get("name", "Powertrain")
    dept_obj = session.query(DepartmentModel).filter_by(name=dept_name).first()
    if not dept_obj:
        # Create a description from production_manager and associate_representative
        description = f"Production Manager: {dept_json.get('production_manager', '')}, Associate Representative: {dept_json.get('associate_representative', '')}"
        dept_obj = DepartmentModel(
            name=dept_name,
            description=description
        )
        session.add(dept_obj)
        session.commit()
        print(f"  Created Department: {dept_name}")
    else:
        # Update description if needed
        description = f"Production Manager: {dept_json.get('production_manager', '')}, Associate Representative: {dept_json.get('associate_representative', '')}"
        dept_obj.description = description
        session.commit()

    # 5) Load <department>_groups.json
    groups_json = load_json_data(powertrain_dir / "groups" / f"{dept_name}_groups.json")
    if not groups_json or "groups" not in groups_json:
        print("❌ Cannot find or parse powertrain_groups.json. Aborting seed.")
        return

    group_objs = {}
    # 6) For each group, create or fetch GroupModel, then process its JSON
    for group_name in groups_json["groups"].keys():
        group_dir = powertrain_dir / "groups" / group_name

        # 6a) Load group.json
        group_data = load_json_data(group_dir / "group.json")
        if not group_data:
            print(f"  ⚠ Skipping group '{group_name}' (missing group.json).")
            continue

        # 6b) Create or fetch GroupModel
        grp_obj = session.query(GroupModel).filter_by(name=group_name, department_id=dept_obj.id).first()
        if not grp_obj:
            grp_obj = GroupModel(
                name=group_name,
                department_id=dept_obj.id
            )
            session.add(grp_obj)
            session.commit()
            print(f"  Created Group: {group_name} (Group Leader: {group_data.get('group_leader', '')})")
        else:
            # No group_leader field in GroupModel, so we just log it
            print(f"  Group exists: {group_name} (Group Leader: {group_data.get('group_leader', '')})")
            session.commit()
        group_objs[group_name] = grp_obj

        # 6c) Load <group>_teams.json
        teams_json = load_json_data(group_dir / "teams" / f"{group_name}_teams.json")
        if not teams_json or "teams" not in teams_json:
            print(f"  ⚠ No teams file for group '{group_name}'. Skipping teams.")
            continue

        team_objs = {}
        # 7) For each team name, create or fetch TeamModel
        for team_name in teams_json["teams"]:
            team_dir = group_dir / "teams" / team_name
            # No team_metadata.json is generated by build_json.py, so we'll skip this step
            team_data = None

            # Check if a team with this name exists anywhere in the database
            existing_team = session.query(TeamModel).filter_by(name=team_name).first()
            if existing_team:
                # Generate a new unique name by adding a suffix
                suffix = 1
                new_team_name = f"{team_name}-{suffix}"
                while session.query(TeamModel).filter_by(name=new_team_name).first():
                    suffix += 1
                    new_team_name = f"{team_name}-{suffix}"
                print(f"    ⚠ Team name '{team_name}' already exists, using '{new_team_name}' instead.")
                team_name = new_team_name

            t_obj = session.query(TeamModel).filter_by(name=team_name, group_id=grp_obj.id).first()
            if not t_obj:
                t_obj = TeamModel(name=team_name, group_id=grp_obj.id)
                session.add(t_obj)
                session.commit()
                print(f"    Created Team: {team_name}")
            team_objs[team_name] = t_obj

            # Store team ID for ARO seeding
            teams_by_name[team_name] = t_obj.id
            if t_obj.id not in employees_by_team:
                employees_by_team[t_obj.id] = []
            if t_obj.id not in workstations_by_team:
                workstations_by_team[t_obj.id] = []

            # 8) Load workstation.json for this team
            ws_json = load_json_data(team_dir / "workstation.json")
            if ws_json and "workstations" in ws_json:
                for ws_item in ws_json["workstations"]:
                    ws_name = ws_item.get("name")
                    # Determine line_type from WS code prefix, or default to “Mainline”
                    lt_key = "Mainline"
                    if ws_item.get("line_type"):
                        lt_key = ws_item["line_type"]
                    lt_obj = lt_objs.get(lt_key, lt_objs["Mainline"])

                    ws_obj = session.query(WorkstationModel).filter_by(name=ws_name, team_id=t_obj.id).first()
                    if not ws_obj:
                        ws_obj = WorkstationModel(
                            name=ws_name,
                            line_type_id=lt_obj.id,
                            is_loading_job=ws_item.get("is_loading_job", False),
                            is_heavy_job=ws_item.get("is_heavy_job", False),
                            is_key_skill_job=ws_item.get("is_key_skill_job", False),
                            team_id=t_obj.id
                        )
                        session.add(ws_obj)
                        session.commit()
                        print(f"      Created Workstation: {ws_name}")

                        # Store workstation ID for ARO seeding
                        workstations_by_team[t_obj.id].append(ws_obj.id)
            else:
                print(f"      ⚠ No workstation.json for team '{team_name}'")

            # 9) Load employee.json for this team
            emp_json = load_json_data(team_dir / "employee.json")
            if emp_json and "employees" in emp_json:
                for emp_data in emp_json["employees"]:
                    emp_name = emp_data.get("name")
                    emp_role = emp_data.get("role", "Associate")
                    known_stations = emp_data.get("known_stations", [])

                    # Check if an employee with this name exists anywhere in the database
                    existing_emp = session.query(EmployeeModel).filter_by(name=emp_name).first()
                    if existing_emp:
                        # Generate a new unique name by adding a suffix
                        suffix = 1
                        while session.query(EmployeeModel).filter_by(name=f"{emp_name}_{suffix}").first():
                            suffix += 1
                        emp_name = f"{emp_name}_{suffix}"
                        print(f"      ⚠ Employee name '{emp_data.get('name')}' already exists, using '{emp_name}' instead.")

                    # Now check if this employee exists in this team
                    emp_obj = session.query(EmployeeModel).filter_by(name=emp_name, team_id=t_obj.id).first()
                    if not emp_obj:
                        emp_obj = EmployeeModel(name=emp_name, team_id=t_obj.id, is_active=True)
                        session.add(emp_obj)
                        session.commit()
                        print(f"      Created Employee: {emp_name}")

                        # Store employee ID for ARO seeding
                        employees_by_team[t_obj.id].append(emp_obj.id)

                    # Create TeamMember mapping
                    tm_obj = (
                        session.query(TeamMemberModel)
                        .filter_by(team_id=t_obj.id, employee_id=emp_obj.id)
                        .first()
                    )
                    if not tm_obj:
                        tm_obj = TeamMemberModel(team_id=t_obj.id, employee_id=emp_obj.id)
                        session.add(tm_obj)
                        session.commit()

                    # Assign roles to this team member
                    # Clear existing roles, then re-add
                    tm_obj.roles.clear()
                    # Every employee is at least an Associate
                    tm_obj.roles.append(role_objs['Associate'])
                    if emp_role == "Team Leader":
                        tm_obj.roles.append(role_objs['Team Leader'])
                    elif emp_role == "Backup":
                        tm_obj.roles.append(role_objs['Backup'])
                    session.commit()
                    print(f"      Assigned roles for Employee: {emp_name}")

                    # 10) Link KnownStations (EmployeeWorkstationModel)
                    for station_code in known_stations:
                        ws_obj = (
                            session.query(WorkstationModel)
                            .filter_by(name=station_code, team_id=t_obj.id)
                            .first()
                        )
                        if not ws_obj:
                            print(redact_log_message(
                                f"        Warning: Workstation '{station_code}' not found for team '{team_name}'",
                                file_paths=[str(team_dir / "workstation.json")]
                            ))
                            continue

                        ew_obj = (
                            session.query(EmployeeWorkstationModel)
                            .filter_by(employee_id=emp_obj.id, station_id=ws_obj.id)
                            .first()
                        )
                        if not ew_obj:
                            ew_obj = EmployeeWorkstationModel(
                                employee_id=emp_obj.id,
                                station_id=ws_obj.id,
                                last_worked_date=None
                            )
                            session.add(ew_obj)
                            session.commit()
                            print(f"        Linked {emp_name} → {station_code}")
            else:
                print(f"      ⚠ No employee.json for team '{team_name}'")

    # ARO seeding: For each team, select AROs from other teams and assign them workstations
    print("\nStarting ARO seeding...")
    coverage_pct = 0.30  # 30% coverage of workstations

    for team_id, workstations in workstations_by_team.items():
        if not workstations:
            print(f"  Skipping ARO seeding for team ID {team_id} (no workstations)")
            continue

        # Get all employees from other teams as candidates
        candidates = []
        for other_team_id, employee_ids in employees_by_team.items():
            if other_team_id != team_id:
                candidates.extend(employee_ids)

        if not candidates:
            print(f"  Skipping ARO seeding for team ID {team_id} (no candidates from other teams)")
            continue

        # Select AROs for this team
        aro_employee_ids = pick_aros_for_team(team_id, candidates, workstations_by_team, coverage_pct)

        if not aro_employee_ids:
            print(f"  No AROs selected for team ID {team_id}")
            continue

        print(f"  Selected {len(aro_employee_ids)} AROs for team ID {team_id}")

        # For each ARO, create TeamAroModel and assign workstations
        for aro_emp_id in aro_employee_ids:
            # Create TeamAroModel row linking this employee as floater/ARO
            team_aro = TeamAroModel(
                team_id=team_id,
                employee_id=aro_emp_id,
                status=AroTeamStatus.ACTIVE
            )
            session.add(team_aro)

            # Decide which workstations this ARO knows
            ws_ids = workstations_by_team[team_id]
            if len(ws_ids) <= 2:
                # If there are only 1-2 workstations, assign all of them
                subset_size = len(ws_ids)
            else:
                # Pick anywhere from 3 to len(ws_ids) random workstations
                subset_size = random.randint(min(3, len(ws_ids)), len(ws_ids))

            known_ws_ids = random.sample(ws_ids, subset_size)

            # Create EmployeeWorkstationModel rows for each known workstation
            for ws_id in known_ws_ids:
                emp_ws = EmployeeWorkstationModel(
                    employee_id=aro_emp_id,
                    station_id=ws_id,
                    last_worked_date=None
                )
                session.add(emp_ws)

            print(f"    ARO employee ID {aro_emp_id} assigned {len(known_ws_ids)} workstations")

        session.flush()

    session.commit()
    print("✅ ARO seeding completed successfully.")
    print("✅ Powertrain department data seeded successfully.")
