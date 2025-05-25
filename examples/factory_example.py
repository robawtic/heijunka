# examples/factory_example.py
"""
This example demonstrates how to use the factory pattern to create domain entities.
"""
from datetime import date

from domain.factories.employee_factory import EmployeeFactory
from domain.factories.workstation_factory import WorkstationFactory
from domain.value_objects.employee_availability import EmployeeAvailability, AvailabilityStatus
from domain.services.employee_service import EmployeeService
from domain.repositories.implementations.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from domain.repositories.implementations.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from domain.models.db import Session


def create_entities_with_factories():
    """Demonstrate creating entities with factories."""
    print("Creating entities with factories...")

    # Create an employee using the factory
    employee = EmployeeFactory.create_employee(
        name="John Doe",
        team_id=1,
        roles=["Associate"],
        qualifications=["H010", "H080/H090"]
    )
    print(f"Created employee: {employee.name} with roles {employee.roles}")

    # Create an employee with availability
    today = date.today()
    availability = EmployeeAvailability(
        employee_id=None,  # Will be set when the employee is saved
        date=today,
        status=AvailabilityStatus.CALL_IN,
        period=None
    )

    employee_with_availability = EmployeeFactory.create_employee_with_availability(
        name="Jane Smith",
        team_id=1,
        roles=["Team Leader", "Associate"],
        availabilities=[availability]
    )
    print(f"Created employee with availability: {employee_with_availability.name}")
    print(f"Availability periods: {len(employee_with_availability.available_periods)}")

    # Create workstations using the factory
    workstation = WorkstationFactory.create_workstation(
        name="H010",
        line_type="Sub-Assembly",
        is_loading_job=True,
        team_id=1
    )
    print(f"Created workstation: {workstation.name} ({workstation.line_type})")

    # Create a specialized workstation
    heavy_workstation = WorkstationFactory.create_heavy_workstation(
        name="H170",
        line_type="Sub-Assembly",
        team_id=1
    )
    print(f"Created heavy workstation: {heavy_workstation.name}")
    print(f"Is loading job: {heavy_workstation.is_loading_job}")
    print(f"Is heavy job: {heavy_workstation.is_heavy_job}")


def use_service_with_factories():
    """Demonstrate using services with factories."""
    print("\nUsing services with factories...")

    # Create a session
    session = Session()

    try:
        # Create repositories
        employee_repo = SqlAlchemyEmployeeRepository(session)
        workstation_repo = SqlAlchemyWorkstationRepository(session)

        # Create a service with repositories
        employee_service = EmployeeService(
            employee_repository=employee_repo,
            workstation_repository=workstation_repo
        )

        # Use the service to create an employee
        employee = employee_service.create_employee(
            name="Bob Johnson",
            team_id=1,
            roles=["Associate"]
        )
        print(f"Created and saved employee: {employee.name}")

        # Use the service to create a workstation
        workstation = employee_service.create_workstation(
            name="H200",
            line_type="Sub-Assembly",
            team_id=1,
            is_loading_job=True
        )
        print(f"Created and saved workstation: {workstation.name}")

    finally:
        session.close()


def main():
    """Run the example."""
    print("Factory Pattern Example")
    print("======================")

    create_entities_with_factories()

    # Uncomment to test with database
    # use_service_with_factories()


if __name__ == "__main__":
    main()
