# Goal 3: Implement Aggregate Roots with Proper Invariant Enforcement

## Objective
Identify and implement proper aggregate roots with comprehensive invariant enforcement, ensuring business consistency boundaries are clearly defined and maintained according to DDD principles.

## Current State Analysis

### Aggregate Identification Issues
Based on the codebase analysis, the current implementation lacks proper aggregate boundaries:

1. **Missing Aggregate Roots**: Entities exist without clear aggregate root designation
2. **Weak Invariant Enforcement**: Business invariants are not consistently enforced
3. **Inconsistent Boundaries**: Related entities are not properly grouped into aggregates
4. **Direct Entity Access**: Entities can be modified directly without going through aggregate roots
5. **Transaction Boundary Confusion**: Unclear what constitutes a single business transaction

### Current Entity Structure Analysis

#### 1. User Management Context
**Current Entities**:
- `User` (potential aggregate root)
- `ApiKey` (should be part of User aggregate)
- `RefreshToken` (should be part of User aggregate)

**Issues**:
- ApiKey and RefreshToken can be modified independently
- No invariant enforcement between User and their keys/tokens
- Missing aggregate boundary definition

#### 2. Workstation Management Context
**Current Entities**:
- `Workstation` (potential aggregate root)

**Issues**:
- Workstation updates don't enforce business invariants
- Missing related entities that should be part of the aggregate
- No capacity or configuration consistency enforcement

#### 3. Scheduling Context
**Current Entities**:
- `Schedule` (potential aggregate root)
- `TimeSlot` (should be part of Schedule aggregate)
- `EmployeeSchedule` (should be part of Schedule aggregate)

**Issues**:
- Schedule components can be modified independently
- No enforcement of scheduling business rules
- Missing aggregate boundary for schedule consistency

#### 4. Assignment Context
**Current Entities**:
- `WorkAssignment` (potential aggregate root)

**Issues**:
- Assignment modifications don't enforce business constraints
- Missing related entities for complete assignment context
- No invariant enforcement for assignment validity

## Implementation Plan

### Phase 3.1: Define Aggregate Boundaries (Days 1-2)

#### Step 1: Create User Aggregate Root
**Target Location**: `domain/contexts/user_management/aggregates/user_aggregate.py`

**Aggregate Composition**:
- **Root**: User entity
- **Child Entities**: ApiKey, RefreshToken
- **Value Objects**: UserCredentials, UserProfile, UserPreferences

**Invariants to Enforce**:
- User can have maximum number of active API keys
- API key scopes must be subset of user permissions
- Refresh tokens must belong to active users
- User deactivation must invalidate all tokens and keys

**Methods to Implement**:
```python
class UserAggregate:
    def __init__(self, user: User):
        self._user = user
        self._api_keys: List[ApiKey] = []
        self._refresh_tokens: List[RefreshToken] = []
        self._domain_events: List[DomainEvent] = []
    
    def create_api_key(self, scopes: List[str], restrictions: ApiKeyRestrictions) -> ApiKey
    def revoke_api_key(self, api_key_id: int) -> None
    def create_refresh_token(self, device_info: DeviceInfo) -> RefreshToken
    def revoke_refresh_token(self, token_id: int) -> None
    def deactivate_user(self, reason: str) -> None
    def update_user_permissions(self, new_permissions: List[Permission]) -> None
    def validate_invariants(self) -> List[InvariantViolation]
```

#### Step 2: Create Workstation Aggregate Root
**Target Location**: `domain/contexts/workstation_management/aggregates/workstation_aggregate.py`

**Aggregate Composition**:
- **Root**: Workstation entity
- **Child Entities**: WorkstationCapacity, MaintenanceRecord
- **Value Objects**: WorkstationConfiguration, SafetyRequirements, PerformanceMetrics

**Invariants to Enforce**:
- Workstation capacity cannot exceed safety limits
- Maintenance schedules cannot conflict with production schedules
- Configuration changes must maintain safety compliance
- Performance metrics must be within acceptable ranges

**Methods to Implement**:
```python
class WorkstationAggregate:
    def __init__(self, workstation: Workstation):
        self._workstation = workstation
        self._capacity_records: List[WorkstationCapacity] = []
        self._maintenance_records: List[MaintenanceRecord] = []
        self._domain_events: List[DomainEvent] = []
    
    def update_configuration(self, new_config: WorkstationConfiguration) -> None
    def schedule_maintenance(self, maintenance_window: MaintenanceWindow) -> None
    def update_capacity(self, new_capacity: CapacitySpecification) -> None
    def record_performance_metrics(self, metrics: PerformanceMetrics) -> None
    def validate_safety_compliance(self) -> SafetyComplianceResult
    def validate_invariants(self) -> List[InvariantViolation]
```

#### Step 3: Create Schedule Aggregate Root
**Target Location**: `domain/contexts/scheduling/aggregates/schedule_aggregate.py`

**Aggregate Composition**:
- **Root**: Schedule entity
- **Child Entities**: TimeSlot, EmployeeSchedule, WorkstationSchedule
- **Value Objects**: SchedulePeriod, ShiftPattern, BreakRequirements

**Invariants to Enforce**:
- No employee can be scheduled for overlapping time slots
- Workstation capacity cannot be exceeded in any time slot
- Break requirements must be satisfied for all employees
- Shift patterns must comply with labor regulations

**Methods to Implement**:
```python
class ScheduleAggregate:
    def __init__(self, schedule: Schedule):
        self._schedule = schedule
        self._time_slots: List[TimeSlot] = []
        self._employee_schedules: List[EmployeeSchedule] = []
        self._workstation_schedules: List[WorkstationSchedule] = []
        self._domain_events: List[DomainEvent] = []
    
    def assign_employee_to_slot(self, employee_id: int, time_slot: TimeSlot, workstation_id: int) -> None
    def remove_employee_from_slot(self, employee_id: int, time_slot: TimeSlot) -> None
    def update_shift_pattern(self, employee_id: int, new_pattern: ShiftPattern) -> None
    def validate_schedule_consistency(self) -> ScheduleValidationResult
    def apply_break_requirements(self, break_rules: BreakRequirements) -> None
    def validate_invariants(self) -> List[InvariantViolation]
```

#### Step 4: Create Assignment Aggregate Root
**Target Location**: `domain/contexts/assignment/aggregates/work_assignment_aggregate.py`

**Aggregate Composition**:
- **Root**: WorkAssignment entity
- **Child Entities**: AssignmentHistory, PerformanceRecord
- **Value Objects**: AssignmentCriteria, SkillRequirements, PerformanceTargets

**Invariants to Enforce**:
- Employee must have required skills for assignment
- Assignment must not conflict with existing assignments
- Performance targets must be achievable
- Assignment duration must comply with labor regulations

**Methods to Implement**:
```python
class WorkAssignmentAggregate:
    def __init__(self, assignment: WorkAssignment):
        self._assignment = assignment
        self._history_records: List[AssignmentHistory] = []
        self._performance_records: List[PerformanceRecord] = []
        self._domain_events: List[DomainEvent] = []
    
    def assign_employee(self, employee: Employee, criteria: AssignmentCriteria) -> None
    def reassign_employee(self, new_employee: Employee, reason: str) -> None
    def update_performance_targets(self, new_targets: PerformanceTargets) -> None
    def record_performance(self, performance_data: PerformanceData) -> None
    def complete_assignment(self, completion_data: AssignmentCompletionData) -> None
    def validate_invariants(self) -> List[InvariantViolation]
```

### Phase 3.2: Implement Invariant Enforcement Infrastructure (Days 2-4)

#### Step 5: Create Invariant Validation Framework
**Target Location**: `domain/contexts/shared/invariants/`

**Components to Create**:
```python
# invariant_validator.py
class InvariantValidator:
    def validate_aggregate(self, aggregate: AggregateRoot) -> InvariantValidationResult
    def validate_business_rules(self, aggregate: AggregateRoot, rules: List[BusinessRule]) -> ValidationResult
    def check_consistency(self, aggregate: AggregateRoot) -> ConsistencyCheckResult

# invariant_violation.py
@dataclass(frozen=True)
class InvariantViolation:
    aggregate_id: str
    aggregate_type: str
    violation_type: InvariantViolationType
    rule_name: str
    message: str
    severity: Severity
    current_state: Dict[str, Any]
    expected_state: Dict[str, Any]
    suggested_fix: Optional[str]

# business_rule.py
class BusinessRule(ABC):
    @abstractmethod
    def validate(self, aggregate: AggregateRoot) -> RuleValidationResult
    
    @abstractmethod
    def get_rule_name(self) -> str
    
    @abstractmethod
    def get_description(self) -> str
```

#### Step 6: Create Aggregate Base Classes
**Target Location**: `domain/contexts/shared/aggregates/`

**Base Classes to Create**:
```python
# aggregate_root.py
class AggregateRoot(ABC):
    def __init__(self):
        self._domain_events: List[DomainEvent] = []
        self._version: int = 0
        self._created_at: datetime = datetime.utcnow()
        self._updated_at: datetime = datetime.utcnow()
    
    @abstractmethod
    def get_id(self) -> Any
    
    @abstractmethod
    def validate_invariants(self) -> List[InvariantViolation]
    
    def add_domain_event(self, event: DomainEvent) -> None
    def clear_domain_events(self) -> None
    def get_domain_events(self) -> List[DomainEvent]
    def increment_version(self) -> None
    
    def apply_business_rules(self, rules: List[BusinessRule]) -> None
        violations = []
        for rule in rules:
            result = rule.validate(self)
            if not result.is_valid:
                violations.extend(result.violations)
        
        if violations:
            raise InvariantViolationException(violations)

# entity.py
class Entity(ABC):
    def __init__(self, id: Any):
        self._id = id
        self._created_at: datetime = datetime.utcnow()
        self._updated_at: datetime = datetime.utcnow()
    
    @property
    def id(self) -> Any:
        return self._id
    
    def mark_as_updated(self) -> None:
        self._updated_at = datetime.utcnow()
```

### Phase 3.3: Implement Specific Business Rules (Days 4-7)

#### Step 7: Create User Management Business Rules
**Target Location**: `domain/contexts/user_management/business_rules/`

**Rules to Implement**:
```python
class MaxApiKeysRule(BusinessRule):
    def __init__(self, max_keys: int = 10):
        self.max_keys = max_keys
    
    def validate(self, aggregate: UserAggregate) -> RuleValidationResult:
        active_keys = len([key for key in aggregate.api_keys if key.is_active])
        if active_keys > self.max_keys:
            return RuleValidationResult.invalid(
                f"User has {active_keys} active API keys, maximum allowed is {self.max_keys}"
            )
        return RuleValidationResult.valid()

class ApiKeyScopeRule(BusinessRule):
    def validate(self, aggregate: UserAggregate) -> RuleValidationResult:
        user_permissions = set(aggregate.user.permissions)
        for api_key in aggregate.api_keys:
            key_scopes = set(api_key.scopes)
            if not key_scopes.issubset(user_permissions):
                invalid_scopes = key_scopes - user_permissions
                return RuleValidationResult.invalid(
                    f"API key has scopes {invalid_scopes} not granted to user"
                )
        return RuleValidationResult.valid()

class ActiveUserTokensRule(BusinessRule):
    def validate(self, aggregate: UserAggregate) -> RuleValidationResult:
        if not aggregate.user.is_active:
            active_tokens = [token for token in aggregate.refresh_tokens if token.is_active]
            active_keys = [key for key in aggregate.api_keys if key.is_active]
            
            if active_tokens or active_keys:
                return RuleValidationResult.invalid(
                    "Inactive user cannot have active tokens or API keys"
                )
        return RuleValidationResult.valid()
```

#### Step 8: Create Workstation Management Business Rules
**Target Location**: `domain/contexts/workstation_management/business_rules/`

**Rules to Implement**:
```python
class WorkstationCapacityRule(BusinessRule):
    def validate(self, aggregate: WorkstationAggregate) -> RuleValidationResult:
        workstation = aggregate.workstation
        if workstation.current_capacity > workstation.max_capacity:
            return RuleValidationResult.invalid(
                f"Workstation capacity {workstation.current_capacity} exceeds maximum {workstation.max_capacity}"
            )
        return RuleValidationResult.valid()

class SafetyComplianceRule(BusinessRule):
    def validate(self, aggregate: WorkstationAggregate) -> RuleValidationResult:
        safety_result = aggregate.validate_safety_compliance()
        if not safety_result.is_compliant:
            return RuleValidationResult.invalid(
                f"Workstation fails safety compliance: {safety_result.violations}"
            )
        return RuleValidationResult.valid()

class MaintenanceScheduleRule(BusinessRule):
    def validate(self, aggregate: WorkstationAggregate) -> RuleValidationResult:
        # Check for overlapping maintenance windows
        maintenance_records = aggregate.maintenance_records
        for i, record1 in enumerate(maintenance_records):
            for record2 in maintenance_records[i+1:]:
                if record1.overlaps_with(record2):
                    return RuleValidationResult.invalid(
                        f"Maintenance schedules overlap: {record1.window} and {record2.window}"
                    )
        return RuleValidationResult.valid()
```

#### Step 9: Create Scheduling Business Rules
**Target Location**: `domain/contexts/scheduling/business_rules/`

**Rules to Implement**:
```python
class NoOverlappingAssignmentsRule(BusinessRule):
    def validate(self, aggregate: ScheduleAggregate) -> RuleValidationResult:
        employee_slots = {}
        for slot in aggregate.time_slots:
            for assignment in slot.assignments:
                employee_id = assignment.employee_id
                if employee_id not in employee_slots:
                    employee_slots[employee_id] = []
                employee_slots[employee_id].append(slot)
        
        for employee_id, slots in employee_slots.items():
            for i, slot1 in enumerate(slots):
                for slot2 in slots[i+1:]:
                    if slot1.overlaps_with(slot2):
                        return RuleValidationResult.invalid(
                            f"Employee {employee_id} has overlapping assignments: {slot1.period} and {slot2.period}"
                        )
        return RuleValidationResult.valid()

class WorkstationCapacityRule(BusinessRule):
    def validate(self, aggregate: ScheduleAggregate) -> RuleValidationResult:
        for slot in aggregate.time_slots:
            workstation_assignments = {}
            for assignment in slot.assignments:
                workstation_id = assignment.workstation_id
                if workstation_id not in workstation_assignments:
                    workstation_assignments[workstation_id] = 0
                workstation_assignments[workstation_id] += 1
            
            for workstation_id, count in workstation_assignments.items():
                workstation = aggregate.get_workstation(workstation_id)
                if count > workstation.capacity:
                    return RuleValidationResult.invalid(
                        f"Workstation {workstation_id} has {count} assignments but capacity is {workstation.capacity}"
                    )
        return RuleValidationResult.valid()

class BreakRequirementsRule(BusinessRule):
    def validate(self, aggregate: ScheduleAggregate) -> RuleValidationResult:
        for employee_schedule in aggregate.employee_schedules:
            if not employee_schedule.satisfies_break_requirements():
                return RuleValidationResult.invalid(
                    f"Employee {employee_schedule.employee_id} schedule violates break requirements"
                )
        return RuleValidationResult.valid()
```

### Phase 3.4: Implement Repository Pattern for Aggregates (Days 7-9)

#### Step 10: Create Aggregate Repository Interfaces
**Target Locations**:
- `domain/contexts/user_management/repositories/user_aggregate_repository.py`
- `domain/contexts/workstation_management/repositories/workstation_aggregate_repository.py`
- `domain/contexts/scheduling/repositories/schedule_aggregate_repository.py`
- `domain/contexts/assignment/repositories/work_assignment_aggregate_repository.py`

**Repository Pattern for Aggregates**:
```python
class UserAggregateRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[UserAggregate]
    
    @abstractmethod
    def save(self, aggregate: UserAggregate) -> None
    
    @abstractmethod
    def delete(self, aggregate: UserAggregate) -> None
    
    def save_with_invariant_validation(self, aggregate: UserAggregate) -> None:
        violations = aggregate.validate_invariants()
        if violations:
            raise InvariantViolationException(violations)
        
        # Apply business rules
        business_rules = self._get_business_rules()
        aggregate.apply_business_rules(business_rules)
        
        self.save(aggregate)
```

#### Step 11: Implement Unit of Work Pattern
**Target Location**: `domain/contexts/shared/unit_of_work/`

**Unit of Work Implementation**:
```python
class UnitOfWork(ABC):
    def __init__(self):
        self._aggregates: List[AggregateRoot] = []
        self._is_committed = False
    
    def register_aggregate(self, aggregate: AggregateRoot) -> None:
        if aggregate not in self._aggregates:
            self._aggregates.append(aggregate)
    
    def commit(self) -> None:
        # Validate all aggregates
        all_violations = []
        for aggregate in self._aggregates:
            violations = aggregate.validate_invariants()
            all_violations.extend(violations)
        
        if all_violations:
            raise InvariantViolationException(all_violations)
        
        # Save all aggregates
        for aggregate in self._aggregates:
            self._save_aggregate(aggregate)
        
        # Publish domain events
        for aggregate in self._aggregates:
            self._publish_domain_events(aggregate)
        
        self._is_committed = True
    
    @abstractmethod
    def _save_aggregate(self, aggregate: AggregateRoot) -> None:
        pass
    
    @abstractmethod
    def _publish_domain_events(self, aggregate: AggregateRoot) -> None:
        pass
```

### Phase 3.5: Integration and Testing (Days 9-10)

#### Step 12: Update Application Services
**Target**: Application layer services

**Changes**:
- Use aggregate repositories instead of entity repositories
- Work with aggregates instead of individual entities
- Implement proper transaction boundaries using Unit of Work
- Handle invariant violations appropriately

**Example Application Service Update**:
```python
class UserApplicationService:
    def __init__(self, 
                 user_aggregate_repo: UserAggregateRepository,
                 unit_of_work: UnitOfWork):
        self._user_aggregate_repo = user_aggregate_repo
        self._unit_of_work = unit_of_work
    
    def create_api_key(self, user_id: int, scopes: List[str], restrictions: ApiKeyRestrictions) -> ApiKey:
        # Load aggregate
        user_aggregate = self._user_aggregate_repo.get_by_id(user_id)
        if not user_aggregate:
            raise UserNotFoundException(user_id)
        
        # Perform business operation
        api_key = user_aggregate.create_api_key(scopes, restrictions)
        
        # Register with unit of work
        self._unit_of_work.register_aggregate(user_aggregate)
        
        # Commit transaction (includes invariant validation)
        self._unit_of_work.commit()
        
        return api_key
```

#### Step 13: Create Comprehensive Tests
**Test Categories**:

1. **Aggregate Invariant Tests**:
   - Test each business rule individually
   - Test combinations of business rules
   - Test edge cases and boundary conditions

2. **Aggregate Behavior Tests**:
   - Test aggregate methods produce correct state changes
   - Test domain events are generated correctly
   - Test aggregate consistency after operations

3. **Integration Tests**:
   - Test aggregate persistence and retrieval
   - Test Unit of Work transaction boundaries
   - Test cross-aggregate consistency

## Success Criteria

### Technical Validation
- [ ] All aggregates properly implement invariant enforcement
- [ ] Business rules are clearly defined and testable
- [ ] Aggregate boundaries are well-defined and respected
- [ ] Unit of Work pattern ensures transaction consistency
- [ ] Domain events are properly generated and handled
- [ ] Repository pattern works correctly with aggregates
- [ ] All invariant violations are properly handled

### Business Validation
- [ ] Business invariants are consistently enforced across all operations
- [ ] Aggregate boundaries align with business transaction boundaries
- [ ] Business rules are traceable to business requirements
- [ ] Invariant violations provide clear business feedback
- [ ] Aggregates maintain business consistency at all times

### Architectural Validation
- [ ] Clear separation between aggregates and entities
- [ ] Proper encapsulation of business logic within aggregates
- [ ] Consistent aggregate interface across all bounded contexts
- [ ] Proper dependency direction (application → domain)
- [ ] Clean integration with existing domain services

## Risk Mitigation

### Potential Issues
1. **Performance Impact**: Invariant validation might slow down operations
2. **Complex Invariants**: Some business rules might be too complex for single aggregates
3. **Cross-Aggregate Consistency**: Maintaining consistency across aggregate boundaries
4. **Migration Complexity**: Converting existing code to use aggregates

### Mitigation Strategies
1. **Selective Validation**: Only validate invariants when necessary, cache validation results
2. **Domain Services**: Use domain services for complex cross-aggregate business rules
3. **Eventual Consistency**: Accept eventual consistency for cross-aggregate operations
4. **Gradual Migration**: Implement aggregates incrementally, maintain backward compatibility

## Testing Strategy

### Unit Tests Required
- Individual business rule validation tests
- Aggregate method behavior tests
- Invariant enforcement tests
- Domain event generation tests

### Integration Tests Required
- Aggregate persistence and retrieval tests
- Unit of Work transaction tests
- Cross-aggregate consistency tests
- Performance tests for invariant validation

### Business Rule Tests Required
- Business stakeholder validation of rules
- Rule consistency tests across aggregates
- Rule evolution and backward compatibility tests

## Timeline
- **Days 1-2**: Define aggregate boundaries and create aggregate roots
- **Days 2-4**: Implement invariant enforcement infrastructure
- **Days 4-7**: Implement specific business rules for each aggregate
- **Days 7-9**: Implement repository pattern and Unit of Work for aggregates
- **Days 9-10**: Integration, testing, and application service updates

## Dependencies
- Completion of Goal 1 (Extract Domain Services from Infrastructure)
- Completion of Goal 2 (Create Domain Services for Business Rules Validation)
- Domain event infrastructure
- Repository pattern implementation
- Unit of Work pattern implementation

## Next Steps
After completing this goal:
1. Begin Phase 2: Application Layer Restructuring
2. Implement CQRS pattern with proper aggregate handling
3. Add cross-cutting concerns for aggregate auditing and monitoring
4. Implement event sourcing for critical aggregates (if required)

## Business Value
- **Data Consistency**: Business invariants ensure data remains consistent
- **Business Rule Enforcement**: Critical business rules are automatically enforced
- **Transaction Integrity**: Clear transaction boundaries prevent partial updates
- **Maintainability**: Business logic is centralized and easily maintainable
- **Testability**: Business rules can be thoroughly tested in isolation
- **Reliability**: System prevents invalid business states from occurring