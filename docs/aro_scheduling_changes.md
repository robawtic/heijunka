# ARO Scheduling Changes

## Overview

This document describes the changes made to the Heijunka scheduling system to improve the handling of ARO (Assigned Relief Operator) employees. The changes address the following requirements:

1. Employees with ARO status should be considered available, not unavailable
2. ARO employees should be discouraged (but not forbidden) from being reassigned
3. Availability status should be checked for each period, not just the entire day

## Changes Made

### 1. Employee Availability Logic

**File:** `domain/entities/employee.py`

The `is_available_for_period` method was updated to consider ARO employees as available. Previously, employees with ARO status were treated as unavailable, but now they are considered available.

```python
# Before
if av.status in (AvailabilityStatus.CALL_IN, AvailabilityStatus.ARO):
    return False

# After
if av.status == AvailabilityStatus.CALL_IN:
    return False
    
# Track if employee is an ARO
if av.status == AvailabilityStatus.ARO:
    is_aro = True
```

### 2. Schedule Generation Logic

**File:** `domain/entities/schedule.py`

The schedule generation logic was updated to include ARO employees in the count of available employees. Previously, ARO employees were filtered out when checking if there were enough employees to cover all workstations.

```python
# Before
non_aro_employees = [e for e in employees if not any(
    av.status == AvailabilityStatus.ARO 
    for av in e.available_periods 
    if av.date == self.start_date
)]

if len(non_aro_employees) < len(workstations):
    # Not enough employees...

# After
aro_employees = [e for e in employees if any(
    av.status == AvailabilityStatus.ARO 
    for av in e.available_periods 
    if av.date == self.start_date
)]
available_employees = len(employees)
aro_count = len(aro_employees)

if available_employees < len(workstations):
    # Not enough employees...
```

### 3. ARO Reassignment Penalty

**File:** `domain/rules/soft.py`

A new soft rule was added to discourage (but not forbid) reassigning ARO employees. This rule adds a high penalty to assignments of employees who are already assigned as AROs.

```python
@rule_metadata(uses=["model", "assign", "employees", "workstations", "periods", "start_date"])
def add_aro_reassignment_penalties(ctx: RuleContext):
    """
    Penalize reassigning employees who are already assigned as AROs.
    
    This rule discourages (but doesn't forbid) reassigning ARO employees
    by adding a high penalty to their assignments.
    """
    # ... implementation ...
```

### 4. Rule Registry Update

**File:** `domain/rules/registry.py`

The new soft rule was added to the registry to ensure it's applied during schedule generation.

```python
COMMON_SOFT_RULES = [
    add_same_day_repeat_penalties,
    add_lookback_any_period_penalties,
    add_lookback_same_period_penalties,
    add_aro_reassignment_penalties,  # New rule
    # ...add more
]
```

## Testing

A test script (`test_aro_scheduling.py`) was created to verify the changes with live data. The script runs the `generate` command with the `--department powertrain` option and includes some call-ins to test the ARO scheduling logic.

## Edge Cases Handled

1. **Multiple ARO Employees:** The system now correctly counts all ARO employees as available, regardless of how many there are.
2. **Period-Specific Availability:** The system already checked availability for each period, not just the entire day, so no changes were needed for this requirement.
3. **ARO Reassignment:** The new soft rule ensures that ARO employees are discouraged from being reassigned, but it doesn't forbid it if necessary.

## Conclusion

These changes improve the handling of ARO employees in the scheduling system by:
1. Considering ARO employees as available
2. Discouraging (but not forbidding) reassigning ARO employees
3. Ensuring availability is checked for each period

The changes follow Domain-Driven Design principles and maintain the existing architecture of the system.