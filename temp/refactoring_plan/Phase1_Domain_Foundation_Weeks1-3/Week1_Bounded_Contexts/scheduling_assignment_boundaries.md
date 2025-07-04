# Scheduling and Assignment Context Boundaries

## 📋 Overview

This document provides precise clarification of responsibilities between the **Scheduling Context** and **Assignment Context** within the Heijunka system. These two contexts work together to create optimal workforce schedules while maintaining clear separation of concerns.

## 🎯 Context Responsibilities

### 📅 Scheduling Context

**Primary Responsibility**: Schedule lifecycle management and temporal coordination

**Core Responsibilities**:
1. **Schedule Creation & Management**
   - Create schedule entities with metadata (team_id, start_date, periods)
   - Manage schedule status (pending, in_progress, completed, failed, partial)
   - Handle schedule validation and business rules
   - Coordinate schedule regeneration and updates

2. **Temporal Logic**
   - Define and manage schedule periods (SchedulePeriod value object)
   - Handle time-based constraints and validations
   - Manage schedule duration and timing rules

3. **Schedule Coordination**
   - Orchestrate the overall schedule generation process
   - Coordinate with Assignment Context for employee-workstation optimization
   - Handle schedule-level constraints (call-ins, offline employees, force_complete)
   - Manage ARO (Additional Resource Optimization) requests when needed

4. **Schedule Persistence**
   - Persist schedule entities and their metadata
   - Track schedule history and changes
   - Manage schedule repository operations

**Key Services**:
- `ScheduleGenerationService`: Coordinates schedule creation and management

**Key Entities**:
- `Schedule`: Core schedule entity with lifecycle management

**Key Value Objects**:
- `SchedulePeriod`: Represents time periods within schedules

---

### 🔧 Assignment Context

**Primary Responsibility**: Employee-workstation optimization and assignment management

**Core Responsibilities**:
1. **Assignment Optimization**
   - Optimize employee-workstation pairings based on criteria
   - Apply assignment algorithms (greedy, Hungarian, genetic, etc.)
   - Handle assignment scoring and ranking
   - Manage assignment matrix creation and optimization

2. **Assignment Criteria Management**
   - Define and apply assignment constraints and preferences
   - Handle skill-based matching requirements
   - Manage workload balancing and fairness rules
   - Apply time-based and team-based constraints

3. **Work Assignment Creation**
   - Create individual WorkAssignment entities
   - Validate assignments against business rules
   - Handle assignment conflicts and resolution
   - Manage temporary and permanent assignments

4. **ARO Assignment Management**
   - Handle Additional Resource Optimization logic
   - Manage cross-team employee assignments
   - Coordinate ARO graph operations and optimization
   - Handle ARO assignment persistence and tracking

**Key Services**:
- `AssignmentOptimizationService`: Optimizes employee-workstation assignments
- `AROGraphService`: Manages ARO assignment graph operations

**Key Entities**:
- `WorkAssignment`: Individual employee-workstation assignment
- `AROAssignment`: ARO-specific assignment entity

**Key Value Objects**:
- `AssignmentCriteria`: Criteria and constraints for optimization
- `WorkAssignmentValidator`: Assignment validation logic

---

## 🔄 Context Interaction Patterns

### 1. Schedule Generation Flow
```
Scheduling Context → Assignment Context → Scheduling Context
```

1. **Scheduling Context** creates a Schedule entity
2. **Scheduling Context** calls Assignment Context to optimize assignments
3. **Assignment Context** returns optimized WorkAssignments
4. **Scheduling Context** incorporates assignments into the Schedule
5. **Scheduling Context** manages final schedule status and persistence

### 2. ARO Request Flow
```
Scheduling Context → Assignment Context (ARO) → Scheduling Context
```

1. **Scheduling Context** detects insufficient employees
2. **Scheduling Context** requests ARO assignments from Assignment Context
3. **Assignment Context** uses AROGraphService to find optimal AROs
4. **Assignment Context** returns additional employees/assignments
5. **Scheduling Context** incorporates ARO assignments into schedule

### 3. Assignment Validation Flow
```
Assignment Context → Scheduling Context (validation) → Assignment Context
```

1. **Assignment Context** creates potential assignments
2. **Assignment Context** validates against Assignment criteria
3. **Scheduling Context** validates against Schedule constraints
4. **Assignment Context** finalizes valid assignments

---

## 🚧 Clear Boundaries

### What Scheduling Context DOES NOT Handle:
- ❌ Individual employee-workstation optimization algorithms
- ❌ Assignment scoring and ranking logic
- ❌ Detailed assignment criteria management
- ❌ ARO graph operations and optimization
- ❌ Assignment conflict resolution
- ❌ Workstation-specific assignment rules

### What Assignment Context DOES NOT Handle:
- ❌ Schedule entity lifecycle management
- ❌ Schedule status tracking and updates
- ❌ Schedule-level validation rules
- ❌ Schedule persistence and history
- ❌ Overall schedule coordination
- ❌ Schedule regeneration logic

---

## 📊 Data Flow and Dependencies

### Scheduling Context Dependencies:
- **Employee Management Context**: Employee entities and availability
- **Assignment Context**: Assignment optimization services
- **Workstation Management Context**: Workstation entities

### Assignment Context Dependencies:
- **Employee Management Context**: Employee entities and skills
- **Scheduling Context**: SchedulePeriod value objects
- **Workstation Management Context**: Workstation entities

### Shared Concepts:
- **SchedulePeriod**: Defined in Scheduling, used by Assignment
- **Employee**: Defined in Employee Management, used by both
- **Workstation**: Defined in Workstation Management, used by both

---

## 🎯 Integration Points

### 1. Schedule.generate_assignments()
- **Context**: Scheduling Context method
- **Action**: Delegates to Assignment Context for optimization
- **Input**: Employees, workstations, criteria
- **Output**: Optimized WorkAssignments

### 2. AssignmentOptimizationService.optimize_assignments()
- **Context**: Assignment Context service
- **Action**: Creates optimized assignments for given parameters
- **Input**: Employees, workstations, date, periods, criteria
- **Output**: List of WorkAssignments

### 3. AROGraphService.assign_optimal_aros()
- **Context**: Assignment Context service
- **Action**: Finds optimal ARO assignments for understaffed teams
- **Input**: Team ID, needed AROs, date, period
- **Output**: ARO assignments

---

## 🔍 Business Rules Distribution

### Scheduling Context Rules:
- Schedule must have valid team_id and start_date
- Schedule periods must be between 1-5
- Schedule status transitions must follow defined workflow
- Call-ins and offline employees affect schedule generation
- Force_complete flag determines partial schedule acceptance

### Assignment Context Rules:
- Employees can only be assigned to workstations they can work
- No employee can be assigned to multiple workstations in same period
- Assignment criteria must be validated before optimization
- ARO assignments must respect team boundaries and availability
- Assignment scores must be calculated based on defined criteria

---

## 📈 Future Considerations

### Potential Enhancements:
1. **Event-Driven Communication**: Implement domain events for context communication
2. **Assignment Strategies**: Support multiple assignment algorithms
3. **Real-time Optimization**: Support dynamic assignment updates
4. **Advanced ARO Logic**: Enhanced cross-team optimization
5. **Assignment Analytics**: Track assignment effectiveness and metrics

### Architectural Benefits:
- **Clear Separation**: Each context has distinct, well-defined responsibilities
- **Loose Coupling**: Contexts interact through well-defined interfaces
- **Independent Evolution**: Each context can evolve independently
- **Testability**: Clear boundaries enable focused unit and integration testing
- **Maintainability**: Reduced complexity through proper separation of concerns

---

## ✅ Summary

The **Scheduling Context** is responsible for the overall schedule lifecycle, coordination, and temporal management, while the **Assignment Context** focuses on the optimization and creation of individual employee-workstation assignments. This clear separation enables:

- **Scheduling Context**: "When and how should we create schedules?"
- **Assignment Context**: "Who should work where and when within those schedules?"

This boundary ensures that each context can evolve independently while maintaining a cohesive system that efficiently manages workforce scheduling and assignment optimization.