import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from domain.contexts.employee_management.entities.employee import Employee
from domain.contexts.workstation_management.entities.workstation import Workstation
from domain.contexts.employee_management.value_objects.work_history_entry import WorkHistoryEntry
from domain.contexts.employee_management.services.employee_service import EmployeeService
from domain.events.publisher import DomainEventPublisher
from domain.events.employee import WorkHistoryEntryAdded


class TestEmployeeService(unittest.TestCase):
    def setUp(self):
        # Create mock repositories
        self.employee_repository = MagicMock()
        self.work_history_repository = MagicMock()
        self.event_publisher = MagicMock(spec=DomainEventPublisher)
        
        # Create the service
        self.employee_service = EmployeeService(
            employee_repository=self.employee_repository,
            work_history_repository=self.work_history_repository,
            event_publisher=self.event_publisher
        )
        
        # Create test data
        self.employee = Employee(id=1, name="Test Employee", team_id=1, is_active=True)
        self.workstation = Workstation(id=1, name="Test Workstation", line_type="test", team_id=1)
        self.test_date = date(2024, 6, 1)
        self.test_period = 3
        
        # Set up repository returns
        self.employee_repository.get.return_value = self.employee
    
    def test_get_employee_history(self):
        # Set up repository to return test data
        test_entries = [
            WorkHistoryEntry(
                employee_id=1,
                workstation_id=1,
                worked_date=self.test_date,
                work_period=self.test_period
            )
        ]
        self.work_history_repository.get_by_employee_date_range.return_value = test_entries
        
        # Call the service
        result = self.employee_service.get_employee_history(
            employee_id=1,
            start_date=self.test_date,
            end_date=self.test_date
        )
        
        # Check result
        self.assertEqual(result, test_entries)
        
        # Verify repository calls
        self.work_history_repository.get_by_employee_date_range.assert_called_once_with(
            employee_id=1,
            start_date=self.test_date,
            end_date=self.test_date
        )
    
    def test_record_work_session(self):
        # Set up employee to return a domain event
        self.employee.add_work_history_entry = MagicMock()
        self.employee.domain_events = [WorkHistoryEntryAdded(
            employee_id=1,
            workstation_id=1,
            work_date=self.test_date,
            period=self.test_period
        )]
        self.employee.clear_domain_events = MagicMock()
        
        # Call the service
        result = self.employee_service.record_work_session(
            employee_id=1,
            workstation_id=1,
            worked_date=self.test_date,
            work_period=self.test_period
        )
        
        # Check result
        self.assertTrue(result)
        
        # Verify repository calls
        self.employee_repository.get.assert_called_once_with(1)
        self.employee.add_work_history_entry.assert_called_once_with(1, self.test_date, self.test_period)
        self.employee_repository.update.assert_called_once_with(self.employee)
        self.work_history_repository.add.assert_called_once()
        
        # Verify event publishing
        self.event_publisher.publish.assert_called_once()
        self.employee.clear_domain_events.assert_called_once()
    
    def test_record_work_session_employee_not_found(self):
        # Set up repository to return None
        self.employee_repository.get.return_value = None
        
        # Call the service
        result = self.employee_service.record_work_session(
            employee_id=1,
            workstation_id=1,
            worked_date=self.test_date,
            work_period=self.test_period
        )
        
        # Check result
        self.assertFalse(result)
        
        # Verify repository calls
        self.employee_repository.get.assert_called_once_with(1)
        self.employee_repository.update.assert_not_called()
        self.work_history_repository.add.assert_not_called()
        self.event_publisher.publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()