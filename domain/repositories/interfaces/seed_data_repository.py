from typing import List, Optional, Dict, Any
from domain.contexts.shared.entities.seed_data import (
    WorkstationSeedData, EmployeeSeedData, TeamSeedData, 
    GroupSeedData, DepartmentSeedData
)


class SeedDataRepositoryInterface:
    """Interface for repositories that handle seed data."""
    
    def load_workstation_data(self, team_name: str) -> List[WorkstationSeedData]:
        """
        Load workstation seed data for a team.
        
        Args:
            team_name: The name of the team
            
        Returns:
            A list of WorkstationSeedData objects
        """
        raise NotImplementedError
    
    def load_employee_data(self, team_name: str) -> List[EmployeeSeedData]:
        """
        Load employee seed data for a team.
        
        Args:
            team_name: The name of the team
            
        Returns:
            A list of EmployeeSeedData objects
        """
        raise NotImplementedError
    
    def load_team_data(self, team_name: str) -> TeamSeedData:
        """
        Load all seed data for a team.
        
        Args:
            team_name: The name of the team
            
        Returns:
            A TeamSeedData object containing workstation and employee data
        """
        raise NotImplementedError
    
    def load_group_data(self, group_name: str) -> GroupSeedData:
        """
        Load all seed data for a group.
        
        Args:
            group_name: The name of the group
            
        Returns:
            A GroupSeedData object containing team data
        """
        raise NotImplementedError
    
    def load_department_data(self, department_name: str) -> DepartmentSeedData:
        """
        Load all seed data for a department.
        
        Args:
            department_name: The name of the department
            
        Returns:
            A DepartmentSeedData object containing group data
        """
        raise NotImplementedError
    
    def get_available_departments(self) -> List[str]:
        """
        Get a list of available department names.
        
        Returns:
            A list of department names
        """
        raise NotImplementedError
    
    def get_available_groups(self, department_name: Optional[str] = None) -> List[str]:
        """
        Get a list of available group names.
        
        Args:
            department_name: Optional department name to filter by
            
        Returns:
            A list of group names
        """
        raise NotImplementedError
    
    def get_available_teams(self, department_name: Optional[str] = None, group_name: Optional[str] = None) -> List[str]:
        """
        Get a list of available team names.
        
        Args:
            department_name: Optional department name to filter by
            group_name: Optional group name to filter by
            
        Returns:
            A list of team names
        """
        raise NotImplementedError