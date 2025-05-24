# models/WatcherHeartbeat.py

from sqlalchemy import Column, Integer, DateTime, String
from datetime import datetime
from .Base import Base

class WatcherHeartbeatModel(Base):
    __tablename__ = 'watcher_heartbeat'

    id = Column(Integer, primary_key=True)
    last_run = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String, default="ok")  # e.g., "ok", "error", "timeout"
    message = Column(String, nullable=True)
    duration_seconds = Column(Integer, nullable=True)


