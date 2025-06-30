# Domain-Driven Design Refactoring for Schedule Generation

## Overview

This document outlines the refactoring changes made to align the schedule generation flow with Domain-Driven Design (DDD) principles. The primary goal was to ensure the domain layer is persistence-agnostic and all persistence logic is handled in the application layer.

## Key Changes

### Domain Layer Changes

1. **ScheduleService**
   - Removed repository dependencies from method signatures
   - Created a new `_create_schedule_entity` method that doesn't interact with repositories
   - Refactored `generate_schedule` to return domain objects (assignments and metadata) without saving them
   - Refactored `generate_period_schedule` to accept work history data directly instead of a repository
   - Created a new `generate_schedule_flow` method that doesn't depend on repositories
   - Kept legacy methods with `_legacy` suffix for backward compatibility

2. **CPModelBuilder**
   - Updated `solve_one_period` and `build_model` to accept work history data directly instead of a repository
   - Added backward compatibility for repository-based approach

### Application Layer Changes

1. **GenerateScheduleHandler**
   - Updated methods to use the refactored domain services
   - Added helper methods for fetching and saving data:
     - `_fetch_work_history_data`: Fetches work history data from the repository
     - `_save_schedule`: Saves schedule metadata to the repository
     - `_save_work_history`: Creates and saves work history entries
   - Moved all persistence logic to the application layer

## New Flow

### Application Layer (GenerateScheduleHandler)
1. Fetch data with repositories (employees, workstations, work history)
2. Call domain service for schedule generation:  
   `assignments, metadata = schedule_service.generate_schedule(...)`
3. Save schedule metadata:  
   `_save_schedule(metadata)`
4. Save work history:  
   `_save_work_history(assignments, start_date)`
5. Save assignments:  
   `assignment_repository.save_all(assignments)`
6. Return result

### Domain Layer (ScheduleService)
- Pure business logic, no persistence
- Returns domain objects (assignments and metadata)

## Benefits

1. **Cleaner Domain Layer**: The domain layer now focuses solely on business logic without persistence concerns.
2. **Better Testability**: Domain services can be tested in isolation without mocking repositories.
3. **Improved Separation of Concerns**: Clear distinction between domain logic and persistence operations.
4. **Flexibility**: The application layer can decide when and how to persist data.

## Backward Compatibility

Legacy methods have been preserved with `_legacy` suffix to ensure backward compatibility while encouraging the use of the new methods.