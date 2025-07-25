1. Bounded Context Directory Migration
Goal: Ensure every business capability (“bounded context”) has its own clear section in the application layer, so logic, data structures, and use cases are truly independent and testable.

1.1. Identify and create directories for each bounded context
What to do:
For each main business domain (assignment, schedule, employee, etc.), create a folder under application/.

Why:
This prevents context leakage, accidental coupling, and confusion over “who owns what.”

How:
E.g., application/assignment_management/, application/schedule_management/, etc.

1.2. For each context, create subfolders for CQRS/DDD artifacts
What to do:
Add at minimum:

commands/ (actions that change state)

handlers/ (application service logic to handle commands/queries)

queries/ (read-side logic)

services/ (orchestrators or app-specific services, NOT domain services)

interfaces/ (for context-specific abstractions)

exceptions/ (context-specific error types)

Why:
This gives a clean separation of command/query logic, makes refactoring easy, and enforces one place for related business logic.

How:
E.g.:

bash
Copy
Edit
application/schedule_management/
  commands/
    generate_schedule_command.py
  handlers/
    generate_schedule_handler.py
  queries/
    get_schedule_query.py
  services/
  interfaces/
  exceptions/
1.3. Move all relevant files from global folders into new per-context locations
What to do:
Move any file that represents a use case, handler, or service to its context’s folder (based on business responsibility).

Why:
Having logic scattered in global folders creates tight coupling and code ambiguity.

How:
Example:

application/commands/generate_schedule_command.py → application/schedule_management/commands/generate_schedule_command.py

application/commands/create_manual_assignment_command.py → application/assignment_management/commands/create_manual_assignment_command.py

1.4. Move and group tests by context
What to do:
If tests exist, move them to application/<context>/tests/ or a mirrored location in /tests/.

Why:
Test code should evolve with the context it covers and help catch accidental coupling.

2. Eliminate Global and Shared Directories
Goal: Remove ambiguous, over-shared directories in favor of context isolation. Minimize cross-context dependencies.

2.1. Delete or empty global commands/, queries/, and services/ directories
What to do:
After migration, remove empty global directories. Ensure no business logic is left there.

Why:
Enforces context boundaries; prevents regression.

How:
rm -rf application/commands/, etc.

2.2. Review and empty the shared/ directory
What to do:
Carefully audit application/shared/ for what is truly cross-cutting vs. what’s miscategorized.

Why:
Shared is often a dumping ground—most files should be context-specific or infra.

How:

Move cross-cutting marker interfaces (if truly needed) to a new shared_kernel/ directory (application layer).

Move bus, middleware, or pipeline implementations to infrastructure (see next section).

Move DTOs/exceptions used by only one context into that context.

Delete or refactor the rest.

3. Move Bus, Pipeline, and Middleware Implementations to Infrastructure
Goal: Keep technical “plumbing” out of the business-facing application layer. Application code should depend on interfaces only.

3.1. Create infrastructure/messaging/ for CQRS bus and middleware implementations
What to do:
In the infrastructure layer, add a messaging/ folder for technical routing logic.

Why:
Command, query, and event bus implementations are infrastructure concerns (transport, logging, etc.).

How:
Example:

bash
Copy
Edit
infrastructure/messaging/
  command_bus.py
  query_bus.py
  event_bus.py
  pipeline.py
3.2. Move all bus and middleware/pipeline implementations
What to do:
Move concrete classes (not interfaces) from application/shared/ to infrastructure/messaging/.

Why:
Application shouldn’t “know” how messages are routed—just that routing exists.

How:
Example:

application/shared/command_bus.py → infrastructure/messaging/command_bus.py

application/shared/behaviors/behavior_pipeline.py → infrastructure/messaging/behavior_pipeline.py

3.3. Move or create only minimal marker interfaces in shared_kernel/ (if needed)
What to do:
If application code needs to reference an abstract bus, put only the base interface or protocol in shared_kernel/.

Why:
Interfaces are application’s contract with infrastructure; keeps dependencies flowing the right direction.

How:

application/shared/command_bus_interface.py → application/shared_kernel/command_bus_interface.py

4. Separate Infrastructure-Only Concerns
Goal: Move setup, data seeding, and other “operations” logic out of business logic layers.

4.1. Move seed and setup commands to infrastructure/commands/
What to do:
Files like seed_database_command.py belong in infrastructure.

Why:
Seeding is not a use case; it’s a deployment/ops task.

How:

application/commands/seed_database_command.py → infrastructure/commands/seed_database_command.py

4.2. Audit application layer for any lingering technical concerns
What to do:
Look for anything that’s about DB setup, message bus wiring, integrations, etc.

How:
Move those to infrastructure.

5. Refactor DTOs and Exceptions
Goal: Minimize sharing to avoid coupling. Prefer context-local data structures.

5.1. Move DTOs to per-context folders
What to do:

DTOs used by only one context: move to application/<context>/dto/.

DTOs genuinely used by >1 context: move to application/shared_kernel/dto/.

Why:
Most DTOs are context-specific. Shared DTOs are usually a sign of coupling, but can be justified for authentication, etc.

5.2. Move exceptions to per-context folders
What to do:

Context-specific exceptions → application/<context>/exceptions/.

Rare base exceptions (e.g., ApplicationError) → application/shared_kernel/exceptions.py.

6. Update All Imports, Tests, and References
Goal: Maintain working code and tests after refactor. Prevent broken imports and regressions.

6.1. Update all code imports to new file paths
What to do:
Replace any from application.commands... with new per-context path.

6.2. Update all test imports and helpers
What to do:
Ensure test files import from the new structure.

6.3. Move tests into context-matching folders for best isolation
How:
E.g., application/schedule_management/tests/test_generate_schedule.py

6.4. Run the full test suite and fix all import/path issues
7. Documentation & Process Enforcement
Goal: Institutionalize new structure so the codebase stays healthy as the team grows.

7.1. Update project documentation to explain the new structure
What to do:
Update README, onboarding docs, and architecture diagrams.

7.2. Add code review guidelines/checklist for DDD/CQRS compliance
What to do:
Write out simple rules:

“No global use case files”

“No direct cross-context imports except via events or shared_kernel/ interfaces”

“Infrastructure-only logic stays out of the application layer”

8. (Optional Advanced) Implement Domain Event Pattern
Goal: Enable decoupled communication between contexts without tight coupling.

8.1. Define base domain event interfaces in shared_kernel/
8.2. For each context, place event definitions and handlers in that context
8.3. Implement event dispatching infrastructure in infrastructure/messaging/
📋 Example Markdown for Tracking
markdown
Copy
Edit
# DDD/CQRS Master Refactor Checklist

## 1. Bounded Context Migration
- [ ] Identify contexts and create application/<context>/ directories
- [ ] For each, add commands/, handlers/, queries/, services/, interfaces/, exceptions/
- [ ] Move all code from global folders to correct context
- [ ] Move tests to per-context folders

## 2. Remove Shared/Global Directories
- [ ] Delete application/commands, queries, services after move
- [ ] Audit application/shared; move valid interfaces to shared_kernel/, implementations to infra, delete rest

## 3. Infrastructure Move
- [ ] Create infrastructure/messaging/
- [ ] Move all bus/pipeline implementations there
- [ ] Keep only marker interfaces in shared_kernel/

## 4. Infrastructure Concerns
- [ ] Move seed/setup logic to infrastructure/commands/

## 5. DTOs & Exceptions
- [ ] Move to per-context folders; only common ones in shared_kernel/

## 6. Update Imports & Tests
- [ ] Update all import paths, tests, helpers
- [ ] Run and fix the full test suite

## 7. Documentation & Process
- [ ] Update docs, diagrams, onboarding
- [ ] Add code review checklist

## 8. (Optional) Domain Events
- [ ] Implement domain event pattern for cross-context comms