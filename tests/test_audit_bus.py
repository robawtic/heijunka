import unittest
import os
import shutil
import tempfile
from datetime import datetime, timedelta
import json
import time
from infrastructure.audit.bus import AuditEvent, AuditEventBus

class TestAuditEventBus(unittest.TestCase):
    """Test cases for the AuditEventBus class."""
    
    def setUp(self):
        """Set up a temporary directory for audit event storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.bus = AuditEventBus(self.temp_dir)
        
    def tearDown(self):
        """Clean up the temporary directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_publish_and_persist(self):
        """Test that events are published and persisted correctly."""
        # Create a test event
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            user={"username": "test_user", "roles": ["admin"]},
            action="create",
            resource_type="user",
            resource_id="123",
            details={"key": "value"}
        )
        
        # Create a subscriber to verify that events are published
        received_events = []
        def subscriber(event):
            received_events.append(event)
        
        # Subscribe to events
        self.bus.subscribe(subscriber)
        
        # Publish the event
        self.bus.publish(event)
        
        # Verify that the subscriber received the event
        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].id, event.id)
        
        # Verify that the event was persisted
        date_str = datetime.fromisoformat(event.timestamp).strftime("%Y%m%d")
        file_path = os.path.join(self.temp_dir, f"{date_str}_audit.jsonl")
        self.assertTrue(os.path.exists(file_path))
        
        # Read the persisted event
        with open(file_path, "r") as f:
            persisted_event = json.loads(f.read().strip())
        
        # Verify that the persisted event matches the original event
        self.assertEqual(persisted_event["id"], event.id)
        self.assertEqual(persisted_event["action"], "create")
        self.assertEqual(persisted_event["resource_type"], "user")
        self.assertEqual(persisted_event["resource_id"], "123")
        self.assertEqual(persisted_event["user"]["username"], "test_user")
        self.assertEqual(persisted_event["details"]["key"], "value")
    
    def test_replay_events(self):
        """Test that events can be replayed with filtering."""
        # Create test events
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        
        events = [
            # Yesterday, user1, create, user
            AuditEvent(
                timestamp=yesterday.isoformat(),
                user={"username": "user1", "roles": ["admin"]},
                action="create",
                resource_type="user",
                resource_id="123",
                details={}
            ),
            # Yesterday, user2, update, user
            AuditEvent(
                timestamp=yesterday.isoformat(),
                user={"username": "user2", "roles": ["editor"]},
                action="update",
                resource_type="user",
                resource_id="123",
                details={}
            ),
            # Today, user1, delete, user
            AuditEvent(
                timestamp=now.isoformat(),
                user={"username": "user1", "roles": ["admin"]},
                action="delete",
                resource_type="user",
                resource_id="123",
                details={}
            ),
            # Today, user1, create, team
            AuditEvent(
                timestamp=now.isoformat(),
                user={"username": "user1", "roles": ["admin"]},
                action="create",
                resource_type="team",
                resource_id="456",
                details={}
            )
        ]
        
        # Publish all events
        for event in events:
            self.bus.publish(event)
        
        # Wait for events to be persisted
        time.sleep(0.1)
        
        # Test replay with no filters (should return all events)
        replayed = self.bus.replay_events()
        self.assertEqual(len(replayed), 4)
        
        # Test replay with start_time filter
        replayed = self.bus.replay_events(start_time=now)
        self.assertEqual(len(replayed), 2)
        
        # Test replay with end_time filter
        replayed = self.bus.replay_events(end_time=yesterday)
        self.assertEqual(len(replayed), 2)
        
        # Test replay with user filter
        replayed = self.bus.replay_events(user="user1")
        self.assertEqual(len(replayed), 3)
        
        # Test replay with action filter
        replayed = self.bus.replay_events(action="create")
        self.assertEqual(len(replayed), 2)
        
        # Test replay with resource_type filter
        replayed = self.bus.replay_events(resource_type="team")
        self.assertEqual(len(replayed), 1)
        
        # Test replay with resource_id filter
        replayed = self.bus.replay_events(resource_id="456")
        self.assertEqual(len(replayed), 1)
        
        # Test replay with multiple filters
        replayed = self.bus.replay_events(
            user="user1",
            action="create",
            resource_type="team"
        )
        self.assertEqual(len(replayed), 1)
        self.assertEqual(replayed[0].resource_id, "456")
    
    def test_unsubscribe(self):
        """Test that subscribers can be unsubscribed."""
        # Create a test event
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            user={"username": "test_user", "roles": ["admin"]},
            action="create",
            resource_type="user",
            resource_id="123",
            details={}
        )
        
        # Create subscribers
        received_events1 = []
        received_events2 = []
        
        def subscriber1(event):
            received_events1.append(event)
            
        def subscriber2(event):
            received_events2.append(event)
        
        # Subscribe both subscribers
        self.bus.subscribe(subscriber1)
        self.bus.subscribe(subscriber2)
        
        # Publish an event
        self.bus.publish(event)
        
        # Verify that both subscribers received the event
        self.assertEqual(len(received_events1), 1)
        self.assertEqual(len(received_events2), 1)
        
        # Unsubscribe subscriber1
        self.bus.unsubscribe(subscriber1)
        
        # Clear the received events
        received_events1.clear()
        received_events2.clear()
        
        # Publish another event
        self.bus.publish(event)
        
        # Verify that only subscriber2 received the event
        self.assertEqual(len(received_events1), 0)
        self.assertEqual(len(received_events2), 1)

if __name__ == "__main__":
    unittest.main()