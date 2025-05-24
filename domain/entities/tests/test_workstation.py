import unittest
from datetime import date

from domain.entities.workstation import Workstation
from domain.events import (
    WorkstationCreated, WorkstationUpdated, WorkstationPropertyChanged,
    WorkstationLineTypeChanged, WorkstationTeamChanged
)


class TestWorkstation(unittest.TestCase):
    def setUp(self):
        """Set up a new workstation for each test."""
        self.workstation = Workstation(
            id=1,
            name="Workstation 1",
            line_type="Mainline"
        )
        # Clear the creation event
        self.workstation.clear_domain_events()

    def test_initialization(self):
        """Test that a workstation is properly initialized."""
        workstation = Workstation(
            id=2,
            name="Workstation 2",
            line_type="Mainline",
            is_loading_job=True,
            is_heavy_job=True,
            is_key_skill_job=True,
            team_id=1
        )

        # Check properties
        self.assertEqual(workstation.id, 2)
        self.assertEqual(workstation.name, "Workstation 2")
        self.assertEqual(workstation.line_type, "Mainline")
        self.assertTrue(workstation.is_loading_job)
        self.assertTrue(workstation.is_heavy_job)
        self.assertTrue(workstation.is_key_skill_job)
        self.assertEqual(workstation.team_id, 1)

        # Check helper methods
        self.assertTrue(workstation.is_loading())
        self.assertTrue(workstation.is_heavy())
        self.assertTrue(workstation.requires_key_skill())

        # Check that a creation event was raised
        events = workstation.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WorkstationCreated)
        self.assertEqual(events[0].workstation_id, 2)
        self.assertEqual(events[0].name, "Workstation 2")
        self.assertEqual(events[0].line_type, "Mainline")

    def test_set_line_type(self):
        """Test changing the line type of a workstation."""
        # Change the line type
        result = self.workstation.set_line_type("SubAssembly")
        self.assertTrue(result)
        self.assertEqual(self.workstation.line_type, "SubAssembly")

        # Check that a domain event was raised
        events = self.workstation.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WorkstationLineTypeChanged)
        self.assertEqual(events[0].workstation_id, 1)
        self.assertEqual(events[0].old_line_type, "Mainline")
        self.assertEqual(events[0].new_line_type, "SubAssembly")

        # Try to set the same line type again
        self.workstation.clear_domain_events()
        result = self.workstation.set_line_type("SubAssembly")
        self.assertFalse(result)  # Should return False for no change
        self.assertEqual(len(self.workstation.domain_events), 0)  # No event should be raised

        # Test invalid line type
        with self.assertRaises(ValueError):
            self.workstation.set_line_type("")
        with self.assertRaises(ValueError):
            self.workstation.set_line_type(None)

    def test_set_team(self):
        """Test assigning the workstation to a team."""
        # Assign to a team
        result = self.workstation.set_team(2)
        self.assertTrue(result)
        self.assertEqual(self.workstation.team_id, 2)

        # Check that a domain event was raised
        events = self.workstation.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WorkstationTeamChanged)
        self.assertEqual(events[0].workstation_id, 1)
        self.assertEqual(events[0].old_team_id, None)
        self.assertEqual(events[0].new_team_id, 2)

        # Try to set the same team again
        self.workstation.clear_domain_events()
        result = self.workstation.set_team(2)
        self.assertFalse(result)  # Should return False for no change
        self.assertEqual(len(self.workstation.domain_events), 0)  # No event should be raised

        # Change to a different team
        result = self.workstation.set_team(3)
        self.assertTrue(result)
        self.assertEqual(self.workstation.team_id, 3)

        # Check that a domain event was raised
        events = self.workstation.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WorkstationTeamChanged)
        self.assertEqual(events[0].old_team_id, 2)
        self.assertEqual(events[0].new_team_id, 3)

        # Unassign from team
        self.workstation.clear_domain_events()
        result = self.workstation.set_team(None)
        self.assertTrue(result)
        self.assertIsNone(self.workstation.team_id)

        # Check that a domain event was raised
        events = self.workstation.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WorkstationTeamChanged)
        self.assertEqual(events[0].old_team_id, 3)
        self.assertIsNone(events[0].new_team_id)

        # Test invalid team ID
        with self.assertRaises(ValueError):
            self.workstation.set_team(0)
        with self.assertRaises(ValueError):
            self.workstation.set_team(-1)

    def test_set_loading_job(self):
        """Test setting whether the workstation is a loading job."""
        # Set to True
        result = self.workstation.set_loading_job(True)
        self.assertTrue(result)
        self.assertTrue(self.workstation.is_loading_job)
        self.assertTrue(self.workstation.is_loading())

        # Check that a domain event was raised
        events = self.workstation.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WorkstationPropertyChanged)
        self.assertEqual(events[0].workstation_id, 1)
        self.assertEqual(events[0].property_name, "is_loading_job")
        self.assertEqual(events[0].old_value, False)
        self.assertEqual(events[0].new_value, True)

        # Try to set the same value again
        self.workstation.clear_domain_events()
        result = self.workstation.set_loading_job(True)
        self.assertFalse(result)  # Should return False for no change
        self.assertEqual(len(self.workstation.domain_events), 0)  # No event should be raised

        # Set back to False
        result = self.workstation.set_loading_job(False)
        self.assertTrue(result)
        self.assertFalse(self.workstation.is_loading_job)
        self.assertFalse(self.workstation.is_loading())

        # Check that a domain event was raised
        events = self.workstation.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WorkstationPropertyChanged)
        self.assertEqual(events[0].old_value, True)
        self.assertEqual(events[0].new_value, False)

    def test_set_heavy_job(self):
        """Test setting whether the workstation is a heavy job."""
        # Set to True
        result = self.workstation.set_heavy_job(True)
        self.assertTrue(result)
        self.assertTrue(self.workstation.is_heavy_job)
        self.assertTrue(self.workstation.is_heavy())

        # Check that a domain event was raised
        events = self.workstation.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WorkstationPropertyChanged)
        self.assertEqual(events[0].workstation_id, 1)
        self.assertEqual(events[0].property_name, "is_heavy_job")
        self.assertEqual(events[0].old_value, False)
        self.assertEqual(events[0].new_value, True)

        # Try to set the same value again
        self.workstation.clear_domain_events()
        result = self.workstation.set_heavy_job(True)
        self.assertFalse(result)  # Should return False for no change
        self.assertEqual(len(self.workstation.domain_events), 0)  # No event should be raised

        # Set back to False
        result = self.workstation.set_heavy_job(False)
        self.assertTrue(result)
        self.assertFalse(self.workstation.is_heavy_job)
        self.assertFalse(self.workstation.is_heavy())

        # Check that a domain event was raised
        events = self.workstation.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WorkstationPropertyChanged)
        self.assertEqual(events[0].old_value, True)
        self.assertEqual(events[0].new_value, False)

    def test_set_key_skill_job(self):
        """Test setting whether the workstation requires key skill."""
        # Set to True
        result = self.workstation.set_key_skill_job(True)
        self.assertTrue(result)
        self.assertTrue(self.workstation.is_key_skill_job)
        self.assertTrue(self.workstation.requires_key_skill())

        # Check that a domain event was raised
        events = self.workstation.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WorkstationPropertyChanged)
        self.assertEqual(events[0].workstation_id, 1)
        self.assertEqual(events[0].property_name, "is_key_skill_job")
        self.assertEqual(events[0].old_value, False)
        self.assertEqual(events[0].new_value, True)

        # Try to set the same value again
        self.workstation.clear_domain_events()
        result = self.workstation.set_key_skill_job(True)
        self.assertFalse(result)  # Should return False for no change
        self.assertEqual(len(self.workstation.domain_events), 0)  # No event should be raised

        # Set back to False
        result = self.workstation.set_key_skill_job(False)
        self.assertTrue(result)
        self.assertFalse(self.workstation.is_key_skill_job)
        self.assertFalse(self.workstation.requires_key_skill())

        # Check that a domain event was raised
        events = self.workstation.domain_events
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], WorkstationPropertyChanged)
        self.assertEqual(events[0].old_value, True)
        self.assertEqual(events[0].new_value, False)

    def test_update(self):
        """Test updating multiple properties at once."""
        # Update multiple properties
        self.workstation.update(
            name="Updated Workstation",
            line_type="SubAssembly",
            is_loading_job=True,
            is_heavy_job=True,
            is_key_skill_job=True,
            team_id=2
        )

        # Check that properties were updated
        self.assertEqual(self.workstation.name, "Updated Workstation")
        self.assertEqual(self.workstation.line_type, "SubAssembly")
        self.assertTrue(self.workstation.is_loading_job)
        self.assertTrue(self.workstation.is_heavy_job)
        self.assertTrue(self.workstation.is_key_skill_job)
        self.assertEqual(self.workstation.team_id, 2)

        # Check that domain events were raised
        events = self.workstation.domain_events
        # Should be 7 events: 6 property changes (name, line_type, 3 job flags, team_id) + 1 update event
        self.assertEqual(len(events), 7)

        # The last event should be WorkstationUpdated
        self.assertIsInstance(events[-1], WorkstationUpdated)
        self.assertEqual(events[-1].workstation_id, 1)

        # Update with no changes
        self.workstation.clear_domain_events()
        self.workstation.update(
            name="Updated Workstation",
            line_type="SubAssembly",
            is_loading_job=True,
            is_heavy_job=True,
            is_key_skill_job=True,
            team_id=2
        )

        # No events should be raised
        self.assertEqual(len(self.workstation.domain_events), 0)

        # Update with some changes
        self.workstation.update(
            name="Updated Again",
            is_loading_job=False
        )

        # Check that properties were updated
        self.assertEqual(self.workstation.name, "Updated Again")
        self.assertFalse(self.workstation.is_loading_job)

        # Check that domain events were raised
        events = self.workstation.domain_events
        # Should be at least 2 events (name change and loading_job change)
        self.assertGreaterEqual(len(events), 2)

        # Verify we have the expected property change events
        property_events = [e for e in events if isinstance(e, WorkstationPropertyChanged)]
        self.assertGreaterEqual(len(property_events), 2)

        # Verify we have the WorkstationUpdated event
        update_events = [e for e in events if isinstance(e, WorkstationUpdated)]
        self.assertEqual(len(update_events), 1)

        # Test invalid values
        with self.assertRaises(ValueError):
            self.workstation.update(name="")
        with self.assertRaises(ValueError):
            self.workstation.update(line_type="")
        with self.assertRaises(ValueError):
            self.workstation.update(team_id=0)

    def test_validate(self):
        """Test validating the workstation entity."""
        # Valid workstation
        self.workstation.validate()  # Should not raise an exception

        # Test validation directly without creating invalid objects
        # This avoids triggering validation in __post_init__ and WorkstationCreated event

        # Create a valid workstation first
        workstation = Workstation(id=2, name="Valid Name", line_type="Mainline")
        workstation.clear_domain_events()

        # Test invalid name (empty)
        workstation.name = ""
        with self.assertRaises(ValueError):
            workstation.validate()

        # Reset to valid state
        workstation.name = "Valid Name"

        # Test invalid name (too long)
        workstation.name = "x" * 101
        with self.assertRaises(ValueError):
            workstation.validate()

        # Reset to valid state
        workstation.name = "Valid Name"

        # Test invalid line type (empty)
        workstation.line_type = ""
        with self.assertRaises(ValueError):
            workstation.validate()


if __name__ == "__main__":
    unittest.main()
