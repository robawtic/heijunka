# Re-export all events for backward compatibility
from .base import DomainEvent
from .schedule import (
    ScheduleEvent, ScheduleCreated, ScheduleUpdated, 
    ScheduleStatusChanged, ScheduleValidationFailed
)
from .employee import (
    QualificationAdded, QualificationRemoved, 
    RoleAssigned, TeamRoleAssigned, WorkHistoryEntryAdded
)
from .team import (
    TeamMemberAdded, TeamMemberRemoved, 
    WorkstationAddedToTeam, WorkstationRemovedFromTeam
)
from .workstation import (
    WorkstationCreated, WorkstationUpdated, 
    WorkstationPropertyChanged, WorkstationLineTypeChanged, 
    WorkstationTeamChanged
)
from .department import (
    DepartmentCreated, DepartmentUpdated, 
    DepartmentPropertyChanged, GroupAddedToDepartment, 
    GroupRemovedFromDepartment
)
from .group import (
    GroupCreated, GroupUpdated, 
    GroupPropertyChanged, GroupDepartmentChanged
)
from .assignment import (
    AssignmentCreated, AssignmentAdded, AssignmentRemoved
)