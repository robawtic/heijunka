# heijunka/domain/services/employee_service.py
from typing import List, Optional
from datetime import date

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation


class EmployeeService:
    def assign_role(self, employee: Employee, role_name: str) -> None:
        """Assign a role to an employee"""
        if role_name not in employee.roles:
            employee.roles.append(role_name)

    def remove_role(self, employee: Employee, role_name: str) -> None:
        """Remove a role from an employee"""
        if role_name in employee.roles:
            employee.roles.remove(role_name)

    def assign_qualification(self, employee: Employee, workstation_name: str) -> None:
        """Qualify an employee for a workstation"""
        if workstation_name not in employee.qualifications:
            employee.qualifications.append(workstation_name)

    def get_employee_history(self, employee: Employee,
                             start_date: date, end_date: date) -> List[dict]:
        """Get work history for an employee in the given date range"""
        # This would be implemented with a repository in the infrastructure layer
        return []

    def assign_workstation(self, employee: Employee, workstation: Workstation) -> bool:
        if not employee.assign_workstation(workstation):
            return False
        return self._employee_repository.assign_workstation(employee.id, workstation.id)["status"] == "success"

    def record_work_session(self, employee: Employee, workstation: Workstation,
                          date_obj: date, period: int):
        """Record a work session with all necessary updates"""
        employee.update_work_history(
            employee.id, workstation.id, date_obj, period
        )
