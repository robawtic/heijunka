import os
import json
import random
from pathlib import Path
from faker import Faker

fake = Faker()


def write_json(path: Path, data: dict):
    """
    Write `data` as JSON (indented) to `path`, creating parent directories if needed.
    Always overwrites any existing file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def make_abbreviation(team_name: str) -> str:
    """
    Return a 1–3‐character uppercase abbreviation for a given team_name.
    For 'shortblock', we force 'SB'. Otherwise, take up to the first 3 letters.
    """
    if team_name.lower() == "shortblock":
        return "SB"
    cleaned = "".join(ch for ch in team_name if ch.isalnum())
    return cleaned[:3].upper()


if __name__ == "__main__":
    # 1. Locate the "departments" root
    base_dir = Path(__file__).resolve().parent
    departments_root = base_dir / "seed_data" / "departments"

    # 2. For every department folder under "departments":
    for dept_path in departments_root.iterdir():
        if not dept_path.is_dir():
            continue

        dept_name = dept_path.name
        # Overwrite department.json
        dept_json_path = dept_path / "department.json"
        dept_json = {
            "name": dept_name,
            "production_manager": fake.name(),
            "associate_representative": fake.name(),
        }
        write_json(dept_json_path, dept_json)

        # 2b. Look for a "groups" subfolder
        groups_dir = dept_path / "groups"
        if not groups_dir.is_dir():
            continue

        # 2c. Collect immediate subdirectory names under "groups"
        group_names = [p.name for p in groups_dir.iterdir() if p.is_dir()]

        # 2d. Build or overwrite "<department>_groups.json"
        group_json_path = groups_dir / f"{dept_name}_groups.json"
        groups_json = {"groups": {name: {} for name in group_names}}
        write_json(group_json_path, groups_json)

        # 3. For each group folder, create group.json and teams-level listing
        for group_name in group_names:
            group_path = groups_dir / group_name

            # 3a. Overwrite group.json in each group directory
            group_info = {
                "name": group_name,
                "group_leader": fake.name()
            }
            write_json(group_path / "group.json", group_info)

            teams_dir = group_path / "teams"
            if not teams_dir.is_dir():
                continue

            # 3b. Collect immediate subdirectory names under "teams"
            team_names = [p.name for p in teams_dir.iterdir() if p.is_dir()]

            # 3c. Write "<group>_teams.json" inside the "teams" folder
            teams_json_path = teams_dir / f"{group_name}_teams.json"
            teams_json = {"teams": team_names}
            write_json(teams_json_path, teams_json)

            # 4. For each team, create or overwrite workstation.json and employee.json
            for team_name in team_names:
                team_path = teams_dir / team_name

                # 4a. Generate workstation.json first (overwrite if exists)
                abbr = make_abbreviation(team_name)
                count = random.randint(7, 13)
                choices = random.sample(list(range(10, 301, 10)), count)
                choices.sort()
                workstations = [{"name": f"{abbr}{num:03}"} for num in choices]

                workstation_json = {"workstations": workstations}
                write_json(team_path / "workstation.json", workstation_json)

                # 4b. Generate employee.json next (overwrite if exists)
                station_names = [ws["name"] for ws in workstations]
                num_jobs = len(station_names)
                num_employees = num_jobs + 4  # exactly 4 more employees than jobs

                employees = []
                # 1 Team Leader (knows no stations)
                employees.append(
                    {"name": fake.first_name(), "role": "Team Leader", "known_stations": []}
                )

                # 1 Backup (knows all stations)
                employees.append(
                    {"name": fake.first_name(), "role": "Backup", "known_stations": station_names.copy()}
                )

                # Remaining are Associates
                associates_needed = num_employees - 2
                for _ in range(associates_needed):
                    # Each associate knows a random subset of stations (at least 3, up to all)
                    subset_size = random.randint(min((num_jobs-2), num_jobs), num_jobs)
                    known_stations = random.sample(station_names, subset_size)
                    employees.append(
                        {"name": fake.first_name(), "role": "Associate", "known_stations": known_stations}
                    )

                employee_json = {"employees": employees}
                write_json(team_path / "employee.json", employee_json)

    print("✅ JSON files regenerated (existing ones overwritten).")
