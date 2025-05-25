# domain/factories/employee_factory.py
from typing import List, Optional
from datetime import date
from domain.entities.employee import Employee
from domain.entities.employee_availability import EmployeeAvailability
from domain.entities.team_member import TeamMember
from domain.value_objects.workstation_assignment import WorkstationAssignment
from domain.value_objects.work_history_entry import WorkHistoryEntry

class EmployeeFactory:
    @staticmethod
    def create_employee(
        id: Optional[int] = None,
        name: str = "",
        team_id: Optional[int] = None,
        is_active: bool = True,
        roles: List[str] = None,
        qualifications: List[str] = None
    ) -> Employee:
        """Create a new Employee entity with basic properties."""
        return Employee(
            id=id,
            name=name,
            team_id=team_id,
            is_active=is_active,
            _roles=roles or [],
            _qualifications=qualifications or []
        )
    
    @staticmethod
    def create_employee_with_availability(
        id: Optional[int] = None,
        name: str = "",
        team_id: Optional[int] = None,
        is_active: bool = True,
        roles: List[str] = None,
        qualifications: List[str] = None,
        availabilities: List[EmployeeAvailability] = None
    ) -> Employee:
        """Create an Employee with availability information."""
        employee = EmployeeFactory.create_employee(
            id, name, team_id, is_active, roles, qualifications
        )
        
        if availabilities:
            for availability in availabilities:
                employee.add_availability(availability)
                
        return employee
    
    @staticmethod
    def create_employee_with_workstations(
        id: Optional[int] = None,
        name: str = "",
        team_id: Optional[int] = None,
        is_active: bool = True,
        roles: List[str] = None,
        qualifications: List[str] = None,
        workstation_assignments: List[WorkstationAssignment] = None
    ) -> Employee:
        """Create an Employee with workstation assignments."""
        employee = EmployeeFactory.create_employee(
            id, name, team_id, is_active, roles, qualifications
        )
        
        if workstation_assignments:
            for assignment in workstation_assignments:
                employee._assigned_workstations.append(assignment)
                
        return employee
    
    @staticmethod
    def create_employee_with_team_roles(
        id: Optional[int] = None,
        name: str = "",
        team_id: Optional[int] = None,
        is_active: bool = True,
        qualifications: List[str] = None,
        team_memberships: List[TeamMember] = None
    ) -> Employee:
        """Create an Employee with team memberships and roles."""
        # Extract roles from team memberships
        roles = []
        if team_memberships:
            for membership in team_memberships:
                roles.extend(membership.roles)
        
        employee = EmployeeFactory.create_employee(
            id, name, team_id, is_active, roles, qualifications
        )
        
        if team_memberships:
            for membership in team_memberships:
                employee._team_memberships.append(membership)
                
        return employee
    
    @staticmethod
    def create_from_model(model) -> Employee:
        """Create an Employee entity from a database model."""
        employee = EmployeeFactory.create_employee(
            id=model.id,
            name=model.name,
            team_id=model.team_id,
            is_active=model.is_active,
            roles=[role.name for team_member in model.teams for role in team_member.roles],
            qualifications=[ws.workstation.name for ws in model.workstations if ws.workstation]
        )
        
        # Add availability
        for av in model.availability:
            employee.add_availability(av.to_domain())
        
        # Add work history
        for wh in model.work_history:
            employee.add_work_history_entry(
                wh.station_id, wh.worked_date, wh.work_period
            )
        
        # Add workstation assignments
        for ws in model.workstations:
            if ws.workstation:
                employee.assign_workstation(
                    ws.station_id, 
                    ws.workstation.name
                )
        
        # Add team memberships
        for tm in model.teams:
            for role in tm.roles:
                employee.add_team_role(role.name, tm.team_id)
        
        return employee