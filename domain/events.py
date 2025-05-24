from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional
import uuid
from domain.value_objects.schedule_period import SchedulePeriod

@dataclass
class DomainEvent:
    """Base class for all domain events"""
    occurred_on: datetime = field(default_factory=datetime.utcnow, init=False)

    def __post_init__(self):
        if self.occurred_on is None:
            self.occurred_on = datetime.utcnow()


@dataclass
class ScheduleEvent(DomainEvent):
    """Base class for schedule-related events"""
    schedule_id: str  # non-default

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.schedule_id, str):
            raise TypeError("schedule_id must be a string")
        if not self.schedule_id or self.schedule_id.isspace():
            raise ValueError("schedule_id cannot be empty or whitespace")

@dataclass
class ScheduleCreated(DomainEvent):
    """Event raised when a new schedule is created"""
    schedule_id: int
    team_id: int
    start_date: date
    days: int
    periods_per_day: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.schedule_id, int) or self.schedule_id <= 0:
            raise ValueError("schedule_id must be a positive integer")
        if not isinstance(self.team_id, int) or self.team_id <= 0:
            raise ValueError("team_id must be a positive integer")
        if not isinstance(self.start_date, date):
            raise ValueError("start_date must be a date object")
        if not isinstance(self.days, int) or self.days <= 0:
            raise ValueError("days must be a positive integer")
        if not isinstance(self.periods_per_day, int) or self.periods_per_day <= 0:
            raise ValueError("periods_per_day must be a positive integer")


@dataclass
class ScheduleUpdated(DomainEvent):
    """Event raised when a schedule is updated"""
    schedule_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.schedule_id, int) or self.schedule_id <= 0:
            raise ValueError("schedule_id must be a positive integer")


@dataclass
class ScheduleStatusChanged(DomainEvent):
    """Event raised when a schedule's status is changed"""
    schedule_id: int
    old_status: str
    new_status: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.schedule_id, int) or self.schedule_id <= 0:
            raise ValueError("schedule_id must be a positive integer")
        if not isinstance(self.old_status, str):
            raise ValueError("old_status must be a string")
        if not isinstance(self.new_status, str) or not self.new_status:
            raise ValueError("new_status must be a non-empty string")


@dataclass
class AssignmentAdded(DomainEvent):
    """Event raised when an assignment is added to a schedule"""
    schedule_id: int
    employee_id: int
    workstation_id: int
    period: SchedulePeriod

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.schedule_id, int) or self.schedule_id <= 0:
            raise ValueError("schedule_id must be a positive integer")
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.period, SchedulePeriod):
            raise ValueError("period must be a SchedulePeriod instance")


@dataclass
class AssignmentRemoved(DomainEvent):
    """Event raised when an assignment is removed from a schedule"""
    schedule_id: int
    employee_id: int
    workstation_id: int
    period: SchedulePeriod

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.schedule_id, int) or self.schedule_id <= 0:
            raise ValueError("schedule_id must be a positive integer")
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.period, SchedulePeriod):
            raise ValueError("period must be a SchedulePeriod instance")


@dataclass
class AssignmentCreated(DomainEvent):
    """Event raised when a new work assignment is created"""
    employee_id: int
    workstation_id: int
    schedule_period: SchedulePeriod

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.employee_id, int):
            raise TypeError("id must be an integer")
        if not isinstance(self.workstation_id, int):
            raise TypeError("workstation_id must be an integer")
        if not isinstance(self.schedule_period, SchedulePeriod):
            raise TypeError("schedule_period must be a SchedulePeriod instance")
        if self.employee_id <= 0:
            raise ValueError("id must be positive")
        if self.workstation_id <= 0:
            raise ValueError("workstation_id must be positive")

@dataclass
class QualificationAdded(DomainEvent):
    """Event raised when a qualification is added to an employee"""
    employee_id: int
    qualification: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.qualification, str) or not self.qualification:
            raise ValueError("qualification must be a non-empty string")

@dataclass
class QualificationRemoved(DomainEvent):
    """Event raised when a qualification is removed from an employee"""
    employee_id: int
    qualification: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.qualification, str) or not self.qualification:
            raise ValueError("qualification must be a non-empty string")

@dataclass
class RoleAssigned(DomainEvent):
    """Event raised when a role is assigned to an employee"""
    employee_id: int
    role: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.role, str) or not self.role:
            raise ValueError("role must be a non-empty string")

@dataclass
class TeamRoleAssigned(DomainEvent):
    """Event raised when a team role is assigned to an employee"""
    employee_id: int
    team_id: int
    role: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.team_id, int) or self.team_id <= 0:
            raise ValueError("team_id must be a positive integer")
        if not isinstance(self.role, str) or not self.role:
            raise ValueError("role must be a non-empty string")

@dataclass
class WorkHistoryEntryAdded(DomainEvent):
    """Event raised when a work history entry is added to an employee"""
    employee_id: int
    workstation_id: int
    worked_date: date
    work_period: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.worked_date, date):
            raise ValueError("worked_date must be a date object")
        if not isinstance(self.work_period, int) or not 1 <= self.work_period <= 5:
            raise ValueError("work_period must be an integer between 1 and 5")

@dataclass
class TeamMemberAdded(DomainEvent):
    """Event raised when a member is added to a team"""
    team_id: int
    employee_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.team_id, int) or self.team_id <= 0:
            raise ValueError("team_id must be a positive integer")
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")

@dataclass
class TeamMemberRemoved(DomainEvent):
    """Event raised when a member is removed from a team"""
    team_id: int
    employee_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.team_id, int) or self.team_id <= 0:
            raise ValueError("team_id must be a positive integer")
        if not isinstance(self.employee_id, int) or self.employee_id <= 0:
            raise ValueError("employee_id must be a positive integer")

@dataclass
class WorkstationAddedToTeam(DomainEvent):
    """Event raised when a workstation is added to a team"""
    team_id: int
    workstation_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.team_id, int) or self.team_id <= 0:
            raise ValueError("team_id must be a positive integer")
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")

@dataclass
class WorkstationRemovedFromTeam(DomainEvent):
    """Event raised when a workstation is removed from a team"""
    team_id: int
    workstation_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.team_id, int) or self.team_id <= 0:
            raise ValueError("team_id must be a positive integer")
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")

@dataclass
class WorkstationCreated(DomainEvent):
    """Event raised when a new workstation is created"""
    workstation_id: int
    name: str
    line_type: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")
        if not isinstance(self.line_type, str) or not self.line_type:
            raise ValueError("line_type must be a non-empty string")

@dataclass
class WorkstationUpdated(DomainEvent):
    """Event raised when a workstation is updated"""
    workstation_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")

@dataclass
class WorkstationPropertyChanged(DomainEvent):
    """Event raised when a workstation property is changed"""
    workstation_id: int
    property_name: str
    old_value: any
    new_value: any

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.property_name, str) or not self.property_name:
            raise ValueError("property_name must be a non-empty string")

@dataclass
class WorkstationLineTypeChanged(DomainEvent):
    """Event raised when a workstation's line type is changed"""
    workstation_id: int
    old_line_type: str
    new_line_type: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if not isinstance(self.old_line_type, str):
            raise ValueError("old_line_type must be a string")
        if not isinstance(self.new_line_type, str) or not self.new_line_type:
            raise ValueError("new_line_type must be a non-empty string")

@dataclass
class WorkstationTeamChanged(DomainEvent):
    """Event raised when a workstation's team is changed"""
    workstation_id: int
    old_team_id: Optional[int]
    new_team_id: Optional[int]

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.workstation_id, int) or self.workstation_id <= 0:
            raise ValueError("workstation_id must be a positive integer")
        if self.old_team_id is not None and (not isinstance(self.old_team_id, int) or self.old_team_id <= 0):
            raise ValueError("old_team_id must be a positive integer or None")
        if self.new_team_id is not None and (not isinstance(self.new_team_id, int) or self.new_team_id <= 0):
            raise ValueError("new_team_id must be a positive integer or None")

@dataclass
class DepartmentCreated(DomainEvent):
    """Event raised when a new department is created"""
    department_id: int
    name: str
    description: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.department_id, int) or self.department_id <= 0:
            raise ValueError("department_id must be a positive integer")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")
        if self.description is not None and not isinstance(self.description, str):
            raise ValueError("description must be a string or None")

@dataclass
class DepartmentUpdated(DomainEvent):
    """Event raised when a department is updated"""
    department_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.department_id, int) or self.department_id <= 0:
            raise ValueError("department_id must be a positive integer")

@dataclass
class DepartmentPropertyChanged(DomainEvent):
    """Event raised when a department property is changed"""
    department_id: int
    property_name: str
    old_value: any
    new_value: any

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.department_id, int) or self.department_id <= 0:
            raise ValueError("department_id must be a positive integer")
        if not isinstance(self.property_name, str) or not self.property_name:
            raise ValueError("property_name must be a non-empty string")

@dataclass
class GroupAddedToDepartment(DomainEvent):
    """Event raised when a group is added to a department"""
    department_id: int
    group_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.department_id, int) or self.department_id <= 0:
            raise ValueError("department_id must be a positive integer")
        if not isinstance(self.group_id, int) or self.group_id <= 0:
            raise ValueError("group_id must be a positive integer")

@dataclass
class GroupRemovedFromDepartment(DomainEvent):
    """Event raised when a group is removed from a department"""
    department_id: int
    group_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.department_id, int) or self.department_id <= 0:
            raise ValueError("department_id must be a positive integer")
        if not isinstance(self.group_id, int) or self.group_id <= 0:
            raise ValueError("group_id must be a positive integer")

@dataclass
class GroupCreated(DomainEvent):
    """Event raised when a new group is created"""
    group_id: int
    name: str
    department_id: Optional[int] = None

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.group_id, int) or self.group_id <= 0:
            raise ValueError("group_id must be a positive integer")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")
        if self.department_id is not None and (not isinstance(self.department_id, int) or self.department_id <= 0):
            raise ValueError("department_id must be a positive integer or None")

@dataclass
class GroupUpdated(DomainEvent):
    """Event raised when a group is updated"""
    group_id: int

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.group_id, int) or self.group_id <= 0:
            raise ValueError("group_id must be a positive integer")

@dataclass
class GroupPropertyChanged(DomainEvent):
    """Event raised when a group property is changed"""
    group_id: int
    property_name: str
    old_value: any
    new_value: any

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.group_id, int) or self.group_id <= 0:
            raise ValueError("group_id must be a positive integer")
        if not isinstance(self.property_name, str) or not self.property_name:
            raise ValueError("property_name must be a non-empty string")

@dataclass
class GroupDepartmentChanged(DomainEvent):
    """Event raised when a group's department is changed"""
    group_id: int
    old_department_id: Optional[int]
    new_department_id: Optional[int]

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.group_id, int) or self.group_id <= 0:
            raise ValueError("group_id must be a positive integer")
        if self.old_department_id is not None and (not isinstance(self.old_department_id, int) or self.old_department_id <= 0):
            raise ValueError("old_department_id must be a positive integer or None")
        if self.new_department_id is not None and (not isinstance(self.new_department_id, int) or self.new_department_id <= 0):
            raise ValueError("new_department_id must be a positive integer or None")
