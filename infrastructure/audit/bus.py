import json
import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import os
import time
import uuid
from dataclasses import dataclass, field, asdict

@dataclass
class AuditEvent:
    """
    Data class representing an audit event.
    
    Attributes:
        id: Unique identifier for the event
        timestamp: Time when the event occurred
        user: User who performed the action
        action: Action that was performed
        resource_type: Type of resource that was acted upon
        resource_id: ID of the resource
        details: Additional details about the action
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    user: Dict[str, Any] = field(default_factory=dict)
    action: str = ""
    resource_type: str = ""
    resource_id: Any = None
    details: Dict[str, Any] = field(default_factory=dict)

class AuditEventBus:
    """
    Bus for publishing and subscribing to audit events.
    
    This class provides a way to publish audit events and subscribe to them.
    It also supports persisting events to a file or database for later replay.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the audit event bus.
        
        Args:
            storage_path: Path to the directory where audit events will be stored.
                          If None, events will not be persisted.
        """
        self.subscribers: List[Callable[[AuditEvent], None]] = []
        self.storage_path = storage_path
        self.logger = logging.getLogger("heijunka.audit.bus")
        self.lock = threading.RLock()
        
        # Create storage directory if it doesn't exist
        if storage_path and not os.path.exists(storage_path):
            try:
                os.makedirs(storage_path, exist_ok=True)
            except Exception as e:
                self.logger.error(f"Failed to create audit storage directory: {e}")
    
    def publish(self, event: AuditEvent) -> None:
        """
        Publish an audit event.
        
        Args:
            event: The audit event to publish
        """
        with self.lock:
            # Notify subscribers
            for subscriber in self.subscribers:
                try:
                    subscriber(event)
                except Exception as e:
                    self.logger.error(f"Error in audit event subscriber: {e}")
            
            # Persist the event if storage path is configured
            if self.storage_path:
                self._persist_event(event)
    
    def subscribe(self, callback: Callable[[AuditEvent], None]) -> None:
        """
        Subscribe to audit events.
        
        Args:
            callback: Function to call when an audit event is published
        """
        with self.lock:
            self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[AuditEvent], None]) -> None:
        """
        Unsubscribe from audit events.
        
        Args:
            callback: Function to remove from subscribers
        """
        with self.lock:
            if callback in self.subscribers:
                self.subscribers.remove(callback)
    
    def _persist_event(self, event: AuditEvent) -> None:
        """
        Persist an audit event to storage.
        
        Args:
            event: The audit event to persist
        """
        if not self.storage_path:
            return
        
        try:
            # Create a filename based on timestamp and event ID
            timestamp = datetime.fromisoformat(event.timestamp)
            date_str = timestamp.strftime("%Y%m%d")
            filename = f"{date_str}_audit.jsonl"
            file_path = os.path.join(self.storage_path, filename)
            
            # Convert event to JSON
            event_json = json.dumps(asdict(event))
            
            # Append to file
            with open(file_path, "a") as f:
                f.write(event_json + "\n")
        except Exception as e:
            self.logger.error(f"Failed to persist audit event: {e}")
    
    def replay_events(self, 
                     start_time: Optional[datetime] = None, 
                     end_time: Optional[datetime] = None,
                     user: Optional[str] = None,
                     action: Optional[str] = None,
                     resource_type: Optional[str] = None,
                     resource_id: Optional[Any] = None) -> List[AuditEvent]:
        """
        Replay audit events from storage.
        
        Args:
            start_time: Start time for events to replay
            end_time: End time for events to replay
            user: Filter events by user
            action: Filter events by action
            resource_type: Filter events by resource type
            resource_id: Filter events by resource ID
            
        Returns:
            List of audit events matching the criteria
        """
        if not self.storage_path:
            return []
        
        events = []
        
        try:
            # Determine which files to read based on date range
            files_to_read = []
            if start_time:
                start_date = start_time.strftime("%Y%m%d")
            else:
                # Default to all files
                start_date = "00000000"
            
            if end_time:
                end_date = end_time.strftime("%Y%m%d")
            else:
                # Default to current date
                end_date = datetime.now().strftime("%Y%m%d")
            
            # List all audit files in the directory
            for filename in os.listdir(self.storage_path):
                if filename.endswith("_audit.jsonl"):
                    date_str = filename.split("_")[0]
                    if start_date <= date_str <= end_date:
                        files_to_read.append(os.path.join(self.storage_path, filename))
            
            # Read and filter events from files
            for file_path in sorted(files_to_read):
                with open(file_path, "r") as f:
                    for line in f:
                        try:
                            event_dict = json.loads(line.strip())
                            
                            # Apply filters
                            if start_time and datetime.fromisoformat(event_dict["timestamp"]) < start_time:
                                continue
                            if end_time and datetime.fromisoformat(event_dict["timestamp"]) > end_time:
                                continue
                            if user and event_dict["user"].get("username") != user:
                                continue
                            if action and event_dict["action"] != action:
                                continue
                            if resource_type and event_dict["resource_type"] != resource_type:
                                continue
                            if resource_id is not None and event_dict["resource_id"] != resource_id:
                                continue
                            
                            # Create AuditEvent from dictionary
                            event = AuditEvent(**event_dict)
                            events.append(event)
                        except Exception as e:
                            self.logger.error(f"Error parsing audit event: {e}")
        except Exception as e:
            self.logger.error(f"Error replaying audit events: {e}")
        
        return events

# Singleton instance
_audit_event_bus = None

def get_audit_event_bus(storage_path: Optional[str] = None) -> AuditEventBus:
    """
    Get the audit event bus instance.
    
    Args:
        storage_path: Path to the directory where audit events will be stored.
                      If None, the default path from settings will be used.
                      
    Returns:
        The audit event bus instance
    """
    global _audit_event_bus
    
    if _audit_event_bus is None:
        from infrastructure.config.settings import settings
        
        # Use provided storage path or default from settings
        path = storage_path or os.path.join(settings.log_dir, "audit_events")
        
        _audit_event_bus = AuditEventBus(path)
    
    return _audit_event_bus