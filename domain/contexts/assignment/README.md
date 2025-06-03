# AROAssignment Documentation

## Canonical Location

The canonical implementation of `AROAssignment` is located in:
```
domain/contexts/assignment/aro_assignment.py
```

## Deprecated Location

The legacy implementation in `domain/value_objects/aro_assignment.py` is now deprecated and forwards to the canonical implementation. It issues a deprecation warning when imported.

## Usage

Always import `AROAssignment` from the canonical location:

```python
from domain.contexts.assignment.aro_assignment import AROAssignment
```

## Implementation Details

The canonical `AROAssignment` is a full aggregate root with domain events, while the deprecated version was a simple value object. The canonical version includes:

1. Domain events for creation, removal, and updates
2. Methods for creating, updating, and removing assignments
3. Validation logic

## Migration

If you're updating code that uses the deprecated implementation, make sure to:

1. Update import statements to use the canonical path
2. Provide the required `id` parameter when creating instances
3. Consider using the `create()` factory method instead of direct instantiation