import os
import shutil
import json
import argparse
import sys
from typing import Dict, Any, List, Optional


def ensure_directory(directory: str) -> None:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        directory: The directory path
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def copy_file(source: str, destination: str) -> None:
    """
    Copy a file from source to destination.

    Args:
        source: The source file path
        destination: The destination file path
    """
    if os.path.exists(source):
        shutil.copy2(source, destination)
        print(f"Copied {source} to {destination}")
    else:
        print(f"Warning: Source file {source} does not exist")


def load_json(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load a JSON file.

    Args:
        file_path: The path to the JSON file

    Returns:
        The loaded JSON data, or None if the file doesn't exist or is invalid
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: File not found: {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON in file: {file_path}")
        return None


def save_json(file_path: str, data: Dict[str, Any]) -> None:
    """
    Save data to a JSON file.

    Args:
        file_path: The path to the JSON file
        data: The data to save
    """
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved {file_path}")


def refactor_team_data(source_dir: str, destination_dir: str, team_name: str) -> None:
    """
    Refactor team data from the old structure to the new structure.

    Args:
        source_dir: The source directory
        destination_dir: The destination directory
        team_name: The name of the team
    """
    print(f"Refactoring team data for {team_name}...")

    # Create destination directory
    ensure_directory(destination_dir)

    # Copy README.md if it exists
    source_readme = os.path.join(source_dir, "README.md")
    destination_readme = os.path.join(destination_dir, "README.md")
    copy_file(source_readme, destination_readme)

    # Load workstations.json
    source_workstations = os.path.join(source_dir, "workstations.json")
    workstations_data = load_json(source_workstations)

    if workstations_data:
        # Save workstations.json to the new location
        destination_workstations = os.path.join(destination_dir, "workstations.json")
        save_json(destination_workstations, workstations_data)

    # Load employees.json
    source_employees = os.path.join(source_dir, "employees.json")
    employees_data = load_json(source_employees)

    if employees_data:
        # Save employees.json to the new location
        destination_employees = os.path.join(destination_dir, "employees.json")
        save_json(destination_employees, employees_data)


def refactor_group_data(source_dir: str, destination_dir: str, group_name: str) -> None:
    """
    Refactor group data from the old structure to the new structure.

    Args:
        source_dir: The source directory
        destination_dir: The destination directory
        group_name: The name of the group
    """
    print(f"Refactoring group data for {group_name}...")

    # Create destination directory
    ensure_directory(destination_dir)

    # Create teams directory
    teams_dir = os.path.join(destination_dir, "teams")
    ensure_directory(teams_dir)

    # Get teams in the source directory
    source_teams_dir = os.path.join(source_dir, "teams")
    if os.path.exists(source_teams_dir):
        for team_name in os.listdir(source_teams_dir):
            source_team_dir = os.path.join(source_teams_dir, team_name)
            if os.path.isdir(source_team_dir):
                destination_team_dir = os.path.join(teams_dir, team_name)
                refactor_team_data(source_team_dir, destination_team_dir, team_name)


def refactor_department_data(source_dir: str, destination_dir: str, department_name: str) -> None:
    """
    Refactor department data from the old structure to the new structure.

    Args:
        source_dir: The source directory
        destination_dir: The destination directory
        department_name: The name of the department
    """
    print(f"Refactoring department data for {department_name}...")

    # Create destination directory
    ensure_directory(destination_dir)

    # Create groups directory
    groups_dir = os.path.join(destination_dir, "groups")
    ensure_directory(groups_dir)

    # Get groups in the source directory
    source_groups_dir = os.path.join(source_dir)
    if os.path.exists(source_groups_dir):
        for group_name in os.listdir(source_groups_dir):
            source_group_dir = os.path.join(source_groups_dir, group_name)
            if os.path.isdir(source_group_dir) and group_name != "teams":
                destination_group_dir = os.path.join(groups_dir, group_name)
                refactor_group_data(source_group_dir, destination_group_dir, group_name)


def refactor_seed_data(source_base_dir: str, destination_base_dir: str) -> None:
    """
    Refactor seed data from the old structure to the new structure.

    Args:
        source_base_dir: The source base directory
        destination_base_dir: The destination base directory
    """
    print(f"Refactoring seed data from {source_base_dir} to {destination_base_dir}...")

    # Create destination directory
    ensure_directory(destination_base_dir)

    # Create departments directory
    departments_dir = os.path.join(destination_base_dir, "departments")
    ensure_directory(departments_dir)

    # Create powertrain department directory
    powertrain_dir = os.path.join(departments_dir, "powertrain")
    ensure_directory(powertrain_dir)

    # Refactor powertrain department data
    source_powertrain_dir = os.path.join(source_base_dir, "groups")
    refactor_department_data(source_powertrain_dir, powertrain_dir, "powertrain")

    print("Refactoring complete!")


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        The parsed arguments
    """
    parser = argparse.ArgumentParser(description='Refactor seed data from the old structure to the new structure')
    parser.add_argument('--source', type=str, default='infrastructure/seeding/seed_data', help='Source base directory')
    parser.add_argument('--destination', type=str, default='infrastructure/seeding/seed_data_new', help='Destination base directory')

    return parser.parse_args()


def main():
    """
    Main entry point for the refactoring script.
    """
    try:
        # Parse arguments
        args = parse_arguments()

        # Refactor seed data
        refactor_seed_data(args.source, args.destination)

        return 0
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
