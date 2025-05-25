# Cache Invalidation System

## Overview

The cache invalidation system in the Heijunka project provides an event-driven mechanism to selectively invalidate portions of the cache when domain events occur. This ensures that the cache remains consistent with the underlying data while avoiding unnecessary cache rebuilding.

## Components

### CacheInvalidationHandler

The `CacheInvalidationHandler` class is responsible for handling domain events and invalidating the relevant portions of the cache. It listens for events such as ARO assignments, team member changes, workstation changes, and qualification changes, and selectively invalidates the affected cache entries.

```python
from domain.services.cache_invalidation_handler import CacheInvalidationHandler

# Create the handler
cache_invalidation_handler = CacheInvalidationHandler(aro_graph_service)

# Register event handlers
aro_service.register_event_handler('aro_assignment_created', cache_invalidation_handler.handle_aro_assignment_created)
aro_service.register_event_handler('aro_assignment_removed', cache_invalidation_handler.handle_aro_assignment_removed)
aro_service.register_event_handler('aro_assignment_updated', cache_invalidation_handler.handle_aro_assignment_updated)
```

### Event Handlers

The `CacheInvalidationHandler` provides the following event handlers:

- `handle_aro_assignment_created`: Invalidates the graph cache for the specific date and period, and the edge cost cache for the specific teams involved
- `handle_aro_assignment_removed`: Invalidates the graph cache for the specific date and period, and the edge cost cache for the specific teams involved
- `handle_aro_assignment_updated`: Invalidates the graph cache for the specific date and period, and the edge cost cache for the specific teams involved
- `handle_team_member_added`: Invalidates all graph caches for the specific team
- `handle_team_member_removed`: Invalidates all graph caches for the specific team
- `handle_workstation_added_to_team`: Invalidates all graph caches for the specific team
- `handle_workstation_removed_from_team`: Invalidates all graph caches for the specific team
- `handle_qualification_added`: Invalidates all graph caches
- `handle_qualification_removed`: Invalidates all graph caches

### Selective Cache Invalidation

The cache invalidation system is designed to be efficient by only invalidating the parts of the cache that are affected by each event, rather than clearing the entire cache. For example:

- For ARO assignment events, it only invalidates the graph cache for the specific date and period, and the edge cost cache for the specific teams involved
- For team member and workstation events, it invalidates the graph cache for the specific team
- For qualification events, it invalidates all graph caches since we don't know which teams might be affected

### Logging

The cache invalidation system includes detailed logging to help with monitoring and tuning the cache. Each cache eviction is logged with information about the event that triggered it, which can be used to analyze cache usage patterns and optimize the cache invalidation strategy.

## Benefits

- **Improved Performance**: By selectively invalidating only the affected portions of the cache, the system reduces unnecessary cache rebuilding and improves performance.
- **Data Consistency**: The event-driven approach ensures that the cache remains consistent with the underlying data.
- **Monitoring and Tuning**: The detailed logging provides insights into cache usage patterns, which can be used to optimize the cache invalidation strategy.

## Example

```python
# When an ARO assignment is created
event = AROAssignmentCreated(
    employee_id=1,
    from_team_id=1,
    to_team_id=2,
    assignment_date=date(2024, 6, 1),
    period=3
)

# The cache invalidation handler will:
# 1. Invalidate the graph cache for the specific date and period
# 2. Invalidate the edge cost cache for the specific teams involved
# 3. Log the cache eviction
cache_invalidation_handler.handle_aro_assignment_created(event)
```