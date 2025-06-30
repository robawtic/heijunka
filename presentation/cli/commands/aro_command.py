"""
ARO (Assigned Relief Operator) command handling for the CLI application.
"""
import sys
from typing import Optional, Any, Dict, List, Tuple, Union, cast
from datetime import datetime, date
from sqlalchemy.orm import Session

from domain.repositories.implementations.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from domain.repositories.implementations.sqlalchemy_team_repository import SqlAlchemyTeamRepository
from domain.repositories.implementations.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from utilities.logging_factory import get_logger, RateLimitedLogger

# Create a logger for this module
logger = cast(RateLimitedLogger, get_logger("presentation.cli.commands.aro_command", rate_limit=True))

def handle_aro_assignment(
    args: Any, 
    session_factory: Any, 
    aro_service: Optional[Any] = None, 
    aro_graph_service: Optional[Any] = None
) -> bool:
    """
    Handle the ARO management commands.

    Args:
        args: Command line arguments
        session_factory: Database session factory
        aro_service: Optional ARO service instance (if None, a new one will be created)
        aro_graph_service: Optional ARO graph service instance

    Returns:
        bool: True if the operation was successful, False otherwise
    """
    logger.info(
        f"Handling ARO {args.aro_command} command", 
        event_type="aro_assignment", 
        identifier=args.aro_command
    )

    try:
        # Setup repositories
        logger.debug(
            "Setting up repositories for ARO assignment", 
            event_type="aro_assignment", 
            identifier="setup"
        )

        employee_repository = SqlAlchemyEmployeeRepository(session_factory)
        team_repository = SqlAlchemyTeamRepository(session_factory)
        workstation_repository = SqlAlchemyWorkstationRepository(session_factory)

        # Use the provided ARO service or create a new one
        if aro_service is None:
            logger.debug(
                "Creating ARO service", 
                event_type="aro_assignment", 
                identifier="service_creation"
            )

            from domain.repositories.implementations.sqlalchemy_aro_assignment_repository import SqlAlchemyAROAssignmentRepository
            from domain.repositories.implementations.sqlalchemy_team_aro_repository import SqlAlchemyTeamAroRepository
            aro_repository = SqlAlchemyAROAssignmentRepository(session_factory)
            team_aro_repository = SqlAlchemyTeamAroRepository(session_factory)
            from domain.services.aro_service import AROService
            aro_service = AROService(aro_repository, employee_repository, team_repository, team_aro_repository)

        # Handle ARO optimize command
        if args.aro_command == 'optimize':
            return handle_aro_optimize(
                args, 
                session_factory, 
                employee_repository, 
                team_repository, 
                workstation_repository, 
                aro_service, 
                aro_graph_service
            )

        # For other commands, we need an employee
        if args.aro_command != 'optimize':
            logger.debug(
                f"Processing ARO {args.aro_command} command", 
                event_type=f"aro_{args.aro_command}", 
                identifier="start"
            )

            # Get employee by name
            logger.debug(
                f"Looking up employee: {args.employee}", 
                event_type=f"aro_{args.aro_command}", 
                identifier="employee_lookup"
            )

            employee = employee_repository.get_by_name(args.employee)
            if not employee:
                error_msg = f"Error: Employee '{args.employee}' not found"
                logger.error(
                    error_msg, 
                    event_type=f"aro_{args.aro_command}", 
                    identifier="employee_lookup"
                )
                print(error_msg, file=sys.stderr)
                return False

            # Parse date
            logger.debug(
                f"Parsing date: {args.date}", 
                event_type=f"aro_{args.aro_command}", 
                identifier="date_parsing"
            )

            try:
                assignment_date = datetime.strptime(args.date, "%Y-%m-%d").date()
            except ValueError:
                error_msg = f"Error: Invalid date format. Use YYYY-MM-DD"
                logger.error(
                    error_msg, 
                    event_type=f"aro_{args.aro_command}", 
                    identifier="date_parsing"
                )
                print(error_msg, file=sys.stderr)
                return False

        # Handle ARO assign command
        if args.aro_command == 'assign':
            return handle_aro_assign(
                args, 
                employee_repository, 
                team_repository, 
                aro_service, 
                employee, 
                assignment_date
            )

        # Handle ARO remove command
        elif args.aro_command == 'remove':
            return handle_aro_remove(
                args, 
                team_repository, 
                aro_service, 
                employee, 
                assignment_date
            )

        else:
            error_msg = f"Error: Unknown ARO command '{args.aro_command}'"
            logger.error(
                error_msg, 
                event_type="aro_assignment", 
                identifier="unknown_command"
            )
            print(error_msg, file=sys.stderr)
            return False

    except Exception as e:
        error_msg = f"Error handling ARO assignment: {e}"
        logger.error(
            error_msg, 
            event_type="aro_assignment", 
            identifier="exception", 
            extra={"exception": str(e)}
        )
        print(error_msg, file=sys.stderr)
        return False

def handle_aro_optimize(
    args: Any, 
    session_factory: Any,
    employee_repository: SqlAlchemyEmployeeRepository,
    team_repository: SqlAlchemyTeamRepository,
    workstation_repository: SqlAlchemyWorkstationRepository,
    aro_service: Any,
    aro_graph_service: Optional[Any] = None
) -> bool:
    """
    Handle the ARO optimize command.

    Args:
        args: Command line arguments
        session_factory: Database session factory
        employee_repository: Repository for employee data
        team_repository: Repository for team data
        workstation_repository: Repository for workstation data
        aro_service: ARO service instance
        aro_graph_service: Optional ARO graph service instance

    Returns:
        bool: True if the operation was successful, False otherwise
    """
    logger.info(
        "Handling ARO optimize command", 
        event_type="aro_optimize", 
        identifier="start"
    )

    # Create ARO graph service if not provided
    if aro_graph_service is None:
        logger.debug(
            "Creating ARO graph service", 
            event_type="aro_optimize", 
            identifier="service_creation"
        )

        from domain.repositories.implementations.sqlalchemy_aro_assignment_repository import SqlAlchemyAROAssignmentRepository
        aro_repository = SqlAlchemyAROAssignmentRepository(session_factory)
        from domain.contexts.assignment.services.aro_graph_service import AROGraphService
        from domain.events.publisher import DomainEventPublisher
        event_publisher = DomainEventPublisher()
        aro_graph_service = AROGraphService(
            aro_service=aro_service,
            aro_repository=aro_repository,
            employee_repository=employee_repository,
            team_repository=team_repository,
            workstation_repository=workstation_repository,
            event_publisher=event_publisher
        )

    # Get team by name
    logger.debug(
        f"Looking up team: {args.team}", 
        event_type="aro_optimize", 
        identifier="team_lookup"
    )

    team = team_repository.get_by_name(args.team)
    if not team:
        error_msg = f"Error: Team '{args.team}' not found"
        logger.error(
            error_msg, 
            event_type="aro_optimize", 
            identifier="team_lookup"
        )
        print(error_msg, file=sys.stderr)
        return False

    # Parse date
    logger.debug(
        f"Parsing date: {args.date}", 
        event_type="aro_optimize", 
        identifier="date_parsing"
    )

    try:
        assignment_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    except ValueError:
        error_msg = f"Error: Invalid date format. Use YYYY-MM-DD"
        logger.error(
            error_msg, 
            event_type="aro_optimize", 
            identifier="date_parsing"
        )
        print(error_msg, file=sys.stderr)
        return False

    # Assign optimal AROs
    logger.info(
        f"Assigning {args.count} optimal AROs to team {args.team}",
        event_type="aro_optimize", 
        identifier="assignment",
        extra={
            "team_id": team.id, 
            "count": args.count, 
            "date": str(assignment_date), 
            "period": args.period
        }
    )

    assignments = aro_graph_service.assign_optimal_aros(
        understaffed_team_id=team.id,
        needed_aros=args.count,
        assignment_date=assignment_date,
        period=args.period
    )

    if assignments:
        success_msg = f"Successfully assigned {len(assignments)} AROs to team {args.team}."
        logger.info(
            success_msg, 
            event_type="aro_optimize", 
            identifier="success",
            extra={"assigned_count": len(assignments)}
        )
        print(success_msg)

        # Display the assignments
        for assignment in assignments:
            employee = employee_repository.get(assignment.employee_id)
            from_team = team_repository.get(assignment.from_team_id)
            to_team = team_repository.get(assignment.to_team_id)

            employee_name = employee.name if employee else f"Employee {assignment.employee_id}"
            from_team_name = from_team.name if from_team else f"Team {assignment.from_team_id}"
            to_team_name = to_team.name if to_team else f"Team {assignment.to_team_id}"

            period_str = f" for period {assignment.period}" if assignment.period else " for the full day"
            assignment_detail = f"- {employee_name} from {from_team_name} to {to_team_name}{period_str}"
            logger.debug(
                assignment_detail, 
                event_type="aro_optimize", 
                identifier="assignment_detail",
                extra={
                    "employee_id": assignment.employee_id, 
                    "from_team_id": assignment.from_team_id,
                    "to_team_id": assignment.to_team_id, 
                    "period": assignment.period
                }
            )
            print(assignment_detail)

        return True
    else:
        error_msg = f"Could not find suitable AROs for team {args.team}."
        logger.warning(
            error_msg, 
            event_type="aro_optimize", 
            identifier="no_assignments"
        )
        print(error_msg)
        return False

def handle_aro_assign(
    args: Any,
    employee_repository: SqlAlchemyEmployeeRepository,
    team_repository: SqlAlchemyTeamRepository,
    aro_service: Any,
    employee: Any,
    assignment_date: date
) -> bool:
    """
    Handle the ARO assign command.

    Args:
        args: Command line arguments
        employee_repository: Repository for employee data
        team_repository: Repository for team data
        aro_service: ARO service instance
        employee: Employee to assign as ARO
        assignment_date: Date for the assignment

    Returns:
        bool: True if the operation was successful, False otherwise
    """
    # Get from team by name
    logger.debug(
        f"Looking up from team: {args.from_team}", 
        event_type="aro_assign", 
        identifier="from_team_lookup"
    )

    from_team = team_repository.get_by_name(args.from_team)
    if not from_team:
        error_msg = f"Error: Team '{args.from_team}' not found"
        logger.error(
            error_msg, 
            event_type="aro_assign", 
            identifier="from_team_lookup"
        )
        print(error_msg, file=sys.stderr)
        return False

    # Get to team by name
    logger.debug(
        f"Looking up to team: {args.to_team}", 
        event_type="aro_assign", 
        identifier="to_team_lookup"
    )

    to_team = team_repository.get_by_name(args.to_team)
    if not to_team:
        error_msg = f"Error: Team '{args.to_team}' not found"
        logger.error(
            error_msg, 
            event_type="aro_assign", 
            identifier="to_team_lookup"
        )
        print(error_msg, file=sys.stderr)
        return False

    # Verify employee belongs to from_team
    logger.debug(
        f"Verifying employee {args.employee} belongs to team {args.from_team}",
        event_type="aro_assign", 
        identifier="team_membership"
    )

    if employee.team_id != from_team.id:
        error_msg = f"Error: Employee '{args.employee}' does not belong to team '{args.from_team}'"
        logger.error(
            error_msg, 
            event_type="aro_assign", 
            identifier="team_membership"
        )
        print(error_msg, file=sys.stderr)
        return False

    # Assign ARO
    logger.info(
        f"Assigning {args.employee} as ARO from {args.from_team} to {args.to_team} on {args.date}",
        event_type="aro_assign", 
        identifier="assignment",
        extra={
            "employee_id": employee.id, 
            "from_team_id": from_team.id,
            "to_team_id": to_team.id, 
            "date": str(assignment_date), 
            "period": args.period
        }
    )

    result = aro_service.assign_aro(employee.id, to_team.id, assignment_date, args.period)

    if result["status"] == "success":
        period_str = f" for period {args.period}" if args.period else " for the full day"
        success_msg = f"Successfully assigned {args.employee} as ARO from {args.from_team} to {args.to_team} on {args.date}{period_str}"
        logger.info(
            success_msg, 
            event_type="aro_assign", 
            identifier="success"
        )
        print(success_msg)
        return True
    else:
        error_msg = f"Error: {result['message']}"
        logger.error(
            error_msg, 
            event_type="aro_assign", 
            identifier="failure",
            extra={"error_details": result.get("details", "")}
        )
        print(error_msg, file=sys.stderr)
        return False

def handle_aro_remove(
    args: Any,
    team_repository: SqlAlchemyTeamRepository,
    aro_service: Any,
    employee: Any,
    assignment_date: date
) -> bool:
    """
    Handle the ARO remove command.

    Args:
        args: Command line arguments
        team_repository: Repository for team data
        aro_service: ARO service instance
        employee: Employee whose ARO assignment should be removed
        assignment_date: Date of the assignment to remove

    Returns:
        bool: True if the operation was successful, False otherwise
    """
    # Find the ARO assignment
    logger.debug(
        f"Finding ARO assignment for {args.employee} on {args.date}",
        event_type="aro_remove", 
        identifier="assignment_lookup"
    )

    assignment = aro_service.find_aro_assignment(employee.id, assignment_date, args.period)
    if not assignment:
        period_str = f" for period {args.period}" if args.period else " for the full day"
        error_msg = f"Error: No ARO assignment found for {args.employee} on {args.date}{period_str}"
        logger.error(
            error_msg, 
            event_type="aro_remove", 
            identifier="assignment_lookup"
        )
        print(error_msg, file=sys.stderr)
        return False

    # Get the from and to teams for display
    logger.debug(
        "Getting team information for ARO assignment", 
        event_type="aro_remove", 
        identifier="team_lookup"
    )

    from_team = team_repository.get(assignment.from_team_id)
    to_team = team_repository.get(assignment.to_team_id)

    # Remove the ARO assignment
    logger.info(
        f"Removing ARO assignment for {args.employee} on {args.date}",
        event_type="aro_remove", 
        identifier="removal",
        extra={
            "assignment_id": assignment.id, 
            "employee_id": employee.id,
            "from_team_id": assignment.from_team_id, 
            "to_team_id": assignment.to_team_id,
            "date": str(assignment_date), 
            "period": assignment.period
        }
    )

    result = aro_service.remove_aro_assignment(assignment.id)

    if result["status"] == "success":
        period_str = f" for period {args.period}" if args.period else " for the full day"
        from_team_name = from_team.name if from_team else f"team {assignment.from_team_id}"
        to_team_name = to_team.name if to_team else f"team {assignment.to_team_id}"
        success_msg = f"Successfully removed ARO assignment for {args.employee} from {from_team_name} to {to_team_name} on {args.date}{period_str}"
        logger.info(
            success_msg, 
            event_type="aro_remove", 
            identifier="success"
        )
        print(success_msg)
        return True
    else:
        error_msg = f"Error: {result['message']}"
        logger.error(
            error_msg, 
            event_type="aro_remove", 
            identifier="failure",
            extra={"error_details": result.get("details", "")}
        )
        print(error_msg, file=sys.stderr)
        return False
