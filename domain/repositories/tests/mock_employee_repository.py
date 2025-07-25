from typing import Optional, List, Dict, Tuple
from datetime import date

from domain.contexts.employee_management.entities.employee import Employee
from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface


class MockEmployeeRepository(EmployeeRepositoryInterface):
    """
    Mock implementation of the employee repository for testing.
    """

    def __init__(self):
        self.employees = {}
        self.work_history = {}

    def get_by_id(self, entity_id: int) -> Optional[Employee]:
        """Retrieve an employee by ID."""
        return self.employees.get(entity_id)

    def list_all(self) -> List[Employee]:
        """Retrieve all employees."""
        return list(self.employees.values())

    def add(self, entity: Employee) -> Employee:
        """Add a new employee."""
        self.employees[entity.id] = entity
        return entity

    def update(self, entity: Employee) -> Employee:
        """Update an existing employee."""
        self.employees[entity.id] = entity
        return entity

    def delete(self, entity_id: int) -> bool:
        """Delete an employee by ID."""
        if entity_id in self.employees:
            del self.employees[entity_id]
            return True
        return False

    def get_by_team_id(self, team_id: int) -> List[Employee]:
        """Retrieve all employees for a specific team."""
        return [e for e in self.employees.values() if e.id == team_id]

    def is_available(self, employee_id: int, date_obj: date, period: Optional[int] = None) -> bool:
        """Check if employee is available on the given date and period."""
        return True

    def assign_role(self, employee_id: int, role_name: str, team_id: int) -> Dict[str, str]:
        """Assign a role to an employee within a team."""
        employee = self.employees.get(employee_id)
        if not employee:
            return {"status": "error", "message": "Employee not found"}

        if role_name in employee.roles:
            return {"status": "exists", "message": f"Already has role '{role_name}'"}

        try:
            if employee.add_team_role(role_name, team_id):
                return {"status": "success", "message": f"RoleModel '{role_name}' assigned"}
            else:
                if employee.assign_role(role_name):
                    return {"status": "success", "message": f"RoleModel '{role_name}' assigned"}
                else:
                    return {"status": "exists", "message": f"Already has role '{role_name}'"}
        except ValueError as e:
            return {"status": "error", "message": str(e)}

    def remove_role(self, employee_id: int, role_name: str, team_id: int) -> Dict[str, str]:
        """Remove a role from an employee within a team."""
        employee = self.employees.get(employee_id)
        if not employee:
            return {"status": "error", "message": "Employee not found"}
        for membership in employee.team_memberships:
            if membership.team_id == team_id:
                if role_name in membership.roles:
                    membership.remove_role(role_name)
                    return {"status": "success", "message": f"Removed role '{role_name}'"}
        if role_name not in employee.roles:
            return {"status": "error", "message": f"RoleModel '{role_name}' not found"}
        employee._roles.remove(role_name)
        return {"status": "success", "message": f"Removed role '{role_name}'"}

    def assign_workstation(self, employee_id: int, workstation_id: int) -> Dict[str, str]:
        """Assign a workstation to an employee."""
        employee = self.employees.get(employee_id)
        if not employee:
            return {"status": "error", "message": "Employee not found"}
        try:
            if employee.assign_workstation(workstation_id, f"Workstation {workstation_id}"):
                return {"status": "success", "message": "Workstation assigned"}
            else:
                return {"status": "exists", "message": f"Already assigned to Workstation {workstation_id}"}
        except ValueError as e:
            return {"status": "error", "message": str(e)}

    def get_work_history(self, employee_id: int, workstation_id: int) -> list:
        """Get employee's work history for a specific workstation."""
        key = (employee_id, workstation_id)
        return self.work_history.get(key, [])

    def add_work_history(self, employee_id: int, workstation_id: int,
                         worked_date: date, work_period: int, end_flag: bool = False) -> bool:
        """Add a work history entry."""
        key = (employee_id, workstation_id)
        if key not in self.work_history:
            self.work_history[key] = []

        self.work_history[key].append({
            'id': employee_id,
            'workstation_id': workstation_id,
            'worked_date': worked_date,
            'work_period': work_period,
            'end_flag': end_flag
        })

        return True

    def get_last_worked_date(self, employee_id: int, workstation_id: int) -> Tuple[Optional[date], Optional[int]]:
        """Get the last date an employee worked at a specific workstation."""
        key = (employee_id, workstation_id)
        history = self.work_history.get(key, [])

        if not history:
            return None, None
        sorted_history = sorted(
            history,
            key=lambda x: (x['worked_date'], x['work_period']),
            reverse=True
        )

        return sorted_history[0]['worked_date'], sorted_history[0]['work_period']
