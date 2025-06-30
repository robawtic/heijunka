# presentation/cli/cli.py
"""
Main entry point for the CLI application.
"""
import sys
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import event
from sqlalchemy.engine import Engine
import colorama

# Initialize colorama to handle ANSI color codes in Windows
colorama.init()

from presentation.cli.utils.argument_parser import parse_arguments
from presentation.cli.utils.dependencies import setup_dependencies
from presentation.cli.commands.generate_command import handle_generate
from presentation.cli.commands.manual_assignment_command import handle_manual_assignment
from presentation.cli.commands.simulation_command import handle_simulation
from presentation.cli.commands.regression_command import handle_regression_test
from presentation.cli.commands.aro_command import handle_aro_assignment
from utilities.logging_factory import get_logger

# Create a logger for this module
logger = get_logger("presentation.cli", rate_limit=True)

# Global counter for queries
query_count = 0

@event.listens_for(Engine, "before_cursor_execute")
def count_queries(conn, cursor, statement, parameters, context, executemany):
    """Event listener that counts SQL queries."""
    global query_count
    query_count += 1


def main():
    """Main entry point for the CLI application."""
    logger.info("Starting CLI application", event_type="application", identifier="startup")
    try:
        # Parse arguments
        args = parse_arguments()
        logger.debug(f"Parsed arguments: {args}", event_type="arguments", identifier="parse")

        # Setup dependencies
        dependencies = setup_dependencies()
        session_factory = dependencies[0]  # Extract session factory from dependencies tuple
        session = session_factory()  # Create a session from the factory

        try:
            # Execute the appropriate command
            if args.command == 'generate':
                handle_generate(args, dependencies, query_count)
            elif args.command == 'assign':
                handle_manual_assignment(args, session_factory)
            elif args.command == 'simulate':
                handle_simulation(args, session_factory)
            elif args.command == 'regression-test':
                handle_regression_test(args, session_factory)
            elif args.command == 'aro':
                if not hasattr(args, 'aro_command') or not args.aro_command:
                    print("Error: No ARO command specified. Use 'aro assign', 'aro remove', or 'aro optimize'.", file=sys.stderr)
                    sys.exit(1)
                handle_aro_assignment(args, session_factory, dependencies[8], dependencies[9])  # Pass aro_service and aro_graph_service
            else:
                print("Error: No command specified. Use 'generate', 'assign', 'simulate', 'regression-test', or 'aro'.", file=sys.stderr)
                sys.exit(1)

        except Exception as e:
            error_msg = f"Error executing command: {e}"
            logger.error(error_msg, event_type="command_execution", identifier=str(args.command))
            print(error_msg, file=sys.stderr)
            sys.exit(1)
        finally:
            session.close()

    except SQLAlchemyError as e:
        error_msg = f"Database error: {e}"
        logger.error(error_msg, event_type="database_error", identifier="sqlalchemy")
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        logger.error(error_msg, event_type="unexpected_error", identifier="main")
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    finally:
        logger.info("CLI application finished", event_type="application", identifier="shutdown")


if __name__ == '__main__':
    main()
