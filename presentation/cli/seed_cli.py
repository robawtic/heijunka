import argparse
import sys
from sqlalchemy.orm import Session

from application.commands.seed_database_command import SeedDatabaseCommand
from application.commands.seed_database_handler import SeedDatabaseHandler
from infrastructure.repositories.shared.file_seed_data_repository import FileSeedDataRepository
from infrastructure.repositories.employee_management.sqlalchemy_department_repository import SqlAlchemyDepartmentRepository
from infrastructure.repositories.employee_management.sqlalchemy_group_repository import SqlAlchemyGroupRepository
from infrastructure.repositories.employee_management.sqlalchemy_team_repository import SqlAlchemyTeamRepository
from infrastructure.repositories.workstation_management.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from infrastructure.repositories.employee_management.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from infrastructure.repositories.user_management.sqlalchemy_role_repository import SqlAlchemyRoleRepository
from infrastructure.repositories.workstation_management.sqlalchemy_line_type_repository import SqlAlchemyLineTypeRepository
from domain.models.db import Session as SessionFactory
from utilities.logging_factory import get_logger


def setup_dependencies(session: Session):
    """
    Set up and return the dependencies needed for seeding.

    Args:
        session: Database session

    Returns:
        A tuple containing the handler and repositories
    """
    # Create repositories
    seed_data_repository = FileSeedDataRepository()
    department_repository = SqlAlchemyDepartmentRepository(session)
    group_repository = SqlAlchemyGroupRepository(session)
    team_repository = SqlAlchemyTeamRepository(session)
    workstation_repository = SqlAlchemyWorkstationRepository(session)
    employee_repository = SqlAlchemyEmployeeRepository(session)
    role_repository = SqlAlchemyRoleRepository(session)
    line_type_repository = SqlAlchemyLineTypeRepository(session)

    # Create handler
    handler = SeedDatabaseHandler(
        seed_data_repository=seed_data_repository,
        department_repository=department_repository,
        group_repository=group_repository,
        team_repository=team_repository,
        workstation_repository=workstation_repository,
        employee_repository=employee_repository,
        role_repository=role_repository,
        line_type_repository=line_type_repository,
        session=session
    )

    return handler


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        The parsed arguments
    """
    parser = argparse.ArgumentParser(description='Seed the database with initial data')

    # Target options (mutually exclusive)
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument('--department', type=str, help='Department to seed')
    target_group.add_argument('--group', type=str, help='Group to seed')
    target_group.add_argument('--team', type=str, help='Team to seed')
    target_group.add_argument('--all', action='store_true', help='Seed all departments')

    # Other options
    parser.add_argument('--reset-db', action='store_true', help='Reset the database before seeding')
    parser.add_argument('--base-path', type=str, default='infrastructure/seeding/seed_data', help='Base path for seed data files')

    return parser.parse_args()


def main():
    """
    Main entry point for the seeding CLI.
    """
    logger = get_logger("presentation.cli.seed_cli")
    logger.info("Starting seeding CLI", event_type="seed_cli", identifier="start")

    try:
        # Parse arguments
        args = parse_arguments()

        # Create session
        session = SessionFactory()

        try:
            # Setup dependencies
            handler = setup_dependencies(session)

            # Create command
            command = SeedDatabaseCommand(
                department=args.department,
                group=args.group,
                team=args.team,
                reset_database=args.reset_db
            )

            # Handle command
            result = handler.handle(command)

            # Check result
            if result["status"] == "success":
                # Print success message
                if args.team:
                    print(f"Successfully seeded team '{args.team}':")
                    print(f"  Workstations created: {result['workstations_created']}")
                    print(f"  Employees created: {result['employees_created']}")
                elif args.group:
                    print(f"Successfully seeded group '{args.group}':")
                    print(f"  Teams created: {result['teams_created']}")
                    print(f"  Workstations created: {result['workstations_created']}")
                    print(f"  Employees created: {result['employees_created']}")
                elif args.department:
                    print(f"Successfully seeded department '{args.department}':")
                    print(f"  Groups created: {result['groups_created']}")
                    print(f"  Teams created: {result['teams_created']}")
                    print(f"  Workstations created: {result['workstations_created']}")
                    print(f"  Employees created: {result['employees_created']}")
                else:
                    print("Successfully seeded all departments:")
                    print(f"  Departments created: {result['departments']}")
                    print(f"  Groups created: {result['groups']}")
                    print(f"  Teams created: {result['teams']}")
                    print(f"  Workstations created: {result['workstations']}")
                    print(f"  Employees created: {result['employees']}")

                logger.info(
                    "Seeding completed successfully",
                    event_type="seed_cli",
                    identifier="success",
                    extra=result
                )

                return 0
            else:
                # Print error message
                print(f"Error: {result['message']}", file=sys.stderr)

                logger.error(
                    f"Seeding failed: {result['message']}",
                    event_type="seed_cli",
                    identifier="error"
                )

                return 1
        finally:
            # Close session
            session.close()
    except Exception as e:
        # Print error message
        print(f"Error: {str(e)}", file=sys.stderr)

        logger.error(
            f"Unexpected error: {str(e)}",
            event_type="seed_cli",
            identifier="exception",
            extra={"exception": str(e)}
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())
