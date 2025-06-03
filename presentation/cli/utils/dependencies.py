"""
Dependency setup utilities for the CLI application.
"""
from typing import Tuple, Any, Optional
from sqlalchemy.orm import Session

from domain.models.db import Session as DbSession
from domain.repositories.implementations.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from domain.repositories.implementations.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from domain.repositories.implementations.sqlalchemy_team_repository import SqlAlchemyTeamRepository
from domain.repositories.implementations.sqlalchemy_assignment_repository import SqlAlchemyAssignmentRepository
from domain.repositories.implementations.sqlalchemy_employee_work_history_repository import SqlAlchemyEmployeeWorkHistoryRepository
from domain.repositories.implementations.sqlalchemy_schedule_repository import SqlAlchemyScheduleRepository
from domain.services.schedule_service import ScheduleService
from utilities.logging_factory import get_logger

# Create a logger for this module
logger = get_logger("presentation.cli.utils.dependencies", rate_limit=True)

def setup_dependencies() -> Tuple[
    Session,  # session
    SqlAlchemyEmployeeRepository,  # employee_repository
    SqlAlchemyWorkstationRepository,  # workstation_repository
    SqlAlchemyTeamRepository,  # team_repository
    ScheduleService,  # schedule_service
    SqlAlchemyAssignmentRepository,  # assignment_repository
    SqlAlchemyEmployeeWorkHistoryRepository,  # work_history_repository
    Any,  # aro_repository
    Any,  # aro_service
    Any,  # aro_graph_service
    SqlAlchemyScheduleRepository  # schedule_repository
]:
    """
    Set up and return the dependencies needed for the application.

    Returns:
        tuple: A tuple containing:
            - session: Database session
            - employee_repository: Repository for employee data
            - workstation_repository: Repository for workstation data
            - team_repository: Repository for team data
            - schedule_service: Service for schedule operations
            - assignment_repository: Repository for assignment data
            - work_history_repository: Repository for work history data
            - aro_repository: Repository for ARO assignments
            - aro_service: Service for ARO operations
            - aro_graph_service: Service for ARO graph operations
            - schedule_repository: Repository for schedule data
    """
    logger.debug("Setting up dependencies", event_type="dependencies", identifier="setup_start")
    
    session = DbSession()
    employee_repository = SqlAlchemyEmployeeRepository(session)
    workstation_repository = SqlAlchemyWorkstationRepository(session)
    team_repository = SqlAlchemyTeamRepository(session)
    schedule_service = ScheduleService()
    assignment_repository = SqlAlchemyAssignmentRepository(session)
    work_history_repository = SqlAlchemyEmployeeWorkHistoryRepository(session)
    schedule_repository = SqlAlchemyScheduleRepository(session)

    # Import here to avoid circular imports
    from domain.repositories.implementations.sqlalchemy_aro_assignment_repository import SqlAlchemyAROAssignmentRepository
    aro_repository = SqlAlchemyAROAssignmentRepository(session)

    # Create and register the schedule recalculation handler
    from domain.services.aro_service import AROService
    from domain.services.schedule_recalculation_handler import ScheduleRecalculationHandler
    from domain.contexts.assignment.services.aro_graph_service import AROGraphService
    from domain.services.cache_invalidation_handler import CacheInvalidationHandler

    aro_service = AROService(aro_repository, employee_repository, team_repository)
    schedule_recalculation_handler = ScheduleRecalculationHandler(
        team_repository, 
        employee_repository, 
        workstation_repository, 
        schedule_service
    )

    # Create the ARO graph service
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

    # Create the cache invalidation handler
    cache_invalidation_handler = CacheInvalidationHandler(aro_graph_service)

    # Register event handlers for schedule recalculation
    aro_service.register_event_handler('aro_assignment_created', schedule_recalculation_handler.handle_aro_assignment_created)
    aro_service.register_event_handler('aro_assignment_removed', schedule_recalculation_handler.handle_aro_assignment_removed)
    aro_service.register_event_handler('aro_assignment_updated', schedule_recalculation_handler.handle_aro_assignment_updated)

    # Register event handlers for cache invalidation
    aro_service.register_event_handler('aro_assignment_created', cache_invalidation_handler.handle_aro_assignment_created)
    aro_service.register_event_handler('aro_assignment_removed', cache_invalidation_handler.handle_aro_assignment_removed)
    aro_service.register_event_handler('aro_assignment_updated', cache_invalidation_handler.handle_aro_assignment_updated)

    logger.debug("Dependencies setup complete", event_type="dependencies", identifier="setup_complete")
    
    return (
        session, 
        employee_repository, 
        workstation_repository, 
        team_repository, 
        schedule_service, 
        assignment_repository, 
        work_history_repository, 
        aro_repository, 
        aro_service, 
        aro_graph_service, 
        schedule_repository
    )