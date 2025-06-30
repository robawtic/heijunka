"""
Manual assignment command handling for the CLI application.
"""
import sys
from typing import Optional, Any, cast
from datetime import datetime
from sqlalchemy.orm import Session

from application.commands.create_manual_assignment_command import CreateManualAssignmentCommand
from application.commands.create_manual_assignment_handler import CreateManualAssignmentHandler
from domain.repositories.implementations.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from domain.repositories.implementations.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from domain.repositories.implementations.sqlalchemy_assignment_repository import SqlAlchemyAssignmentRepository
from utilities.logging_factory import get_logger, RateLimitedLogger

# Create a logger for this module
logger = cast(RateLimitedLogger, get_logger("presentation.cli.commands.manual_assignment_command", rate_limit=True))

def handle_manual_assignment(args: Any, session_factory: Any) -> bool:
    """
    Handle the manual assignment command.

    Args:
        args: Command line arguments
        session_factory: Database session factory

    Returns:
        bool: True if the operation was successful, False otherwise
    """
    logger.info(
        f"Handling manual assignment: {args.employee} to {args.workstation} on {args.date} for period {args.period}",
        event_type="manual_assignment", 
        identifier="start"
    )
    
    try:
        # Setup repositories
        logger.debug(
            "Setting up repositories for manual assignment", 
            event_type="manual_assignment", 
            identifier="setup"
        )
        
        employee_repository = SqlAlchemyEmployeeRepository(session_factory)
        workstation_repository = SqlAlchemyWorkstationRepository(session_factory)
        assignment_repository = SqlAlchemyAssignmentRepository(session_factory)

        # Get employee by name
        logger.debug(
            f"Looking up employee: {args.employee}", 
            event_type="manual_assignment", 
            identifier="employee_lookup"
        )
        
        employee = employee_repository.get_by_name(args.employee)
        if not employee:
            error_msg = f"Error: Employee '{args.employee}' not found"
            logger.error(
                error_msg, 
                event_type="manual_assignment", 
                identifier="employee_lookup"
            )
            print(error_msg, file=sys.stderr)
            return False

        # Get workstation by name
        logger.debug(
            f"Looking up workstation: {args.workstation}", 
            event_type="manual_assignment", 
            identifier="workstation_lookup"
        )
        
        workstation = workstation_repository.get_by_name(args.workstation)
        if not workstation:
            error_msg = f"Error: Workstation '{args.workstation}' not found"
            logger.error(
                error_msg, 
                event_type="manual_assignment", 
                identifier="workstation_lookup"
            )
            print(error_msg, file=sys.stderr)
            return False

        # Parse date
        logger.debug(
            f"Parsing date: {args.date}", 
            event_type="manual_assignment", 
            identifier="date_parsing"
        )
        
        try:
            assignment_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            error_msg = f"Error: Invalid date format. Use YYYY-MM-DD"
            logger.error(
                error_msg, 
                event_type="manual_assignment", 
                identifier="date_parsing"
            )
            print(error_msg, file=sys.stderr)
            return False

        # Validate period
        logger.debug(
            f"Validating period: {args.period}", 
            event_type="manual_assignment", 
            identifier="period_validation"
        )
        
        if args.period < 1 or args.period > 4:
            error_msg = f"Error: Period must be between 1 and 4"
            logger.error(
                error_msg, 
                event_type="manual_assignment", 
                identifier="period_validation"
            )
            print(error_msg, file=sys.stderr)
            return False

        # Create command handler
        logger.debug(
            "Creating command handler", 
            event_type="manual_assignment", 
            identifier="handler_creation"
        )
        
        handler = CreateManualAssignmentHandler(assignment_repository)

        # Create command
        logger.debug(
            "Creating command", 
            event_type="manual_assignment", 
            identifier="command_creation"
        )
        
        command = CreateManualAssignmentCommand(
            employee_id=employee.id,
            workstation_id=workstation.id,
            assignment_date=assignment_date,
            period=args.period,
            schedule_id=args.schedule_id
        )

        # Handle command
        logger.debug(
            "Executing command", 
            event_type="manual_assignment", 
            identifier="command_execution"
        )
        
        success = handler.handle(command)

        if success:
            success_msg = f"Successfully assigned {args.employee} to {args.workstation} on {args.date} for period {args.period}"
            logger.info(
                success_msg, 
                event_type="manual_assignment", 
                identifier="success",
                extra={
                    "employee_id": employee.id, 
                    "workstation_id": workstation.id, 
                    "date": str(assignment_date), 
                    "period": args.period
                }
            )
            print(success_msg)
            return True
        else:
            error_msg = "Failed to create assignment"
            logger.error(
                error_msg, 
                event_type="manual_assignment", 
                identifier="failure"
            )
            print(error_msg, file=sys.stderr)
            return False

    except Exception as e:
        error_msg = f"Error creating manual assignment: {e}"
        logger.error(
            error_msg, 
            event_type="manual_assignment", 
            identifier="exception", 
            extra={"exception": str(e)}
        )
        print(error_msg, file=sys.stderr)
        return False