# opu_team_analysis.py
from datetime import date
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.services.aro_service import AROService
from domain.repositories.implementations.sqlalchemy_team_repository import SqlAlchemyTeamRepository
from domain.repositories.implementations.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from domain.repositories.implementations.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from domain.repositories.implementations.sqlalchemy_aro_assignment_repository import SqlAlchemyAROAssignmentRepository
from domain.repositories.implementations.sqlalchemy_team_aro_repository import SqlAlchemyTeamAroRepository
from presentation.cli.utils.dependencies import setup_dependencies


def analyze_opu_team():
    """
    Analyze all OPU teams:
    1. Print all available employees for each OPU team along with the workstations they know
    2. Compute and print “coverage” data for each OPU workstation (how many employees are qualified)
    3. List qualified ARO candidates for each OPU team along with the OPU workstations they know
    """
    # Setup dependencies
    dependencies = setup_dependencies()
    session = dependencies[0]  # Extract session from dependencies tuple

    # Create repositories
    employee_repository = SqlAlchemyEmployeeRepository(session)
    team_repository = SqlAlchemyTeamRepository(session)
    workstation_repository = SqlAlchemyWorkstationRepository(session)
    aro_repository = SqlAlchemyAROAssignmentRepository(session)
    team_aro_repository = SqlAlchemyTeamAroRepository(session)

    # Create ARO service (not used for coverage, but used below for candidate lookup)
    aro_service = AROService(aro_repository, employee_repository, team_repository, team_aro_repository)

    # Get all teams
    all_teams = team_repository.get_all()

    # Filter for OPU teams (teams with "OPU" in their name, case insensitive)
    opu_teams = [team for team in all_teams if "opu" in team.name.lower()]

    if not opu_teams:
        print("Error: No OPU teams found")
        return

    print(f"Found {len(opu_teams)} OPU teams")

    # Get today's date
    today = date.today()

    # Analyze each OPU team
    for opu_team in opu_teams:
        print(f"\n{'='*20} OPU Team: {opu_team.name} {'='*20}")

        # Get all workstations for the OPU team
        opu_workstations: List[Workstation] = workstation_repository.get_by_team_id(opu_team.id)
        if not opu_workstations:
            print(f"No workstations found for team '{opu_team.name}'")
            continue

        # Build a coverage dictionary keyed by workstation.id (or .name)
        coverage_counts: Dict[int, int] = {ws.id: 0 for ws in opu_workstations}

        # Print all workstations for this OPU team
        print(f"\n=== All Workstations for {opu_team.name} Team ===")
        print(f"Total workstations: {len(opu_workstations)}")
        print("-" * 60)
        print(f"{'Workstation Name':<20} {'Workstation Type':<20} {'Description':<20}")
        print("-" * 60)
        for workstation in opu_workstations:
            workstation_type = getattr(workstation, 'workstation_type', "N/A")
            description = getattr(workstation, 'description', "")
            print(f"{workstation.name:<20} {workstation_type:<20} {description:<20}")
        print("")

        # Get all employees for the OPU team
        opu_employees: List[Employee] = employee_repository.get_by_team_id(opu_team.id)
        if not opu_employees:
            print(f"No employees found for team '{opu_team.name}'")
            continue

        # Print header for OPU team employees and compute coverage
        print(f"\n=== {opu_team.name} Team Employees and Their Qualifications ===")
        print(f"Total employees: {len(opu_employees)}")
        print("-" * 60)
        print(f"{'Employee Name':<20} {'Qualified Workstations':<40}")
        print("-" * 60)

        # For each employee, find which OPU workstations they can run, and increment coverage
        for employee in opu_employees:
            qualified_ws_names: List[str] = []
            for workstation in opu_workstations:
                # Check both can_work(...) and can_handle_workstation_type(...)
                if employee.can_work(workstation) and employee.can_handle_workstation_type(workstation):
                    qualified_ws_names.append(workstation.name)
                    coverage_counts[workstation.id] += 1

            print(f"{employee.name:<20} {', '.join(qualified_ws_names):<40}")

        # After listing employees, print coverage per workstation
        print(f"\n=== Workstation Coverage for {opu_team.name} Team ===")
        print(f"Total distinct workstations: {len(opu_workstations)}")
        print("-" * 60)
        print(f"{'Workstation Name':<20} {'# Qualified Employees':<20}")
        print("-" * 60)
        for workstation in opu_workstations:
            count = coverage_counts.get(workstation.id, 0)
            print(f"{workstation.name:<20} {count:<20}")
        print("")

        # Find qualified ARO candidates for this OPU team
        print(f"\n=== Qualified ARO Candidates for {opu_team.name} Team ===")

        # Dictionary to track qualified ARO candidates and their qualification scores
        qualified_candidates: Dict[int, Dict[str, Any]] = {}

        for donor_team in all_teams:
            # Skip the current OPU team
            if donor_team.id == opu_team.id:
                continue

            # Get the donor team's employees
            donor_employees = employee_repository.get_by_team_id(donor_team.id)
            if not donor_employees:
                continue

            # Get employees already assigned as AROs for today (i.e., who are leaving that team)
            assigned_ids = aro_repository.get_employees_leaving(donor_team.id, today)

            # Find available employees (not already assigned as AROs)
            available_employees = [e for e in donor_employees if e.id not in assigned_ids]

            # Check each available employee for qualifications
            for employee in available_employees:
                qualified_ws_names: List[str] = []
                for workstation in opu_workstations:
                    if employee.can_work(workstation) and employee.can_handle_workstation_type(workstation):
                        qualified_ws_names.append(workstation.name)

                # If employee is qualified for at least one workstation, add them as a candidate
                if qualified_ws_names:
                    qualified_candidates[employee.id] = {
                        'employee': employee,
                        'from_team': donor_team.name,
                        'qualified_workstations': qualified_ws_names,
                        'qualified_count': len(qualified_ws_names)
                    }

        # Print qualified ARO candidates (sorted by how many OPU‐team workstations they cover)
        if qualified_candidates:
            sorted_candidates = sorted(
                qualified_candidates.values(),
                key=lambda x: x['qualified_count'],
                reverse=True
            )

            print(f"Total qualified ARO candidates: {len(sorted_candidates)}")
            print("-" * 80)
            print(f"{'Employee Name':<20} {'From Team':<15} {'Qualified Workstations':<45}")
            print("-" * 80)
            for candidate in sorted_candidates:
                emp = candidate['employee']
                from_team = candidate['from_team']
                ws_list = candidate['qualified_workstations']
                print(f"{emp.name:<20} {from_team:<15} {', '.join(ws_list):<45}")
        else:
            print(f"No qualified ARO candidates found for team '{opu_team.name}'")


if __name__ == "__main__":
    analyze_opu_team()
