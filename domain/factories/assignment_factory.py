# domain/factories/assignment_factory.py
from typing import Optional
from datetime import date
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.value_objects.schedule_period import SchedulePeriod
from domain.value_objects.work_assignment import WorkAssignment

class AssignmentFactory:
    @staticmethod
    def create_assignment(
        employee: Employee,
        workstation: Workstation,
        period: SchedulePeriod
    ) -> WorkAssignment:
        """
        Create a new WorkAssignment value object with validation.
        
        Args:
            employee: The employee to assign
            workstation: The workstation to assign the employee to
            period: The period for the assignment
            
        Returns:
            A new WorkAssignment value object
            
        Raises:
            ValueError: If the assignment is invalid
        """
        # Validate employee can work at this workstation
        if not employee.can_work(workstation):
            raise ValueError(f"{employee.name} cannot work at {workstation.name}")

        # Validate employee is available for this period
        if not employee.is_available_for_period(period.date, period.period):
            raise ValueError(f"{employee.name} is not available on {period}")
            
        # Create the assignment
        return WorkAssignment(
            employee=employee,
            workstation=workstation,
            period=period
        )
    
    @staticmethod
    def create_assignment_for_date(
        employee: Employee,
        workstation: Workstation,
        assignment_date: date,
        period_number: int
    ) -> WorkAssignment:
        """
        Create a new WorkAssignment for a specific date and period number.
        
        Args:
            employee: The employee to assign
            workstation: The workstation to assign the employee to
            assignment_date: The date for the assignment
            period_number: The period number (1-5)
            
        Returns:
            A new WorkAssignment value object
            
        Raises:
            ValueError: If the assignment is invalid
        """
        # Create a SchedulePeriod
        period = SchedulePeriod(date=assignment_date, period=period_number)
        
        # Create and return the assignment
        return AssignmentFactory.create_assignment(
            employee=employee,
            workstation=workstation,
            period=period
        )
    
    @staticmethod
    def create_assignment_if_qualified(
        employee: Employee,
        workstation: Workstation,
        period: SchedulePeriod
    ) -> Optional[WorkAssignment]:
        """
        Create a new WorkAssignment only if the employee is qualified for the workstation.
        
        Args:
            employee: The employee to assign
            workstation: The workstation to assign the employee to
            period: The period for the assignment
            
        Returns:
            A new WorkAssignment value object, or None if the employee is not qualified
        """
        try:
            return AssignmentFactory.create_assignment(
                employee=employee,
                workstation=workstation,
                period=period
            )
        except ValueError:
            return None