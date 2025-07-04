# Repository Cleanup - Actionable Execution Plan

## Current State Summary
✅ **Migration Progress**: Repository imports are working successfully
✅ **Test Validation**: All moved repositories can be imported from new locations
⚠️ **Remaining Work**: 13 repositories still in `domain/repositories/implementations/`

## Phase 1: Immediate Cleanup (Production Ready)

### Step 1: Remove Confirmed Duplicates ✅ SAFE TO DELETE
These repositories already exist in infrastructure and can be safely removed:

```bash
# Delete duplicates (already exist in infrastructure/repositories/)
rm domain/repositories/implementations/sqlalchemy_employee_repository.py
rm domain/repositories/implementations/sqlalchemy_user_repository.py  
rm domain/repositories/implementations/sqlalchemy_refresh_token_repository.py
```

### Step 2: Create Missing Infrastructure Directories
```bash
# Create shared directory for cross-cutting repositories
mkdir infrastructure/repositories/shared
```

### Step 3: Move Remaining Repositories by Bounded Context

#### Employee Management Context (6 repositories)
```bash
# Move to infrastructure/repositories/employee_management/
mv domain/repositories/implementations/sqlalchemy_employee_training_repository.py infrastructure/repositories/employee_management/
mv domain/repositories/implementations/sqlalchemy_employee_workstation_repository.py infrastructure/repositories/employee_management/
mv domain/repositories/implementations/sqlalchemy_employee_work_history_repository.py infrastructure/repositories/employee_management/
mv domain/repositories/implementations/sqlalchemy_department_repository.py infrastructure/repositories/employee_management/
mv domain/repositories/implementations/sqlalchemy_group_repository.py infrastructure/repositories/employee_management/
mv domain/repositories/implementations/sqlalchemy_team_repository.py infrastructure/repositories/employee_management/
```

#### Assignment Context (1 repository)
```bash
# Move to infrastructure/repositories/assignment/
mv domain/repositories/implementations/sqlalchemy_team_aro_repository.py infrastructure/repositories/assignment/
```

#### Workstation Management Context (1 repository)
```bash
# Move to infrastructure/repositories/workstation_management/
mv domain/repositories/implementations/sqlalchemy_line_type_repository.py infrastructure/repositories/workstation_management/
```

#### User Management Context (1 repository)
```bash
# Move to infrastructure/repositories/user_management/
mv domain/repositories/implementations/sqlalchemy_role_repository.py infrastructure/repositories/user_management/
```

#### Shared Context (1 repository)
```bash
# Move to infrastructure/repositories/shared/
mv domain/repositories/implementations/file_seed_data_repository.py infrastructure/repositories/shared/
```

### Step 4: Update Import Statements

#### Files that need import updates:
- `infrastructure/api/dependencies.py`
- `domain/repositories/implementations/__init__.py`
- Application command handlers
- Application query handlers
- Any other files importing these repositories

### Step 5: Validation Testing
```bash
# Run the existing test
python test_reorganization.py

# Run application tests
python -m pytest tests/ -v

# Test dependency injection
python -c "from infrastructure.api.dependencies import *; print('Dependencies OK')"
```

## Phase 2: Import Path Updates

### Critical Files to Update:
1. **infrastructure/api/dependencies.py** - Update all repository imports
2. **domain/repositories/implementations/__init__.py** - Remove moved repositories
3. **Application layer** - Update command/query handler imports
4. **Main application files** - Update any direct imports

## Phase 3: Final Validation

### Production Readiness Checklist:
- [ ] All repository imports working
- [ ] Dependency injection functioning
- [ ] Application starts without errors
- [ ] Basic functionality tests pass
- [ ] No broken imports in codebase

## Execution Strategy

### Approach: Incremental with Rollback Safety
1. **Commit current working state first** (as backup)
2. **Execute Step 1** (remove duplicates) - Test - Commit
3. **Execute Step 2** (create directories) - Test - Commit  
4. **Execute Step 3** (move repositories) - Test - Commit
5. **Execute Step 4** (update imports) - Test - Commit
6. **Final validation** - Test - Commit

### Risk Mitigation:
- Each step is committed separately for easy rollback
- Test after each major change
- Keep production dependencies working at all times
- Use git stash if needed for quick rollbacks

## Expected Outcome:
- Clean bounded context organization
- All repositories in proper infrastructure locations
- No duplicate code
- Production-ready codebase
- Improved maintainability and separation of concerns