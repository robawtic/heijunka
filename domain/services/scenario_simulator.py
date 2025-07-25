# domain/services/scenario_simulator.py
from typing import List, Dict, Any, Optional
from datetime import date

from domain.contexts.shared.value_objects.scenario import Scenario
from domain.contexts.assignment.value_objects.work_assignment import WorkAssignment
from domain.services.schedule_service import ScheduleService
from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from domain.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface
from domain.repositories.interfaces.team_repository import TeamRepositoryInterface
from domain.repositories.interfaces.schedule_repository_interface import ScheduleRepositoryInterface

import logging

logger = logging.getLogger(__name__)

class ScenarioSimulator:
    """Service for running multiple scheduling scenarios and collecting results."""

    def __init__(
        self,
        employee_repository: EmployeeRepositoryInterface,
        workstation_repository: WorkstationRepositoryInterface,
        team_repository: TeamRepositoryInterface,
        schedule_service: ScheduleService,
        schedule_repository: Optional[ScheduleRepositoryInterface] = None,
        session_factory=None
    ):
        self.employee_repository = employee_repository
        self.workstation_repository = workstation_repository
        self.team_repository = team_repository
        self.schedule_service = schedule_service
        self.schedule_repository = schedule_repository
        self.session_factory = session_factory
        self.results = {}  # Store scenario results

    def run_scenario(self, scenario: Scenario) -> Dict[str, Any]:
        """Run a single scenario and return the results."""
        logger.info(f"Running scenario: {scenario}")

        # Get team by ID
        team = self.team_repository.get(scenario.team_id)
        if not team:
            error_msg = f"Team with ID {scenario.team_id} not found"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Get employees and workstations for this team
        employees = self.employee_repository.get_by_team_id(scenario.team_id)
        workstations = self.workstation_repository.get_by_team_id(scenario.team_id)

        logger.debug(f"Found {len(employees)} employees and {len(workstations)} workstations for team {team.name}")

        # Generate schedule
        # Create a new session if a session factory is provided
        session = self.session_factory() if self.session_factory else None

        try:
            assignments = self.schedule_service.generate_schedule(
                employees=employees,
                workstations=workstations,
                start_date=scenario.start_date,
                periods_per_day=scenario.periods_per_day,
                team_name=team.name,
                call_ins=scenario.call_ins,
                offline=scenario.offline,
                force_complete=scenario.force_complete,
                session=session,
                team_repository=self.team_repository,
                schedule_repository=self.schedule_repository
            )

            # Commit the session if it was created here
            if session:
                session.commit()
        finally:
            # Close the session if it was created here
            if session:
                session.close()

        # Calculate metrics
        metrics = self._calculate_metrics(assignments, employees, workstations)

        # Store results
        result = {
            'scenario': scenario,
            'assignments': assignments,
            'metrics': metrics
        }

        self.results[scenario.name] = result
        logger.info(f"Completed scenario '{scenario.name}' with {len(assignments)} assignments")

        return result

    def run_scenarios(self, scenarios: List[Scenario]) -> Dict[str, Dict[str, Any]]:
        """Run multiple scenarios and return all results."""
        logger.info(f"Running {len(scenarios)} scenarios")

        for scenario in scenarios:
            try:
                self.run_scenario(scenario)
            except Exception as e:
                logger.error(f"Error running scenario '{scenario.name}': {str(e)}")
                # Continue with next scenario

        return self.results

    def _calculate_metrics(self, assignments: List[WorkAssignment], employees, workstations) -> Dict[str, Any]:
        """Calculate metrics for the generated schedule."""
        # Basic metrics
        metrics = {
            'total_assignments': len(assignments),
            'assignments_per_employee': {},
            'assignments_per_workstation': {},
            'assignments_per_period': {},
        }

        # Count assignments per employee
        for employee in employees:
            metrics['assignments_per_employee'][employee.name] = sum(
                1 for a in assignments if a.employee.id == employee.id
            )

        # Count assignments per workstation
        for workstation in workstations:
            metrics['assignments_per_workstation'][workstation.name] = sum(
                1 for a in assignments if a.workstation.id == workstation.id
            )

        # Count assignments per period
        for assignment in assignments:
            period_key = f"{assignment.period.date}_{assignment.period.period}"
            if period_key not in metrics['assignments_per_period']:
                metrics['assignments_per_period'][period_key] = 0
            metrics['assignments_per_period'][period_key] += 1

        # Calculate additional metrics if there are assignments
        if assignments:
            # Employee workload balance
            employee_assignments = list(metrics['assignments_per_employee'].values())
            if employee_assignments:
                metrics['min_employee_assignments'] = min(employee_assignments)
                metrics['max_employee_assignments'] = max(employee_assignments)
                metrics['avg_employee_assignments'] = sum(employee_assignments) / len(employee_assignments)

                # Calculate standard deviation for employee assignments
                import math
                mean = metrics['avg_employee_assignments']
                variance = sum((x - mean) ** 2 for x in employee_assignments) / len(employee_assignments)
                metrics['std_dev_employee_assignments'] = math.sqrt(variance)

            # Workstation utilization
            workstation_assignments = list(metrics['assignments_per_workstation'].values())
            if workstation_assignments:
                metrics['min_workstation_utilization'] = min(workstation_assignments)
                metrics['max_workstation_utilization'] = max(workstation_assignments)
                metrics['avg_workstation_utilization'] = sum(workstation_assignments) / len(workstation_assignments)

        return metrics
