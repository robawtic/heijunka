# examples/factory_examples.py
"""
This example demonstrates how to use the factory pattern to create domain entities.
"""
from datetime import date

from domain.factories.team_factory import TeamFactory
from domain.factories.schedule_factory import ScheduleFactory
from domain.factories.assignment_factory import AssignmentFactory
from domain.factories.employee_factory import EmployeeFactory
from domain.factories.workstation_factory import WorkstationFactory
from domain.contexts.employee_management.entities.employee import Employee
from domain.contexts.workstation_management.entities.workstation import Workstation
from domain.contexts.employee_management.entities.team import Team
from domain.contexts.scheduling.entities.model import Schedule
from domain.contexts.scheduling.value_objects.schedule_period import SchedulePeriod
from domain.contexts.assignment.value_objects.work_assignment import WorkAssignment

def demonstrate_team_factory():
    """Demonstrate using the TeamFactory."""
    print("\n=== TeamFactory Examples ===")
    
    # Create a basic team
    team = TeamFactory.create_team(
        name="Example Team",
        description="A team created using TeamFactory"
    )
    print(f"Created team: {team.name} - {team.description}")
    
    # Create employees using EmployeeFactory
    employee1 = EmployeeFactory.create_employee(
        name="John Doe",
        team_id=team.id,
        roles=["Team Leader", "Associate"]
    )
    
    employee2 = EmployeeFactory.create_employee(
        name="Jane Smith",
        team_id=team.id,
        roles=["Associate"]
    )
    
    # Create a team with members
    team_with_members = TeamFactory.create_team_with_members(
        name="Team with Members",
        description="A team with pre-defined members",
        members=[employee1, employee2]
    )
    print(f"Created team with {len(team_with_members.members)} members")
    
    # Create workstations using WorkstationFactory
    workstation1 = WorkstationFactory.create_workstation(
        name="WS001",
        line_type="Mainline",
        team_id=team.id
    )
    
    workstation2 = WorkstationFactory.create_workstation(
        name="WS002",
        line_type="Sub-Assembly",
        team_id=team.id,
        is_loading_job=True
    )
    
    # Create a team with workstations
    team_with_workstations = TeamFactory.create_team_with_workstations(
        name="Team with Workstations",
        description="A team with pre-defined workstations",
        workstations=[workstation1, workstation2]
    )
    print(f"Created team with {len(team_with_workstations.workstations)} workstations")

def demonstrate_schedule_factory():
    """Demonstrate using the ScheduleFactory."""
    print("\n=== ScheduleFactory Examples ===")
    
    today = date.today()
    
    # Create a basic schedule
    schedule = ScheduleFactory.create_schedule(
        team_id=1,
        start_date=today,
        periods_per_day=4,
        status="pending"
    )
    print(f"Created schedule: for team {schedule.team_id} starting on {schedule.start_date}")
    
    # Create a schedule with call-ins and offline periods
    schedule_with_call_ins = ScheduleFactory.create_schedule(
        team_id=1,
        start_date=today,
        periods_per_day=4,
        status="pending",
        call_ins=["John Doe", "Jane Smith"],
        offline={"Bob Johnson": [1, 2], "Alice Brown": [3, 4]}
    )
    print(f"Created schedule with {len(schedule_with_call_ins.call_ins)} call-ins and {len(schedule_with_call_ins.offline)} offline employees")
    
    # Create a daily schedule
    daily_schedule = ScheduleFactory.create_daily_schedule(
        team_id=1,
        start_date=today,
        periods_per_day=4
    )
    print(f"Created daily schedule for {daily_schedule.start_date}")

def demonstrate_assignment_factory():
    """Demonstrate using the AssignmentFactory."""
    print("\n=== AssignmentFactory Examples ===")
    
    # Create employee and workstation
    employee = EmployeeFactory.create_employee(
        id=1,
        name="John Doe",
        team_id=1
    )
    
    # Add qualification to employee
    employee._qualifications.append("WS001")
    
    # Mock the is_available_for_period method
    original_method = employee.is_available_for_period
    employee.is_available_for_period = lambda date_obj, period: True
    
    workstation = WorkstationFactory.create_workstation(
        id=1,
        name="WS001",
        line_type="Mainline",
        team_id=1
    )
    
    today = date.today()
    period = SchedulePeriod(date=today, period=1)
    
    # Create an assignment
    try:
        assignment = AssignmentFactory.create_assignment(
            employee=employee,
            workstation=workstation,
            period=period
        )
        print(f"Created assignment: {employee.name} at {workstation.name} on {period}")
        
        # Create an assignment for a specific date and period
        assignment2 = AssignmentFactory.create_assignment_for_date(
            employee=employee,
            workstation=workstation,
            assignment_date=today,
            period_number=2
        )
        print(f"Created assignment for period {assignment2.period.period}")
        
    except ValueError as e:
        print(f"Error creating assignment: {e}")
    finally:
        # Restore original method
        employee.is_available_for_period = original_method

def main():
    """Run all demonstrations."""
    print("Factory Pattern Examples")
    print("=======================")
    
    demonstrate_team_factory()
    demonstrate_schedule_factory()
    demonstrate_assignment_factory()
    
    print("\nAll examples completed successfully.")

if __name__ == "__main__":
    main()