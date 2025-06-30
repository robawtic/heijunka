# domain/value_objects/work_assignment_validator.py
from typing import List, Optional, Tuple
from domain.value_objects.work_assignment import WorkAssignment

class WorkAssignmentValidator:
    """
    Validator for WorkAssignment value objects.
    
    This class provides methods to validate WorkAssignment objects
    before they are persisted to the database. It ensures that all
    required fields are present and valid.
    """
    
    @staticmethod
    def validate(assignment: WorkAssignment) -> Tuple[bool, Optional[str]]:
        """
        Validate a work assignment.
        
        Args:
            assignment: The work assignment to validate
            
        Returns:
            A tuple of (is_valid, error_message). If the assignment is valid,
            returns (True, None). If invalid, returns (False, error_message).
        """
        # Check if employee is valid
        if not assignment.employee:
            return False, "Employee is missing"
        if not hasattr(assignment.employee, 'id') or not assignment.employee.id:
            return False, "Employee ID is missing or invalid"
        
        # Check if workstation is valid
        if not assignment.workstation:
            return False, "Workstation is missing"
        if not hasattr(assignment.workstation, 'id') or not assignment.workstation.id:
            return False, "Workstation ID is missing or invalid"
        
        # Check if period is valid
        if not assignment.period:
            return False, "Schedule period is missing"
        if not hasattr(assignment.period, 'date') or not assignment.period.date:
            return False, "Schedule date is missing or invalid"
        
        # SchedulePeriod already validates that period is between 1 and 5
        # in its __post_init__ method, so we don't need to check that here
        
        return True, None
    
    @staticmethod
    def validate_batch(assignments: List[WorkAssignment]) -> List[Tuple[WorkAssignment, str]]:
        """
        Validate a batch of work assignments.
        
        Args:
            assignments: The list of work assignments to validate
            
        Returns:
            A list of tuples containing invalid assignments and their error messages.
            If all assignments are valid, returns an empty list.
        """
        invalid_assignments = []
        
        for assignment in assignments:
            is_valid, error_msg = WorkAssignmentValidator.validate(assignment)
            if not is_valid:
                invalid_assignments.append((assignment, error_msg))
                
        return invalid_assignments