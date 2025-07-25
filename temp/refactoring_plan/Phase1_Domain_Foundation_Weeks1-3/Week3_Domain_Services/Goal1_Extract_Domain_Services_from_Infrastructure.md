# Goal 1: Extract Domain Services from Infrastructure

## Objective
Move domain logic currently residing in the infrastructure layer to proper domain services, ensuring clean separation of concerns and adherence to DDD principles.

## Current State Analysis

### Critical Issues Identified
1. **Authentication Logic in Infrastructure**: `infrastructure/security/api_key.py` contains business rules for API key validation, IP restrictions, user agent validation, and scope checking
2. **Mixed Responsibilities**: Infrastructure components are making domain decisions about user authentication and authorization
3. **Dependency Direction Violation**: Infrastructure layer is orchestrating domain logic instead of just providing technical capabilities

### Files Requiring Refactoring
- `infrastructure/security/api_key.py` (147 lines) - Contains domain logic that should be extracted
- Potential other infrastructure files with domain logic (to be identified during implementation)

## Implementation Plan

### Phase 1.1: Create Authentication Domain Service (Days 1-2)

#### Step 1: Create Authentication Domain Service
**Target Location**: `domain/contexts/user_management/services/authentication_service.py`

**Responsibilities**:
- API key validation logic
- User authentication through API keys
- Authentication result creation
- Authentication logging (domain events)

**Methods to Extract**:
```python
class AuthenticationService:
    def authenticate_with_api_key(self, api_key: str, client_ip: str, user_agent: str) -> AuthenticationResult
    def validate_api_key_constraints(self, api_key: ApiKey, client_ip: str, user_agent: str) -> bool
    def create_authentication_context(self, user: User, api_key: ApiKey) -> AuthenticationContext
```

#### Step 2: Create Authorization Domain Service  
**Target Location**: `domain/contexts/user_management/services/authorization_service.py`

**Responsibilities**:
- Scope validation logic
- Permission checking
- Authorization decisions
- Authorization logging (domain events)

**Methods to Extract**:
```python
class AuthorizationService:
    def validate_scope(self, api_key: ApiKey, required_scope: str) -> bool
    def check_permissions(self, user: User, resource: str, action: str) -> bool
    def create_authorization_context(self, user: User, permissions: List[str]) -> AuthorizationContext
```

### Phase 1.2: Create Supporting Value Objects (Days 2-3)

#### Step 3: Create Authentication Result Value Object
**Target Location**: `domain/contexts/user_management/value_objects/authentication_result.py`

```python
@dataclass(frozen=True)
class AuthenticationResult:
    is_authenticated: bool
    user: Optional[User]
    api_key: Optional[ApiKey]
    failure_reason: Optional[str]
    authentication_context: Optional[AuthenticationContext]
```

#### Step 4: Create Authentication Context Value Object
**Target Location**: `domain/contexts/user_management/value_objects/authentication_context.py`

```python
@dataclass(frozen=True)
class AuthenticationContext:
    user_id: int
    username: str
    roles: List[str]
    api_key_id: Optional[int]
    client_ip: str
    user_agent: str
    authenticated_at: datetime
    is_api_client: bool
```

### Phase 1.3: Update Infrastructure Layer (Days 3-4)

#### Step 5: Refactor Infrastructure Security Module
**Target**: `infrastructure/security/api_key.py`

**Changes**:
- Remove domain logic
- Keep only FastAPI dependency injection and HTTP concerns
- Delegate to domain services for business decisions
- Transform domain results to HTTP responses

**New Structure**:
```python
async def get_api_key(
    request: Request,
    api_key: Optional[str] = Depends(API_KEY_HEADER),
    authentication_service: AuthenticationService = Depends(get_authentication_service)
) -> Optional[Dict]:
    if not api_key:
        return None
    
    # Get client information (infrastructure concern)
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Delegate to domain service
    auth_result = authentication_service.authenticate_with_api_key(
        api_key, client_ip, user_agent
    )
    
    if not auth_result.is_authenticated:
        return None
    
    # Store context in request state (infrastructure concern)
    request.state.authentication_context = auth_result.authentication_context
    
    return {
        "username": auth_result.user.username,
        "roles": auth_result.user.roles
    }
```

### Phase 1.4: Create Domain Events (Days 4-5)

#### Step 6: Create Authentication Domain Events
**Target Locations**:
- `domain/contexts/user_management/events/user_authenticated.py`
- `domain/contexts/user_management/events/authentication_failed.py`
- `domain/contexts/user_management/events/authorization_failed.py`

**Events to Create**:
```python
@dataclass
class UserAuthenticated(DomainEvent):
    user_id: int
    username: str
    authentication_method: str
    client_ip: str
    user_agent: str
    authenticated_at: datetime

@dataclass  
class AuthenticationFailed(DomainEvent):
    api_key_prefix: str
    failure_reason: str
    client_ip: str
    attempted_at: datetime

@dataclass
class AuthorizationFailed(DomainEvent):
    user_id: int
    required_scope: str
    available_scopes: List[str]
    resource: str
    attempted_at: datetime
```

### Phase 1.5: Update Dependency Injection (Day 5)

#### Step 7: Register New Domain Services
**Target**: `infrastructure/api/dependencies.py`

**Add**:
```python
def get_authentication_service() -> AuthenticationService:
    return AuthenticationService(
        api_key_repository=get_api_key_repository(),
        user_service=get_user_service(),
        event_dispatcher=get_event_dispatcher()
    )

def get_authorization_service() -> AuthorizationService:
    return AuthorizationService(
        event_dispatcher=get_event_dispatcher()
    )
```

## Success Criteria

### Technical Validation
- [ ] All domain logic removed from `infrastructure/security/api_key.py`
- [ ] Authentication logic properly encapsulated in `AuthenticationService`
- [ ] Authorization logic properly encapsulated in `AuthorizationService`
- [ ] Proper value objects created for authentication results and contexts
- [ ] Domain events implemented for authentication and authorization activities
- [ ] Infrastructure layer only handles HTTP concerns and dependency injection
- [ ] All existing tests pass
- [ ] New unit tests created for domain services

### Architectural Validation
- [ ] Dependencies flow inward (infrastructure → application → domain)
- [ ] Domain services are pure business logic without infrastructure concerns
- [ ] Infrastructure components delegate business decisions to domain services
- [ ] Proper separation between technical concerns and business rules
- [ ] Domain events properly capture business-significant activities

## Risk Mitigation

### Potential Issues
1. **Breaking Changes**: Existing API contracts might be affected
2. **Performance Impact**: Additional abstraction layers might impact performance
3. **Complex Dependencies**: Domain services might have complex dependency graphs

### Mitigation Strategies
1. **Incremental Migration**: Implement new services alongside existing code, then gradually migrate
2. **Comprehensive Testing**: Create extensive unit and integration tests before refactoring
3. **Performance Monitoring**: Benchmark before and after refactoring
4. **Rollback Plan**: Keep original infrastructure code until migration is fully validated

## Testing Strategy

### Unit Tests Required
- `AuthenticationService` unit tests with mocked dependencies
- `AuthorizationService` unit tests with mocked dependencies
- Value object validation tests
- Domain event creation and handling tests

### Integration Tests Required
- End-to-end API authentication flow tests
- Authorization flow tests with various scopes
- Error handling and edge case tests
- Performance regression tests

## Timeline
- **Day 1**: Create AuthenticationService and basic structure
- **Day 2**: Create AuthorizationService and value objects
- **Day 3**: Refactor infrastructure layer to use domain services
- **Day 4**: Implement domain events and event handling
- **Day 5**: Update dependency injection and comprehensive testing

## Dependencies
- Completion of Week 1-2 bounded context restructuring
- Domain event infrastructure must be in place
- Repository interfaces must be properly defined
- Dependency injection container must be configured

## Next Steps
After completing this goal, proceed to:
1. Goal 2: Create proper domain services for business rules validation
2. Goal 3: Implement aggregate roots with proper invariant enforcement