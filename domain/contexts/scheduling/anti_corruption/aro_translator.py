from typing import List, Optional
from datetime import date

from domain.contexts.assignment.aro_assignment import AROAssignment
from domain.contexts.employee_management.entities.employee import Employee

class AROTranslator:
    """
    Anti-corruption layer that translates ARO assignments into a format
    that the scheduling context can understand.
    """
    
    def __init__(self, employee_repository, aro_repository):
        """
        Initialize the translator with the necessary repositories.
        
        Args:
            employee_repository: Repository for accessing employee information
            aro_repository: Repository for accessing ARO assignments
        """
        self.employee_repository = employee_repository
        self.aro_repository = aro_repository
    
    def get_available_employees_for_team(self, team_id: int, assignment_date: date, 
                                        period: Optional[int] = None) -> List[Employee]:
        """
        Get all employees available for a team on a specific date and period,
        including AROs assigned to the team and excluding those assigned elsewhere.
        
        Args:
            team_id: The ID of the team
            assignment_date: The date to check
            period: Optional period of the day to check
            
        Returns:
            List of available employees
        """
        # Get the team's base roster
        team_employees = self.employee_repository.get_by_team_id(team_id)
        
        # Get employees leaving as AROs
        aro_out_ids = self.aro_repository.get_employees_leaving(team_id, assignment_date, period)
        
        # Get employees joining as AROs
        aro_in_ids = self.aro_repository.get_employees_joining(team_id, assignment_date, period)
        
        # Filter out employees leaving as AROs
        available_employees = [e for e in team_employees if e.id not in aro_out_ids]
        
        # Add employees joining as AROs
        for aro_id in aro_in_ids:
            aro_employee = self.employee_repository.get(aro_id)
            if aro_employee:
                available_employees.append(aro_employee)
        
        return available_employees
    
    def translate_aro_assignments(self, assignments: List[AROAssignment], 
                                 team_id: int, assignment_date: date) -> List[Employee]:
        """
        Translate ARO assignments into available employees for a team.
        
        Args:
            assignments: List of ARO assignments
            team_id: ID of the team to get employees for
            assignment_date: Date to get employees for
            
        Returns:
            List of employees available for the team
        """
        # Get employees joining the team as AROs
        joining_employees = []
        for assignment in assignments:
            if assignment.to_team_id == team_id and assignment.assignment_date == assignment_date:
                employee = self.employee_repository.get(assignment.employee_id)
                if employee:
                    joining_employees.append(employee)
        
        return joining_employees