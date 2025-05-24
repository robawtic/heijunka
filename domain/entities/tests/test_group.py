import unittest
from datetime import date

from domain.entities.group import Group
from domain.events import (
    GroupCreated, GroupUpdated, GroupPropertyChanged, GroupDepartmentChanged
)


class TestGroup(unittest.TestCase):
    def setUp(self):
        """Set up a new group for each test."""
        self.group = Group(
            id=1,
            name="Test Group",
            department_id=None
        )
        # Clear the creation event
        self.group.clear_domain_events()

    def test_initialization(self):
        """Test that a group is properly initialized."""
        group = Group(
            id=2,
            name="New Group",
            department_id=1
        )
        
        # Check properties
        self.assertEqual(group.id, 2)
        self.assertEqual(group.name, "New Group")
        self.assertEqual(group.department_id, 1)
        
        # Check that a creation event was raised
        events = group.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], GroupCreated)
        self.assertEqual(events[0].group_id, 2)
        self.assertEqual(events[0].name, "New Group")
        self.assertEqual(events[0].department_id, 1)

    def test_set_name(self):
        """Test setting the name of the group."""
        # Set the name
        result = self.group.set_name("New Name")
        self.assertTrue(result)
        self.assertEqual(self.group.name, "New Name")
        
        # Check that a domain event was raised
        events = self.group.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], GroupPropertyChanged)
        self.assertEqual(events[0].group_id, 1)
        self.assertEqual(events[0].property_name, "name")
        self.assertEqual(events[0].old_value, "Test Group")
        self.assertEqual(events[0].new_value, "New Name")
        
        # Try to set the same name again
        self.group.clear_domain_events()
        result = self.group.set_name("New Name")
        self.assertFalse(result)  # Should return False for no change
        self.assertEqual(len(self.group.domain_events), 0)  # No event should be raised
        
        # Test invalid name
        with self.assertRaises(ValueError):
            self.group.set_name("")
        with self.assertRaises(ValueError):
            self.group.set_name(None)

    def test_set_department(self):
        """Test setting the department of the group."""
        # Set the department
        result = self.group.set_department(1)
        self.assertTrue(result)
        self.assertEqual(self.group.department_id, 1)
        
        # Check that a domain event was raised
        events = self.group.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], GroupDepartmentChanged)
        self.assertEqual(events[0].group_id, 1)
        self.assertIsNone(events[0].old_department_id)
        self.assertEqual(events[0].new_department_id, 1)
        
        # Try to set the same department again
        self.group.clear_domain_events()
        result = self.group.set_department(1)
        self.assertFalse(result)  # Should return False for no change
        self.assertEqual(len(self.group.domain_events), 0)  # No event should be raised
        
        # Change to a different department
        result = self.group.set_department(2)
        self.assertTrue(result)
        self.assertEqual(self.group.department_id, 2)
        
        # Check that a domain event was raised
        events = self.group.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], GroupDepartmentChanged)
        self.assertEqual(events[0].old_department_id, 1)
        self.assertEqual(events[0].new_department_id, 2)
        
        # Unassign from department
        self.group.clear_domain_events()
        result = self.group.set_department(None)
        self.assertTrue(result)
        self.assertIsNone(self.group.department_id)
        
        # Check that a domain event was raised
        events = self.group.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], GroupDepartmentChanged)
        self.assertEqual(events[0].old_department_id, 2)
        self.assertIsNone(events[0].new_department_id)
        
        # Test invalid department ID
        with self.assertRaises(ValueError):
            self.group.set_department(0)
        with self.assertRaises(ValueError):
            self.group.set_department(-1)

    def test_update(self):
        """Test updating multiple properties at once."""
        # Update multiple properties
        self.group.update(
            name="New Name",
            department_id=1
        )
        
        # Check that properties were updated
        self.assertEqual(self.group.name, "New Name")
        self.assertEqual(self.group.department_id, 1)
        
        # Check that domain events were raised
        events = self.group.domain_events
        # Should be 3 events: 2 property changes + 1 update event
        self.assertEqual(len(events), 3)
        
        # The last event should be GroupUpdated
        self.assertIsInstance(events[-1], GroupUpdated)
        self.assertEqual(events[-1].group_id, 1)
        
        # Update with no changes
        self.group.clear_domain_events()
        self.group.update(
            name="New Name",
            department_id=1
        )
        
        # No events should be raised
        self.assertEqual(len(self.group.domain_events), 0)
        
        # Update with some changes
        self.group.update(
            name="Updated Again"
        )
        
        # Check that properties were updated
        self.assertEqual(self.group.name, "Updated Again")
        
        # Check that domain events were raised
        events = self.group.domain_events
        # Should be 2 events: 1 property change + 1 update event
        self.assertEqual(len(events), 2)
        
        # Test invalid values
        with self.assertRaises(ValueError):
            self.group.update(name="")
        with self.assertRaises(ValueError):
            self.group.update(department_id=0)

    def test_validate(self):
        """Test validating the group entity."""
        # Valid group
        self.group.validate()  # Should not raise an exception
        
        # Test validation directly without creating invalid objects
        # This avoids triggering validation in __post_init__ and GroupCreated event
        
        # Create a valid group first
        group = Group(id=2, name="Valid Name", department_id=1)
        group.clear_domain_events()
        
        # Test invalid name (empty)
        group.name = ""
        with self.assertRaises(ValueError):
            group.validate()
        
        # Reset to valid state
        group.name = "Valid Name"
        
        # Test invalid name (too long)
        group.name = "x" * 101
        with self.assertRaises(ValueError):
            group.validate()
        
        # Reset to valid state
        group.name = "Valid Name"
        
        # Test invalid department ID
        group.department_id = 0
        with self.assertRaises(ValueError):
            group.validate()
        
        # Reset to valid state
        group.department_id = 1
        
        # Test None department ID (should be valid)
        group.department_id = None
        group.validate()  # Should not raise an exception


if __name__ == "__main__":
    unittest.main()