import unittest
from datetime import date

from domain.entities.department import Department
from domain.entities.group import Group
from domain.events import (
    DepartmentCreated, DepartmentUpdated, DepartmentPropertyChanged,
    GroupAddedToDepartment, GroupRemovedFromDepartment
)


class TestDepartment(unittest.TestCase):
    def setUp(self):
        """Set up a new department for each test."""
        self.department = Department(
            id=1,
            name="Test Department",
            description="A test department"
        )
        # Clear the creation event
        self.department.clear_domain_events()
        
        # Create some test groups
        self.group1 = Group(
            id=1,
            name="Group 1",
            department_id=None
        )
        self.group1.clear_domain_events()
        
        self.group2 = Group(
            id=2,
            name="Group 2",
            department_id=None
        )
        self.group2.clear_domain_events()

    def test_initialization(self):
        """Test that a department is properly initialized."""
        department = Department(
            id=2,
            name="New Department",
            description="A new department"
        )
        
        # Check properties
        self.assertEqual(department.id, 2)
        self.assertEqual(department.name, "New Department")
        self.assertEqual(department.description, "A new department")
        self.assertEqual(department.groups, [])
        
        # Check that a creation event was raised
        events = department.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], DepartmentCreated)
        self.assertEqual(events[0].department_id, 2)
        self.assertEqual(events[0].name, "New Department")
        self.assertEqual(events[0].description, "A new department")

    def test_add_group(self):
        """Test adding a group to the department."""
        # Add a group
        result = self.department.add_group(self.group1)
        self.assertTrue(result)
        self.assertEqual(len(self.department.groups), 1)
        self.assertEqual(self.department.groups[0].id, 1)
        self.assertEqual(self.group1.department_id, 1)  # Should update the group's department_id
        
        # Check that a domain event was raised
        events = self.department.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], GroupAddedToDepartment)
        self.assertEqual(events[0].department_id, 1)
        self.assertEqual(events[0].group_id, 1)
        
        # Try to add the same group again
        result = self.department.add_group(self.group1)
        self.assertFalse(result)  # Should return False for duplicate
        self.assertEqual(len(self.department.groups), 1)  # Should still have only one group
        
        # Clear events and add another group
        self.department.clear_domain_events()
        result = self.department.add_group(self.group2)
        self.assertTrue(result)
        self.assertEqual(len(self.department.groups), 2)
        
        # Check that a new domain event was raised
        events = self.department.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], GroupAddedToDepartment)
        self.assertEqual(events[0].group_id, 2)
        
        # Test invalid group
        with self.assertRaises(ValueError):
            self.department.add_group("not a group")

    def test_remove_group(self):
        """Test removing a group from the department."""
        # Add groups
        self.department.add_group(self.group1)
        self.department.add_group(self.group2)
        self.department.clear_domain_events()
        
        # Remove a group
        result = self.department.remove_group(1)
        self.assertTrue(result)
        self.assertEqual(len(self.department.groups), 1)
        self.assertEqual(self.department.groups[0].id, 2)
        self.assertIsNone(self.group1.department_id)  # Should update the group's department_id
        
        # Check that a domain event was raised
        events = self.department.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], GroupRemovedFromDepartment)
        self.assertEqual(events[0].department_id, 1)
        self.assertEqual(events[0].group_id, 1)
        
        # Try to remove a non-existent group
        result = self.department.remove_group(999)
        self.assertFalse(result)
        self.assertEqual(len(self.department.groups), 1)

    def test_get_group_by_id(self):
        """Test getting a group by ID."""
        # Add groups
        self.department.add_group(self.group1)
        self.department.add_group(self.group2)
        
        # Get a group by ID
        group = self.department.get_group_by_id(1)
        self.assertIsNotNone(group)
        self.assertEqual(group.id, 1)
        self.assertEqual(group.name, "Group 1")
        
        # Try to get a non-existent group
        group = self.department.get_group_by_id(999)
        self.assertIsNone(group)

    def test_get_group_by_name(self):
        """Test getting a group by name."""
        # Add groups
        self.department.add_group(self.group1)
        self.department.add_group(self.group2)
        
        # Get a group by name
        group = self.department.get_group_by_name("Group 1")
        self.assertIsNotNone(group)
        self.assertEqual(group.id, 1)
        self.assertEqual(group.name, "Group 1")
        
        # Try to get a non-existent group
        group = self.department.get_group_by_name("Non-existent Group")
        self.assertIsNone(group)

    def test_set_name(self):
        """Test setting the name of the department."""
        # Set the name
        result = self.department.set_name("New Name")
        self.assertTrue(result)
        self.assertEqual(self.department.name, "New Name")
        
        # Check that a domain event was raised
        events = self.department.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], DepartmentPropertyChanged)
        self.assertEqual(events[0].department_id, 1)
        self.assertEqual(events[0].property_name, "name")
        self.assertEqual(events[0].old_value, "Test Department")
        self.assertEqual(events[0].new_value, "New Name")
        
        # Try to set the same name again
        self.department.clear_domain_events()
        result = self.department.set_name("New Name")
        self.assertFalse(result)  # Should return False for no change
        self.assertEqual(len(self.department.domain_events), 0)  # No event should be raised
        
        # Test invalid name
        with self.assertRaises(ValueError):
            self.department.set_name("")
        with self.assertRaises(ValueError):
            self.department.set_name(None)

    def test_set_description(self):
        """Test setting the description of the department."""
        # Set the description
        result = self.department.set_description("New Description")
        self.assertTrue(result)
        self.assertEqual(self.department.description, "New Description")
        
        # Check that a domain event was raised
        events = self.department.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], DepartmentPropertyChanged)
        self.assertEqual(events[0].department_id, 1)
        self.assertEqual(events[0].property_name, "description")
        self.assertEqual(events[0].old_value, "A test department")
        self.assertEqual(events[0].new_value, "New Description")
        
        # Try to set the same description again
        self.department.clear_domain_events()
        result = self.department.set_description("New Description")
        self.assertFalse(result)  # Should return False for no change
        self.assertEqual(len(self.department.domain_events), 0)  # No event should be raised
        
        # Set to None
        result = self.department.set_description(None)
        self.assertTrue(result)
        self.assertIsNone(self.department.description)
        
        # Test invalid description
        with self.assertRaises(ValueError):
            self.department.set_description(123)

    def test_update(self):
        """Test updating multiple properties at once."""
        # Update multiple properties
        self.department.update(
            name="New Name",
            description="New Description"
        )
        
        # Check that properties were updated
        self.assertEqual(self.department.name, "New Name")
        self.assertEqual(self.department.description, "New Description")
        
        # Check that domain events were raised
        events = self.department.domain_events
        # Should be 3 events: 2 property changes + 1 update event
        self.assertEqual(len(events), 3)
        
        # The last event should be DepartmentUpdated
        self.assertIsInstance(events[-1], DepartmentUpdated)
        self.assertEqual(events[-1].department_id, 1)
        
        # Update with no changes
        self.department.clear_domain_events()
        self.department.update(
            name="New Name",
            description="New Description"
        )
        
        # No events should be raised
        self.assertEqual(len(self.department.domain_events), 0)
        
        # Update with some changes
        self.department.update(
            name="Updated Again"
        )
        
        # Check that properties were updated
        self.assertEqual(self.department.name, "Updated Again")
        
        # Check that domain events were raised
        events = self.department.domain_events
        # Should be 2 events: 1 property change + 1 update event
        self.assertEqual(len(events), 2)
        
        # Test invalid values
        with self.assertRaises(ValueError):
            self.department.update(name="")
        with self.assertRaises(ValueError):
            self.department.update(description=123)

    def test_validate(self):
        """Test validating the department entity."""
        # Valid department
        self.department.validate()  # Should not raise an exception
        
        # Test validation directly without creating invalid objects
        # This avoids triggering validation in __post_init__ and DepartmentCreated event
        
        # Create a valid department first
        department = Department(id=2, name="Valid Name", description="Valid Description")
        department.clear_domain_events()
        
        # Test invalid name (empty)
        department.name = ""
        with self.assertRaises(ValueError):
            department.validate()
        
        # Reset to valid state
        department.name = "Valid Name"
        
        # Test invalid name (too long)
        department.name = "x" * 101
        with self.assertRaises(ValueError):
            department.validate()


if __name__ == "__main__":
    unittest.main()