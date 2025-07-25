# domain/contexts/assignment/services/assignment_optimization_service.py
from typing import List, Optional, Dict, Any, Tuple
from datetime import date
import logging

from domain.contexts.assignment.entities.work_assignment import WorkAssignment
from domain.contexts.assignment.value_objects.assignment_criteria import AssignmentCriteria
from domain.contexts.assignment.value_objects.work_assignment_validator import WorkAssignmentValidator
from domain.contexts.assignment.repositories.interfaces.assignment_repository import AssignmentRepositoryInterface
from domain.contexts.employee_management.entities.employee import Employee
from domain.contexts.workstation_management.entities.workstation import Workstation
from domain.contexts.scheduling.value_objects.schedule_period import SchedulePeriod

logger = logging.getLogger(__name__)


class AssignmentOptimizationService:
    """
    Domain service responsible for optimizing employee-workstation assignments.
    
    This service encapsulates the business logic for creating optimal assignments
    based on various criteria including skills, workload balancing, and constraints.
    """
    
    def __init__(self, assignment_repository: AssignmentRepositoryInterface):
        """
        Initialize the assignment optimization service.
        
        Args:
            assignment_repository: Repository for assignment persistence
        """
        self.assignment_repository = assignment_repository
    
    def optimize_assignments(
        self,
        employees: List[Employee],
        workstations: List[Workstation],
        assignment_date: date,
        periods: List[int],
        criteria: Optional[AssignmentCriteria] = None
    ) -> List[WorkAssignment]:
        """
        Optimize assignments for a given set of employees and workstations.
        
        Args:
            employees: List of available employees
            workstations: List of workstations to be staffed
            assignment_date: Date for the assignments
            periods: List of periods to assign
            criteria: Optional criteria for optimization
            
        Returns:
            List of optimized work assignments
            
        Raises:
            ValueError: If invalid parameters are provided
        """
        logger.info(f"Starting assignment optimization for {len(employees)} employees and {len(workstations)} workstations")
        
        if not employees:
            raise ValueError("At least one employee must be provided")
        
        if not workstations:
            raise ValueError("At least one workstation must be provided")
        
        if not periods:
            raise ValueError("At least one period must be provided")
        
        # Use default criteria if none provided
        if criteria is None:
            criteria = AssignmentCriteria(assignment_date=assignment_date)
        
        assignments = []
        
        for period in periods:
            period_assignments = self._optimize_period_assignments(
                employees, workstations, assignment_date, period, criteria
            )
            assignments.extend(period_assignments)
        
        logger.info(f"Generated {len(assignments)} optimized assignments")
        return assignments
    
    def _optimize_period_assignments(
        self,
        employees: List[Employee],
        workstations: List[Workstation],
        assignment_date: date,
        period: int,
        criteria: AssignmentCriteria
    ) -> List[WorkAssignment]:
        """
        Optimize assignments for a specific period.
        
        Args:
            employees: List of available employees
            workstations: List of workstations to be staffed
            assignment_date: Date for the assignments
            period: Period number (1-5)
            criteria: Assignment criteria
            
        Returns:
            List of work assignments for the period
        """
        logger.debug(f"Optimizing assignments for period {period}")
        
        # Filter employees and workstations based on criteria
        available_employees = self._filter_available_employees(employees, assignment_date, period, criteria)
        eligible_workstations = self._filter_eligible_workstations(workstations, criteria)
        
        if not available_employees:
            logger.warning(f"No available employees for period {period}")
            return []
        
        if not eligible_workstations:
            logger.warning(f"No eligible workstations for period {period}")
            return []
        
        # Create assignment matrix and optimize
        assignment_matrix = self._create_assignment_matrix(
            available_employees, eligible_workstations, assignment_date, period, criteria
        )
        
        # Apply optimization algorithm
        optimal_assignments = self._apply_optimization_algorithm(
            assignment_matrix, available_employees, eligible_workstations, assignment_date, period
        )
        
        return optimal_assignments
    
    def _filter_available_employees(
        self,
        employees: List[Employee],
        assignment_date: date,
        period: int,
        criteria: AssignmentCriteria
    ) -> List[Employee]:
        """Filter employees based on availability and criteria."""
        available = []
        
        for employee in employees:
            # Check basic availability
            if not employee.is_available_for_period(assignment_date, period):
                continue
            
            # Check period constraints
            if not criteria.is_period_allowed(period):
                continue
            
            # Check preferred/excluded team members
            if criteria.avoid_team_members and employee.id in criteria.avoid_team_members:
                continue
            
            # Add more filtering logic as needed
            available.append(employee)
        
        return available
    
    def _filter_eligible_workstations(
        self,
        workstations: List[Workstation],
        criteria: AssignmentCriteria
    ) -> List[Workstation]:
        """Filter workstations based on criteria."""
        eligible = []
        
        for workstation in workstations:
            # Check workstation constraints
            if not criteria.is_workstation_allowed(workstation.id):
                continue
            
            # Add more filtering logic as needed
            eligible.append(workstation)
        
        return eligible
    
    def _create_assignment_matrix(
        self,
        employees: List[Employee],
        workstations: List[Workstation],
        assignment_date: date,
        period: int,
        criteria: AssignmentCriteria
    ) -> Dict[Tuple[int, int], float]:
        """
        Create a matrix of assignment scores for employee-workstation pairs.
        
        Returns:
            Dictionary mapping (employee_id, workstation_id) to optimization score
        """
        matrix = {}
        
        for employee in employees:
            for workstation in workstations:
                score = self._calculate_assignment_score(
                    employee, workstation, assignment_date, period, criteria
                )
                matrix[(employee.id, workstation.id)] = score
        
        return matrix
    
    def _calculate_assignment_score(
        self,
        employee: Employee,
        workstation: Workstation,
        assignment_date: date,
        period: int,
        criteria: AssignmentCriteria
    ) -> float:
        """
        Calculate optimization score for an employee-workstation assignment.
        
        Returns:
            Float score (higher is better)
        """
        score = 0.0
        
        # Check if employee can work the workstation
        if not employee.can_work(workstation):
            return -1.0  # Invalid assignment
        
        # Skill level matching
        # (This would need to be implemented based on your skill system)
        score += 1.0  # Base score
        
        # Apply criteria weights
        score *= criteria.get_optimization_score()
        
        # Add more scoring logic based on your business rules
        
        return score
    
    def _apply_optimization_algorithm(
        self,
        assignment_matrix: Dict[Tuple[int, int], float],
        employees: List[Employee],
        workstations: List[Workstation],
        assignment_date: date,
        period: int
    ) -> List[WorkAssignment]:
        """
        Apply optimization algorithm to create assignments.
        
        This is a simplified greedy algorithm. In practice, you might want to use
        more sophisticated algorithms like Hungarian algorithm or genetic algorithms.
        """
        assignments = []
        assigned_employees = set()
        assigned_workstations = set()
        
        # Sort assignments by score (highest first)
        sorted_assignments = sorted(
            assignment_matrix.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for (employee_id, workstation_id), score in sorted_assignments:
            # Skip if already assigned or invalid score
            if employee_id in assigned_employees or workstation_id in assigned_workstations:
                continue
            
            if score < 0:
                continue
            
            # Find employee and workstation objects
            employee = next((e for e in employees if e.id == employee_id), None)
            workstation = next((w for w in workstations if w.id == workstation_id), None)
            
            if employee and workstation:
                # Create assignment
                schedule_period = SchedulePeriod(date=assignment_date, period=period)
                assignment = WorkAssignment(
                    employee=employee,
                    workstation=workstation,
                    period=schedule_period
                )
                
                # Validate assignment
                is_valid, error_msg = WorkAssignmentValidator.validate(assignment)
                if is_valid:
                    assignments.append(assignment)
                    assigned_employees.add(employee_id)
                    assigned_workstations.add(workstation_id)
                else:
                    logger.warning(f"Invalid assignment: {error_msg}")
        
        return assignments
    
    def validate_assignments(self, assignments: List[WorkAssignment]) -> Dict[str, Any]:
        """
        Validate a list of assignments.
        
        Args:
            assignments: List of work assignments to validate
            
        Returns:
            Dictionary containing validation results
        """
        logger.debug(f"Validating {len(assignments)} assignments")
        
        validation_results = {
            "is_valid": True,
            "valid_count": 0,
            "invalid_assignments": [],
            "warnings": []
        }
        
        # Validate each assignment
        invalid_assignments = WorkAssignmentValidator.validate_batch(assignments)
        
        validation_results["valid_count"] = len(assignments) - len(invalid_assignments)
        validation_results["invalid_assignments"] = invalid_assignments
        
        if invalid_assignments:
            validation_results["is_valid"] = False
        
        # Check for conflicts (same employee assigned to multiple workstations in same period)
        conflicts = self._check_assignment_conflicts(assignments)
        if conflicts:
            validation_results["warnings"].extend(conflicts)
        
        return validation_results
    
    def _check_assignment_conflicts(self, assignments: List[WorkAssignment]) -> List[str]:
        """Check for assignment conflicts."""
        conflicts = []
        assignment_map = {}
        
        for assignment in assignments:
            key = (assignment.employee.id, assignment.period.date, assignment.period.period)
            if key in assignment_map:
                conflicts.append(
                    f"Employee {assignment.employee.id} assigned to multiple workstations "
                    f"on {assignment.period.date} period {assignment.period.period}"
                )
            else:
                assignment_map[key] = assignment
        
        return conflicts


class AssignmentOptimizationError(Exception):
    """Exception raised when assignment optimization fails."""
    pass