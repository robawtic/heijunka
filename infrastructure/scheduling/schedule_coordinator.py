from typing import Dict, List, Set, Any, Optional, Tuple
from datetime import date
import logging
from sqlalchemy.orm import Session

from domain.events.publisher import DomainEventPublisher
from domain.events import AROTransferRequested, ScheduleGenerationCompleted, ScheduleRegenerationNeeded
from application.commands.generate_schedule_command import GenerateScheduleCommand
from application.commands.generate_schedule_handler import GenerateScheduleHandler
from domain.value_objects.work_assignment import WorkAssignment
from utilities.logging_factory import get_logger

# Create a logger for this module
logger = get_logger("infrastructure.scheduling.schedule_coordinator", rate_limit=True)

class ScheduleCoordinator:
    """
    Coordinates the generation of schedules across multiple teams.

    This class manages the generation of individual schedules and handles
    the coordination between them using an observer pattern.
    """

    def __init__(
        self,
        schedule_handler: GenerateScheduleHandler,
        schedule_data_service,
        event_publisher: DomainEventPublisher
    ):
        self.schedule_handler = schedule_handler
        self.schedule_data_service = schedule_data_service
        self.event_publisher = event_publisher
        self.active_schedules = {}  # team_id -> schedule info
        self.influenced_teams = set()  # Set of team IDs that need regeneration

        # Register event handlers
        self.event_publisher.register("AROTransferRequested", self._handle_aro_transfer)
        self.event_publisher.register("ScheduleGenerationCompleted", self._handle_schedule_completed)

    def generate_schedule(self, command: GenerateScheduleCommand) -> List[WorkAssignment]:
        """
        Generate a schedule for a single team.

        Args:
            command: The command containing schedule generation parameters

        Returns:
            List of generated work assignments
        """
        team_id = command.team_id

        # Register this schedule as active
        self.active_schedules[team_id] = {
            "command": command,
            "status": "generating",
            "assignments": []
        }

        # Generate the schedule
        try:
            # Prefetch data for just this team
            prefetched_data = self.schedule_data_service.prefetch_for_teams(
                team_ids=[team_id],
                start_date=command.start_date,
                periods=command.periods_per_day
            )

            # Process availability
            available_by_team_and_period = self.schedule_data_service.process_availability(
                team_ids=[team_id],
                prefetched_data=prefetched_data,
                call_ins=command.call_ins,
                periods=command.periods_per_day
            )

            all_assignments = []

            # Generate schedule for each period
            for period in range(1, command.periods_per_day + 1):
                # Extract team data for this period
                team_data = self.schedule_data_service.extract_team_data(
                    prefetched_data=prefetched_data,
                    team_id=team_id,
                    period=period,
                    available_by_team_and_period=available_by_team_and_period
                )

                # Generate assignments for this period
                period_assignments = self.schedule_handler.generate_with_prefetched_data(
                    command=command,
                    employees=team_data['employees'],
                    workstations=team_data['workstations'],
                    prefetched_data=prefetched_data
                )

                all_assignments.extend(period_assignments)

            # Update active schedule info
            self.active_schedules[team_id]["status"] = "completed"
            self.active_schedules[team_id]["assignments"] = all_assignments

            # Publish completion event
            self.event_publisher.publish(ScheduleGenerationCompleted(
                team_id=team_id,
                start_date=command.start_date,
                periods_per_day=command.periods_per_day,
                assignment_count=len(all_assignments)
            ))

            return all_assignments

        except Exception as e:
            logger.error(
                f"Error generating schedule for team {team_id}: {str(e)}",
                event_type="schedule_generation",
                identifier=f"team_{team_id}_error"
            )
            self.active_schedules[team_id]["status"] = "failed"
            self.active_schedules[team_id]["error"] = str(e)
            return []

    def generate_schedules(self, commands: List[GenerateScheduleCommand]) -> Dict[int, List[WorkAssignment]]:
        """
        Generate schedules for multiple teams.

        Args:
            commands: List of commands for each team

        Returns:
            Dictionary mapping team_id to list of assignments
        """
        all_assignments = {}

        # First pass: Generate initial schedules for all teams
        for command in commands:
            assignments = self.generate_schedule(command)
            all_assignments[command.team_id] = assignments

        # Second pass: Regenerate schedules for influenced teams
        while self.influenced_teams:
            team_id = self.influenced_teams.pop()
            if team_id in self.active_schedules:
                command = self.active_schedules[team_id]["command"]
                assignments = self.generate_schedule(command)
                all_assignments[command.team_id] = assignments

        return all_assignments

    def _handle_aro_transfer(self, event: AROTransferRequested) -> None:
        """Handle ARO transfer requests between teams."""
        # Mark both source and destination teams as influenced
        self.influenced_teams.add(event.from_team_id)
        self.influenced_teams.add(event.to_team_id)

        logger.info(
            f"ARO transfer requested: Employee {event.employee_id} from team {event.from_team_id} to team {event.to_team_id}",
            event_type="aro_transfer",
            identifier=f"emp_{event.employee_id}_period_{event.period}"
        )

    def _handle_schedule_completed(self, event: ScheduleGenerationCompleted) -> None:
        """Handle schedule generation completion events."""
        logger.info(
            f"Schedule generation completed for team {event.team_id}: {event.assignment_count} assignments",
            event_type="schedule_completed",
            identifier=f"team_{event.team_id}"
        )

    def generate_period_schedules(self, teams: List[Any], period: int, 
                                 available_by_team_and_period: Dict,
                                 prefetched_data: Dict) -> List[WorkAssignment]:
        """Generate schedules for all teams for a specific period.

        Args:
            teams: List of teams to generate schedules for
            period: The period to generate schedules for
            available_by_team_and_period: Dictionary mapping team IDs to dictionaries of available employees by period
            prefetched_data: Dictionary containing prefetched data to avoid database queries

        Returns:
            List of work assignments for all teams for the specified period
        """
        all_assignments = []

        # Process each team for this period
        for team in teams:
            team_id = team.id

            # Skip if no available employees for this team and period
            if team_id not in available_by_team_and_period or period not in available_by_team_and_period[team_id]:
                logger.info(
                    f"No available employees for team {team_id} in period {period}, skipping",
                    event_type="period_schedule_generation",
                    identifier=f"team_{team_id}_period_{period}"
                )
                continue

            # Extract team data for this period
            team_data = self.schedule_data_service.extract_team_data(
                prefetched_data=prefetched_data,
                team_id=team_id,
                period=period,
                available_by_team_and_period=available_by_team_and_period
            )

            # Skip if no employees or workstations
            if not team_data['employees'] or not team_data['workstations']:
                logger.info(
                    f"No employees or workstations for team {team_id} in period {period}, skipping",
                    event_type="period_schedule_generation",
                    identifier=f"team_{team_id}_period_{period}"
                )
                continue

            # Create a command for this team
            # We need to get the command from active_schedules if it exists, or create a new one
            command = None
            if team_id in self.active_schedules and "command" in self.active_schedules[team_id]:
                command = self.active_schedules[team_id]["command"]
            else:
                # Create a new command with default values
                from application.commands.generate_schedule_command import GenerateScheduleCommand
                command = GenerateScheduleCommand(
                    team_id=team_id,
                    start_date=prefetched_data.get('schedule_date', date.today()),
                    periods_per_day=prefetched_data.get('periods_per_day', 1),
                    call_ins=[],
                    offline=[],
                    force_complete=False
                )

            try:
                # Generate assignments for this team and period
                period_assignments = self.schedule_handler.generate_with_prefetched_data(
                    command=command,
                    employees=team_data['employees'],
                    workstations=team_data['workstations'],
                    prefetched_data=prefetched_data
                )

                # Add assignments to the result
                all_assignments.extend(period_assignments)

                logger.info(
                    f"Generated {len(period_assignments)} assignments for team {team_id} in period {period}",
                    event_type="period_schedule_generation",
                    identifier=f"team_{team_id}_period_{period}"
                )

            except Exception as e:
                logger.error(
                    f"Error generating schedule for team {team_id} in period {period}: {str(e)}",
                    event_type="period_schedule_generation",
                    identifier=f"team_{team_id}_period_{period}_error"
                )

        return all_assignments
