# Goal 2: Create Proper Domain Services for Business Rules Validation

## Objective
Identify and consolidate complex business rules scattered throughout the codebase into proper domain services, ensuring business logic is centralized, testable, and follows DDD principles.

## Current State Analysis

### Business Rules Scattered Across Layers
Based on the codebase analysis, business rules are currently distributed across:

1. **Entity Methods**: Some business rules are embedded in entity methods
2. **Application Services**: Complex validation logic mixed with orchestration
3. **Repository Implementations**: Business rules in data access layer
4. **Presentation Layer**: Validation logic in API controllers
5. **Infrastructure Services**: Business decisions in technical components

### Key Business Domains Requiring Rule Consolidation

#### 1. Scheduling Domain
- **Current Location**: `domain/contexts/scheduling/services/schedule_generation_service.py`
- **Issues**: Complex scheduling rules mixed with generation logic
- **Business Rules Identified**:
  - Employee availability validation
  - Workstation capacity constraints
  - Shift pattern compliance
  - Break time requirements
  - Overtime regulations
  - Skill-to-workstation matching

#### 2. Assignment Domain  
- **Current Location**: `domain/contexts/assignment/services/assignment_optimization_service.py`
- **Issues**: Optimization algorithms mixed with business rule validation
- **Business Rules Identified**:
  - Employee-workstation compatibility
  - Load balancing requirements
  - Priority assignment rules
  - Conflict resolution policies
  - Performance-based assignment preferences

#### 3. User Management Domain
- **Current Location**: `domain/contexts/user_management/services/user_service.py`
- **Issues**: User creation and authentication mixed with business validation
- **Business Rules Identified**:
  - Password complexity requirements
  - Role assignment policies
  - Account activation rules
  - Session management policies
  - API key generation constraints

#### 4. Workstation Management Domain
- **Current Location**: `domain/contexts/workstation_management/entities/workstation.py`
- **Issues**: Business rules embedded in entity update methods
- **Business Rules Identified**:
  - Workstation configuration validation
  - Capacity calculation rules
  - Maintenance scheduling constraints
  - Safety compliance requirements

## Implementation Plan

### Phase 2.1: Create Scheduling Business Rules Services (Days 1-3)

#### Step 1: Create Schedule Validation Service
**Target Location**: `domain/contexts/scheduling/services/schedule_validation_service.py`

**Responsibilities**:
- Validate employee availability against schedule
- Check workstation capacity constraints
- Verify shift pattern compliance
- Validate break time requirements
- Check overtime regulations

**Methods to Create**:
```python
class ScheduleValidationService:
    def validate_employee_availability(self, employee: Employee, time_slot: TimeSlot) -> ValidationResult
    def validate_workstation_capacity(self, workstation: Workstation, assigned_employees: List[Employee]) -> ValidationResult
    def validate_shift_patterns(self, schedule: Schedule) -> ValidationResult
    def validate_break_requirements(self, employee_schedule: EmployeeSchedule) -> ValidationResult
    def validate_overtime_compliance(self, employee: Employee, total_hours: int) -> ValidationResult
    def validate_complete_schedule(self, schedule: Schedule) -> ScheduleValidationResult
```

#### Step 2: Create Skill Matching Service
**Target Location**: `domain/contexts/scheduling/services/skill_matching_service.py`

**Responsibilities**:
- Match employee skills to workstation requirements
- Calculate skill compatibility scores
- Identify skill gaps and surpluses
- Recommend skill-based assignments

**Methods to Create**:
```python
class SkillMatchingService:
    def calculate_skill_compatibility(self, employee: Employee, workstation: Workstation) -> SkillCompatibilityScore
    def find_best_skill_matches(self, employees: List[Employee], workstation: Workstation) -> List[SkillMatch]
    def identify_skill_gaps(self, required_skills: List[Skill], available_employees: List[Employee]) -> List[SkillGap]
    def validate_minimum_skill_requirements(self, assignment: WorkAssignment) -> ValidationResult
```

### Phase 2.2: Create Assignment Business Rules Services (Days 3-5)

#### Step 3: Create Assignment Validation Service
**Target Location**: `domain/contexts/assignment/services/assignment_validation_service.py`

**Responsibilities**:
- Validate assignment compatibility
- Check load balancing constraints
- Verify priority assignment rules
- Validate conflict resolution

**Methods to Create**:
```python
class AssignmentValidationService:
    def validate_assignment_compatibility(self, employee: Employee, workstation: Workstation) -> ValidationResult
    def validate_load_balancing(self, assignments: List[WorkAssignment]) -> ValidationResult
    def validate_priority_rules(self, assignment: WorkAssignment, existing_assignments: List[WorkAssignment]) -> ValidationResult
    def validate_conflict_resolution(self, conflicting_assignments: List[WorkAssignment]) -> ConflictResolutionResult
    def validate_performance_constraints(self, employee: Employee, workstation: Workstation) -> ValidationResult
```

#### Step 4: Create Assignment Policy Service
**Target Location**: `domain/contexts/assignment/services/assignment_policy_service.py`

**Responsibilities**:
- Apply assignment policies
- Calculate assignment scores
- Determine assignment priorities
- Handle policy conflicts

**Methods to Create**:
```python
class AssignmentPolicyService:
    def apply_assignment_policies(self, assignment: WorkAssignment, policies: List[AssignmentPolicy]) -> PolicyApplicationResult
    def calculate_assignment_score(self, employee: Employee, workstation: Workstation, criteria: AssignmentCriteria) -> AssignmentScore
    def determine_assignment_priority(self, assignment: WorkAssignment, context: AssignmentContext) -> AssignmentPriority
    def resolve_policy_conflicts(self, conflicting_policies: List[AssignmentPolicy]) -> PolicyResolutionResult
```

### Phase 2.3: Create User Management Business Rules Services (Days 5-7)

#### Step 5: Create User Validation Service
**Target Location**: `domain/contexts/user_management/services/user_validation_service.py`

**Responsibilities**:
- Validate user creation rules
- Check password policies
- Validate role assignments
- Verify account constraints

**Methods to Create**:
```python
class UserValidationService:
    def validate_user_creation(self, user_data: UserCreationData) -> ValidationResult
    def validate_password_policy(self, password: str, user: User) -> PasswordValidationResult
    def validate_role_assignment(self, user: User, roles: List[Role]) -> RoleValidationResult
    def validate_account_constraints(self, user: User) -> AccountValidationResult
    def validate_username_uniqueness(self, username: str) -> ValidationResult
```

#### Step 6: Create API Key Policy Service
**Target Location**: `domain/contexts/user_management/services/api_key_policy_service.py`

**Responsibilities**:
- Apply API key generation policies
- Validate API key constraints
- Check scope assignments
- Manage key lifecycle policies

**Methods to Create**:
```python
class ApiKeyPolicyService:
    def validate_api_key_generation(self, user: User, key_request: ApiKeyRequest) -> ValidationResult
    def apply_scope_policies(self, user: User, requested_scopes: List[str]) -> ScopePolicyResult
    def validate_key_constraints(self, api_key: ApiKey, constraints: ApiKeyConstraints) -> ValidationResult
    def check_key_lifecycle_policies(self, api_key: ApiKey) -> LifecyclePolicyResult
```

### Phase 2.4: Create Workstation Business Rules Services (Days 7-8)

#### Step 7: Create Workstation Validation Service
**Target Location**: `domain/contexts/workstation_management/services/workstation_validation_service.py`

**Responsibilities**:
- Validate workstation configuration
- Check capacity calculations
- Verify safety compliance
- Validate maintenance constraints

**Methods to Create**:
```python
class WorkstationValidationService:
    def validate_workstation_configuration(self, workstation: Workstation) -> ValidationResult
    def validate_capacity_calculation(self, workstation: Workstation, capacity_data: CapacityData) -> ValidationResult
    def validate_safety_compliance(self, workstation: Workstation, safety_requirements: SafetyRequirements) -> ValidationResult
    def validate_maintenance_constraints(self, workstation: Workstation, maintenance_schedule: MaintenanceSchedule) -> ValidationResult
```

### Phase 2.5: Create Supporting Value Objects and Specifications (Days 8-10)

#### Step 8: Create Validation Result Value Objects
**Target Locations**:
- `domain/contexts/shared/value_objects/validation_result.py`
- `domain/contexts/shared/value_objects/business_rule_violation.py`

**Value Objects to Create**:
```python
@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    violations: List[BusinessRuleViolation]
    warnings: List[BusinessRuleWarning]
    context: Optional[ValidationContext]

@dataclass(frozen=True)
class BusinessRuleViolation:
    rule_name: str
    violation_type: ViolationType
    message: str
    severity: Severity
    affected_entity: str
    suggested_action: Optional[str]
```

#### Step 9: Implement Specification Pattern
**Target Location**: `domain/contexts/shared/specifications/`

**Specifications to Create**:
```python
class EmployeeAvailabilitySpecification(Specification[Employee]):
    def is_satisfied_by(self, employee: Employee, time_slot: TimeSlot) -> bool

class WorkstationCapacitySpecification(Specification[Workstation]):
    def is_satisfied_by(self, workstation: Workstation, employee_count: int) -> bool

class SkillRequirementSpecification(Specification[WorkAssignment]):
    def is_satisfied_by(self, assignment: WorkAssignment) -> bool
```

### Phase 2.6: Integration and Refactoring (Days 10-12)

#### Step 10: Refactor Existing Services
**Targets**:
- `domain/contexts/scheduling/services/schedule_generation_service.py`
- `domain/contexts/assignment/services/assignment_optimization_service.py`
- `domain/contexts/user_management/services/user_service.py`

**Changes**:
- Extract business rules to dedicated validation services
- Keep orchestration logic in existing services
- Delegate validation to business rule services
- Simplify complex methods by separating concerns

#### Step 11: Update Application Services
**Target**: Application layer services

**Changes**:
- Use business rule services for validation
- Separate command validation from command execution
- Implement proper error handling for business rule violations
- Add comprehensive logging for business rule applications

## Success Criteria

### Technical Validation
- [ ] All complex business rules extracted to dedicated domain services
- [ ] Business rule services are pure domain logic without infrastructure dependencies
- [ ] Proper value objects created for validation results and business rule violations
- [ ] Specification pattern implemented for complex business rules
- [ ] Existing services refactored to use business rule services
- [ ] All business rules are unit testable in isolation
- [ ] Comprehensive test coverage for all business rule services

### Business Validation
- [ ] Business rules are clearly documented and traceable
- [ ] Business stakeholders can understand and validate rule implementations
- [ ] Rules are consistent across all bounded contexts
- [ ] Rule violations provide clear, actionable feedback
- [ ] Business rules can be modified without affecting technical implementation

### Architectural Validation
- [ ] Clear separation between business rules and orchestration logic
- [ ] Business rules are reusable across different application scenarios
- [ ] Proper dependency injection for business rule services
- [ ] Domain events generated for significant business rule violations
- [ ] Business rules follow single responsibility principle

## Risk Mitigation

### Potential Issues
1. **Over-Engineering**: Creating too many small services for simple rules
2. **Performance Impact**: Multiple validation calls might impact performance
3. **Rule Conflicts**: Different services might have conflicting business rules
4. **Maintenance Overhead**: Too many services to maintain and coordinate

### Mitigation Strategies
1. **Rule Complexity Threshold**: Only create separate services for complex, multi-step business rules
2. **Batch Validation**: Implement batch validation methods to reduce performance impact
3. **Rule Registry**: Create a central registry to detect and resolve rule conflicts
4. **Service Consolidation**: Group related rules into cohesive services rather than creating many small ones

## Testing Strategy

### Unit Tests Required
- Individual business rule service tests with comprehensive scenarios
- Specification pattern tests with edge cases
- Value object validation tests
- Business rule violation and warning tests

### Integration Tests Required
- Cross-service business rule interaction tests
- End-to-end validation flow tests
- Performance tests for complex validation scenarios
- Business rule conflict detection tests

### Business Rule Tests Required
- Rule accuracy tests with business stakeholder validation
- Rule consistency tests across bounded contexts
- Rule evolution tests (backward compatibility)
- Rule documentation and traceability tests

## Timeline
- **Days 1-3**: Create scheduling business rules services
- **Days 3-5**: Create assignment business rules services  
- **Days 5-7**: Create user management business rules services
- **Days 7-8**: Create workstation business rules services
- **Days 8-10**: Create supporting value objects and specifications
- **Days 10-12**: Integration, refactoring, and comprehensive testing

## Dependencies
- Completion of Goal 1 (Extract Domain Services from Infrastructure)
- Proper bounded context structure from Week 1-2
- Domain event infrastructure
- Specification pattern implementation
- Comprehensive test infrastructure

## Next Steps
After completing this goal, proceed to:
1. Goal 3: Implement aggregate roots with proper invariant enforcement
2. Begin Phase 2: Application Layer Restructuring
3. Implement cross-cutting concerns for business rule auditing and monitoring

## Business Value
- **Consistency**: Business rules applied consistently across the system
- **Maintainability**: Business rules can be modified without affecting multiple components
- **Testability**: Business rules can be thoroughly tested in isolation
- **Traceability**: Clear mapping between business requirements and rule implementations
- **Flexibility**: New business rules can be added without major system changes