from typing import Dict, List, Optional
from domain.entities.department import Department
from domain.repositories.interfaces.department_repository import DepartmentRepositoryInterface


class MockDepartmentRepository(DepartmentRepositoryInterface):
    def __init__(self):
        self.departments: Dict[int, Department] = {}
        self.next_id = 1

    def add(self, entity: Department) -> Department:
        if entity.id is None or entity.id == 0:
            entity.id = self.next_id
            self.next_id += 1
        self.departments[entity.id] = entity
        return entity

    def get(self, id: int) -> Optional[Department]:
        return self.departments.get(id)

    def get_all(self) -> List[Department]:
        return list(self.departments.values())

    def update(self, entity: Department) -> Department:
        if entity.id not in self.departments:
            raise ValueError(f"Department with id {entity.id} not found")
        self.departments[entity.id] = entity
        return entity

    def delete(self, id: int) -> bool:
        if id not in self.departments:
            return False
        del self.departments[id]
        return True

    def get_by_name(self, department_name: str) -> Optional[Department]:
        for department in self.departments.values():
            if department.name == department_name:
                return department
        return None

    def get_all_with_groups(self) -> List[Department]:
        return list(self.departments.values())