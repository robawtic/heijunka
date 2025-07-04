# Aggregate Boundaries and Invariants

This document defines the aggregate roots, their boundaries, and enforced business invariants in the Heijunka system.

Clearly defined aggregates encapsulate critical business logic and rules, enforcing domain integrity. Explicit invariants documented here must be rigorously upheld in implementation.

---

## ?? UserAggregate (User Management Context)
**Aggregate Root**: User  
**Entities Included**: User, ApiKey, RefreshToken  
**Value Objects**: Role  
**Invariants**:
- Usernames must be unique across the system.
- API keys must always be associated with an active user.
- Refresh tokens must expire and be securely managed.
- Users must have valid email addresses when provided.
- Password hashes must be properly encrypted using bcrypt.
- API keys must have valid scopes and IP restrictions when specified.

---

## ?? EmployeeAggregate (Employee Management Context)
**Aggregate Root**: Employee  
**Entities Included**: Employee, TeamMember  
**Value Objects**: EmployeeAvailability, WorkHistoryEntry, WorkstationAssignment  
**Invariants**:
- Employee qualifications must be valid and current.
- Employee availability periods cannot overlap for the same date.
- Work history entries must have valid workstation and date references.
- Team role assignments must be valid for the specified team.
- Employee availability status must be consistent with assigned periods.

---

## ?? ScheduleAggregate (Scheduling Context)
**Aggregate Root**: Schedule  
**Entities Included**: Schedule  
**Value Objects**: SchedulePeriod  
**Invariants**:
- A schedule cannot contain overlapping time slots for the same resource.
- A schedule must have clearly defined periods per day.
- Schedule status must be one of the valid states (pending, in_progress, completed, failed).
- Schedule dates must be valid and in the future for active schedules.
- Schedule validation must pass before assignments can be generated.

---

## ?? WorkstationAggregate (Workstation Management Context)
**Aggregate Root**: Workstation  
**Entities Included**: Workstation  
**Value Objects**: WorkstationCapacity, WorkstationLocation (implied)  
**Invariants**:
- Workstation names must be unique within the system.
- Workstation line types must be valid predefined values.
- Team assignments to workstations must reference valid teams.
- Workstation properties (heavy, loading, key skill) must be boolean values.
- Workstation validation must pass for all property combinations.

---

## ?? AssignmentAggregate (Assignment Context)
**Aggregate Root**: WorkAssignment  
**Entities Included**: WorkAssignment  
**Value Objects**: WorkAssignmentValidator, AssignmentCriteria (implied)  
**Invariants**:
- Assignments must comply with workstation capabilities and requirements.
- No employee can be double-assigned during overlapping periods.
- Assignment validation must pass before work assignments are created.
- Work assignments must reference valid employees and workstations.
- Assignment periods must align with schedule periods.
- ARO assignments must follow specific optimization rules.
