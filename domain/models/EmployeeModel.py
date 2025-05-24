# domain/models/EmployeeModel.py
from typing import List, TYPE_CHECKING

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship

from domain.models.Base import Base

if TYPE_CHECKING:
    from domain.entities.employee import Employee

class EmployeeModel(Base):
    __tablename__ = 'employees'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    team_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)

    # Restore relationships
    workstations = relationship('EmployeeWorkstationModel', back_populates='employee')
    work_history = relationship('EmployeeWorkHistoryModel', back_populates='employee')
    availability = relationship('EmployeeAvailabilityModel', back_populates='employee')  # Changed from EmployeeAvailability
    teams = relationship('TeamMemberModel', back_populates='employee')
    station_skills = relationship('EmployeeStationSkillModel', back_populates='employee')

    def to_domain(self) -> 'Employee':
        from domain.entities.employee import Employee
        from domain.entities.employee_availability import EmployeeAvailability
        from domain.entities.team_member import TeamMember
        from domain.value_objects.work_history_entry import WorkHistoryEntry
        from domain.value_objects.workstation_assignment import WorkstationAssignment

        employee = Employee(
            id=self.id,
            name=self.name,
            team_id=self.team_id,
            is_active=self.is_active,
            _roles=self._get_roles(),
            _qualifications=self._get_qualifications()
        )

        # Convert availability
        for av in self.availability:
            employee._available_periods.append(av.to_domain())

        # Convert work history
        for wh in self.work_history:
            employee._work_history.append(WorkHistoryEntry(
                employee_id=wh.employee_id,
                workstation_id=wh.station_id,
                worked_date=wh.worked_date,
                work_period=wh.work_period,
                end_flag=wh.end_flag
            ))

        # Convert workstation assignments
        for ws in self.workstations:
            employee._assigned_workstations.append(WorkstationAssignment(
                employee_id=ws.employee_id,
                workstation_id=ws.station_id,
                workstation_name=ws.workstation.name if ws.workstation else "Unknown"
            ))

        # Convert team memberships
        for tm in self.teams:
            team_member = TeamMember(
                team_member_id=tm.id,
                team_id=tm.team_id,
                employee_id=tm.employee_id,
                roles=[role.name for role in tm.roles]
            )
            employee._team_memberships.append(team_member)

        return employee

    def _get_roles(self) -> List[str]:
        return [role.name
                for team_member in self.teams
                for role in team_member.roles]

    def _get_qualifications(self) -> List[str]:
        return [ws.workstation.name
                for ws in self.workstations]
