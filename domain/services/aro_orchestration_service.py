# domain/services/aro_orchestration_service.py
from typing import List, Dict, Optional, Any, Tuple, Callable
from datetime import date, datetime, timedelta
import logging
import random

from domain.contexts.employee_management.entities.employee import Employee
from domain.contexts.workstation_management.entities.workstation import Workstation
from domain.contexts.assignment.value_objects.work_assignment import WorkAssignment

# Logger for this module
logger = logging.getLogger(__name__)


class AROOrchestrationService:
    """
    Service that orchestrates ARO assignment when teams fail to generate schedules.
    
    This service maintains low coupling by:
    1. Using dependency injection for ARO services
    2. Providing clear interfaces for schedule generation retry
    3. Separating ARO identification from assignment logic
    """
    
    def __init__(self, aro_service=None, aro_roster_service=None):
        """
        Initialize the ARO orchestration service.
        
        Args:
            aro_service: Service for ARO identification and workstation mapping
            aro_roster_service: Service for ARO assignment processing
        """
        self.aro_service = aro_service
        self.aro_roster_service = aro_roster_service
    
    def orchestrate_schedule_with_aro_retry(
        self,
        schedule_generator: Callable,
        team_id: int,
        team_name: str,
        employees: List[Employee],
        workstations: List[Workstation],
        start_date: date,
        periods_per_day: int,
        call_ins: List[str] = None,
        offline: List[str] = None,
        force_complete: bool = False,
        prefetched_data: Optional[Dict] = None,
        max_retries: int = 1
    ) -> Tuple[List[WorkAssignment], Dict[str, Any]]:
        """
        Orchestrate schedule generation with ARO retry logic.
        
        This method:
        1. Attempts initial schedule generation
        2. If it fails, identifies available AROs
        3. Assigns AROs and retries schedule generation
        4. Returns the final result
        
        Args:
            schedule_generator: Function to call for schedule generation
            team_id: ID of the team
            team_name: Name of the team
            employees: List of employees available for scheduling
            workstations: List of workstations to be staffed
            start_date: Start date of the schedule
            periods_per_day: Number of periods per day
            call_ins: List of employee names who called in
            offline: List of offline employee specifications
            force_complete: Whether to force completion
            prefetched_data: Optional prefetched data
            max_retries: Maximum number of ARO retry attempts
            
        Returns:
            Tuple containing:
            - List of work assignments
            - Dictionary with schedule metadata
        """
        logger.info(f"Starting schedule orchestration for team {team_name} (ID: {team_id})")
        
        # Attempt initial schedule generation
        assignments, metadata = schedule_generator(
            employees=employees,
            workstations=workstations,
            start_date=start_date,
            periods_per_day=periods_per_day,
            team_name=team_name,
            team_id=team_id,
            call_ins=call_ins,
            offline=offline,
            force_complete=force_complete,
            prefetched_data=prefetched_data
        )
        
        # If initial generation succeeded, return results
        if assignments and metadata.get("status") == "completed":
            logger.info(f"Initial schedule generation succeeded for team {team_name}")
            return assignments, metadata
        
        # If no ARO services available, return original failure
        if not self.aro_service or not self.aro_roster_service:
            logger.warning(f"Schedule failed for team {team_name} and no ARO services available for retry")
            return assignments, metadata
        
        # Attempt ARO-assisted retry
        logger.info(f"Initial schedule generation failed for team {team_name}, attempting ARO retry")
        
        for retry_attempt in range(max_retries):
            logger.info(f"ARO retry attempt {retry_attempt + 1}/{max_retries} for team {team_name}")
            
            # Identify available AROs for this team
            # TODO: Enhance to handle multiple periods properly instead of defaulting to period=1
            available_aros = self._identify_available_aros(
                team_id=team_id,
                team_name=team_name,
                workstations=workstations,
                start_date=start_date,
                prefetched_data=prefetched_data,
                period=1  # Default to period 1, should be enhanced for multi-period support
            )
            
            if not available_aros:
                logger.warning(f"No available AROs found for team {team_name} on retry {retry_attempt + 1}")
                continue
            
            # Assign AROs and update employee list with workstation-specific pre-assignments
            enhanced_employees, aro_pre_assignments = self._assign_aros_and_update_employees(
                original_employees=employees,
                available_aros=available_aros,
                team_id=team_id,
                start_date=start_date,
                prefetched_data=prefetched_data,
                period=1  # Default to period 1, should be enhanced for multi-period support
            )
            
            if not enhanced_employees or len(enhanced_employees) == len(employees):
                logger.warning(f"ARO assignment did not add new employees for team {team_name} on retry {retry_attempt + 1}")
                continue
            
            logger.info(f"Added {len(enhanced_employees) - len(employees)} ARO employees for team {team_name}")
            if aro_pre_assignments:
                logger.info(f"Created {len(aro_pre_assignments)} workstation-specific ARO pre-assignments for team {team_name}")
            
            # Add pre-assignments to prefetched data for the CP model
            enhanced_prefetched_data = prefetched_data.copy() if prefetched_data else {}
            if aro_pre_assignments:
                enhanced_prefetched_data['aro_pre_assignments'] = aro_pre_assignments
            
            # Retry schedule generation with enhanced employee list and pre-assignments
            retry_assignments, retry_metadata = schedule_generator(
                employees=enhanced_employees,
                workstations=workstations,
                start_date=start_date,
                periods_per_day=periods_per_day,
                team_name=team_name,
                team_id=team_id,
                call_ins=call_ins,
                offline=offline,
                force_complete=force_complete,
                prefetched_data=enhanced_prefetched_data
            )
            
            # If retry succeeded, return results
            if retry_assignments and retry_metadata.get("status") == "completed":
                logger.info(f"ARO retry succeeded for team {team_name} on attempt {retry_attempt + 1}")
                # Update metadata to indicate ARO assistance
                retry_metadata["aro_assisted"] = True
                retry_metadata["aro_retry_attempt"] = retry_attempt + 1
                return retry_assignments, retry_metadata
            
            logger.warning(f"ARO retry {retry_attempt + 1} failed for team {team_name}")
        
        # All retries failed, return original failure with ARO attempt info
        logger.warning(f"All ARO retry attempts failed for team {team_name}")
        metadata["aro_retry_attempted"] = True
        metadata["aro_retry_count"] = max_retries
        return assignments, metadata
    
    def _identify_available_aros(
        self,
        team_id: int,
        team_name: str,
        workstations: List[Workstation],
        start_date: date,
        prefetched_data: Optional[Dict] = None,
        period: Optional[int] = None
    ) -> List[Employee]:
        """
        Identify available ARO employees for a team.
        
        Args:
            team_id: ID of the team needing AROs
            team_name: Name of the team needing AROs
            workstations: List of workstations that need staffing
            start_date: Date for the assignment
            prefetched_data: Optional prefetched data
            
        Returns:
            List of available ARO employees
        """
        if not self.aro_service:
            return []
        
        try:
            # Get workstation-to-ARO mapping
            aro_mapping = self.aro_service.get_workstation_aro_mapping(
                team_id=team_id,
                period=period,  # Use actual period instead of hardcoded 1
                assignment_date=start_date,
                empty_workstations=workstations
            )
            
            if not aro_mapping:
                logger.info(f"No ARO mapping found for team {team_name}")
                return []
            
            # Collect unique ARO employee IDs
            aro_employee_ids = set()
            for workstation_id, employee_ids in aro_mapping.items():
                aro_employee_ids.update(employee_ids)
            
            # Get employee objects from prefetched data or repository
            available_aros = []
            if prefetched_data and 'employees_by_id' in prefetched_data:
                employees_by_id = prefetched_data['employees_by_id']
                for emp_id in aro_employee_ids:
                    if emp_id in employees_by_id:
                        available_aros.append(employees_by_id[emp_id])
            
            logger.info(f"Identified {len(available_aros)} available ARO employees for team {team_name}")
            return available_aros
            
        except Exception as e:
            logger.error(f"Error identifying available AROs for team {team_name}: {str(e)}")
            return []
    
    def _assign_aros_and_update_employees(
        self,
        original_employees: List[Employee],
        available_aros: List[Employee],
        team_id: int,
        start_date: date,
        prefetched_data: Optional[Dict] = None,
        period: Optional[int] = None
    ) -> Tuple[List[Employee], Dict[int, int]]:
        """
        Assign AROs to specific workstations and return updated employee list with pre-assignments.
        
        This method implements the new approach where AROs are assigned to specific workstations
        rather than being added to the general employee pool.
        
        Args:
            original_employees: Original list of team employees
            available_aros: List of available ARO employees
            team_id: ID of the team needing AROs
            start_date: Date for the assignment
            prefetched_data: Optional prefetched data
            
        Returns:
            Tuple containing:
            - Updated list of employees including selected AROs
            - Dictionary mapping workstation indices to ARO employee indices (pre-assignments)
        """
        if not available_aros:
            return original_employees.copy(), {}
        
        # Get workstation-to-ARO mapping from ARO service
        if not self.aro_service:
            return original_employees.copy(), {}
        
        try:
            # Get all workstations for this team from prefetched data
            workstations = []
            if prefetched_data and 'workstations_by_team' in prefetched_data and team_id in prefetched_data['workstations_by_team']:
                workstations = prefetched_data['workstations_by_team'][team_id]
            
            if not workstations:
                logger.warning(f"No workstations found for team {team_id}, falling back to bulk assignment")
                return self._fallback_bulk_assignment(original_employees, available_aros, team_id)
            
            # Get workstation-to-ARO mapping
            aro_mapping = self.aro_service.get_workstation_aro_mapping(
                team_id=team_id,
                period=period,  # Use actual period instead of hardcoded 1
                assignment_date=start_date,
                empty_workstations=workstations
            )
            
            if not aro_mapping:
                logger.info(f"No ARO mapping found for team {team_id}, falling back to bulk assignment")
                return self._fallback_bulk_assignment(original_employees, available_aros, team_id)
            
            # Select best ARO candidate for each workstation
            enhanced_employees = original_employees.copy()
            aro_pre_assignments = {}  # workstation_index -> employee_index
            assigned_aro_ids = set()
            
            # Create employee lookup for available AROs
            aro_lookup = {aro.id: aro for aro in available_aros}
            
            for workstation_idx, workstation in enumerate(workstations):
                if workstation.id in aro_mapping:
                    qualified_aro_ids = aro_mapping[workstation.id]
                    
                    # Find the best ARO candidate for this workstation
                    best_aro = self._select_best_aro_for_workstation(
                        workstation, qualified_aro_ids, aro_lookup, assigned_aro_ids,
                        team_id=team_id, start_date=start_date
                    )
                    
                    if best_aro:
                        # Add ARO to employee list if not already present
                        aro_employee_idx = None
                        for idx, emp in enumerate(enhanced_employees):
                            if emp.id == best_aro.id:
                                aro_employee_idx = idx
                                break
                        
                        if aro_employee_idx is None:
                            enhanced_employees.append(best_aro)
                            aro_employee_idx = len(enhanced_employees) - 1
                        
                        # Create pre-assignment
                        aro_pre_assignments[workstation_idx] = aro_employee_idx
                        assigned_aro_ids.add(best_aro.id)
                        
                        logger.info(f"Pre-assigned ARO {best_aro.name} (ID: {best_aro.id}) to workstation {workstation.name} for team {team_id}")
            
            logger.info(f"Created {len(aro_pre_assignments)} workstation-specific ARO pre-assignments for team {team_id}")
            return enhanced_employees, aro_pre_assignments
            
        except Exception as e:
            logger.error(f"Error creating workstation-specific ARO assignments for team {team_id}: {str(e)}")
            return self._fallback_bulk_assignment(original_employees, available_aros, team_id)
    
    def _get_recent_aro_assignments(
        self,
        employee_id: int,
        team_id: int,
        workstation_id: int,
        assignment_date: date,
        lookback_days: int = 30
    ) -> int:
        """
        Get the count of recent ARO assignments for an employee to a specific team/workstation.
        
        Args:
            employee_id: ID of the ARO employee
            team_id: ID of the team
            workstation_id: ID of the workstation
            assignment_date: Current assignment date
            lookback_days: Number of days to look back for assignment history
            
        Returns:
            Number of recent assignments
        """
        if not self.aro_roster_service:
            return 0
        
        try:
            start_date = assignment_date - timedelta(days=lookback_days)
            
            # Check if aro_roster_service has a method to get assignment history
            if hasattr(self.aro_roster_service, 'get_recent_assignments'):
                return self.aro_roster_service.get_recent_assignments(
                    employee_id=employee_id,
                    team_id=team_id,
                    workstation_id=workstation_id,
                    start_date=start_date,
                    end_date=assignment_date
                )
            
            # Fallback: return 0 if no history tracking available
            return 0
            
        except Exception as e:
            logger.error(f"Error getting recent ARO assignments for employee {employee_id}: {str(e)}")
            return 0
    
    def _select_best_aro_for_workstation(
        self,
        workstation: Workstation,
        qualified_aro_ids: List[int],
        aro_lookup: Dict[int, Employee],
        assigned_aro_ids: set,
        team_id: int = None,
        start_date: date = None
    ) -> Optional[Employee]:
        """
        Select the best ARO candidate for a specific workstation with rotation logic.
        
        Args:
            workstation: The workstation that needs ARO coverage
            qualified_aro_ids: List of ARO employee IDs qualified for this workstation
            aro_lookup: Dictionary mapping ARO IDs to Employee objects
            assigned_aro_ids: Set of ARO IDs already assigned to other workstations
            team_id: ID of the team requesting ARO (for historical tracking)
            start_date: Assignment date (for historical tracking)
            
        Returns:
            Best ARO Employee for this workstation, or None if no suitable candidate
        """
        available_candidates = []
        
        for aro_id in qualified_aro_ids:
            if aro_id not in assigned_aro_ids and aro_id in aro_lookup:
                available_candidates.append(aro_lookup[aro_id])
        
        if not available_candidates:
            return None
        
        # Enhanced selection criteria with rotation logic
        def enhanced_selection_score(employee: Employee) -> Tuple[int, int, int, int]:
            # 1. Count qualifications specific to this workstation
            workstation_qualifications = 0
            if hasattr(employee, 'can_work') and employee.can_work(workstation):
                workstation_qualifications += 1
            if hasattr(employee, 'can_handle_workstation_type') and employee.can_handle_workstation_type(workstation):
                workstation_qualifications += 1
            
            # 2. Count total qualifications
            total_qualifications = len(getattr(employee, 'qualifications', []))
            
            # 3. Recent assignment frequency (lower is better for rotation)
            recent_assignments = self._get_recent_aro_assignments(
                employee.id, team_id, workstation.id, start_date
            ) if team_id and start_date else 0
            rotation_score = -recent_assignments  # Negative so less frequent assignments rank higher
            
            # 4. Random tie-breaker for equal candidates
            tie_breaker = random.randint(0, 1000)
            
            return (workstation_qualifications, total_qualifications, rotation_score, tie_breaker)
        
        # Sort by enhanced criteria (descending order)
        best_candidate = max(available_candidates, key=enhanced_selection_score)
        
        logger.debug(f"Selected ARO {best_candidate.name} for workstation {workstation.name} from {len(available_candidates)} candidates")
        return best_candidate
    
    def _fallback_bulk_assignment(
        self,
        original_employees: List[Employee],
        available_aros: List[Employee],
        team_id: int
    ) -> Tuple[List[Employee], Dict[int, int]]:
        """
        Fallback to the original bulk ARO assignment approach.
        
        Args:
            original_employees: Original list of team employees
            available_aros: List of available ARO employees
            team_id: ID of the team needing AROs
            
        Returns:
            Tuple containing updated employee list and empty pre-assignments dict
        """
        enhanced_employees = original_employees.copy()
        
        for aro_employee in available_aros:
            # Check if ARO is not already in the team
            if not any(emp.id == aro_employee.id for emp in enhanced_employees):
                enhanced_employees.append(aro_employee)
                logger.info(f"Added ARO employee {aro_employee.name} (ID: {aro_employee.id}) to team {team_id} (bulk assignment)")
        
        return enhanced_employees, {}