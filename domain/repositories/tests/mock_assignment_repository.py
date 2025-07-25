from typing import Optional, List
from domain.contexts.assignment.value_objects.work_assignment import WorkAssignment
from domain.repositories.interfaces.assignment_repository import AssignmentRepositoryInterface


class MockAssignmentRepository(AssignmentRepositoryInterface):
    """
    Mock implementation of the assignment repository for testing.
    """

    def __init__(self):
        self.assignments = {}
        self.next_id = 1

    def get_by_id(self, entity_id: int) -> Optional[WorkAssignment]:
        """Retrieve an assignment by ID."""
        return self.assignments.get(entity_id)

    def list_all(self) -> List[WorkAssignment]:
        """Retrieve all assignments."""
        return list(self.assignments.values())

    def add(self, entity: WorkAssignment) -> WorkAssignment:
        """Add a new assignment."""
        entity_id = self.next_id
        self.next_id += 1
        self.assignments[entity_id] = entity
        return entity

    def update(self, entity: WorkAssignment) -> WorkAssignment:
        """Update an existing assignment."""
        return self.add(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete an assignment by ID."""
        if entity_id in self.assignments:
            del self.assignments[entity_id]
            return True
        return False

    def save_all(self, assignments: List[WorkAssignment]) -> bool:
        """Save a list of work assignments."""
        try:
            for assignment in assignments:
                self.add(assignment)
            return True
        except Exception:
            return False

    def get_by_employee_id(self, employee_id: int) -> List[WorkAssignment]:
        """Retrieve all assignments for a specific employee."""
        return [a for a in self.assignments.values() if a.employee.id == employee_id]

    def get_by_workstation_id(self, workstation_id: int) -> List[WorkAssignment]:
        """Retrieve all assignments for a specific workstation."""
        return [a for a in self.assignments.values() if a.workstation.id == workstation_id]