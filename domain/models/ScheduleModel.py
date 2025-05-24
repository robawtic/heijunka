from sqlalchemy import Column, Integer, Date, String, Boolean, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .Base import Base

class ScheduleModel(Base):
    __tablename__ = 'schedules'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    start_date = Column(Date, nullable=False, index=True)
    periods_per_day = Column(Integer, nullable=False, default=4)
    call_ins = Column(JSON, nullable=True)
    offline = Column(JSON, nullable=True)
    force_complete = Column(Boolean, default=False)
    status = Column(String, default="pending", index=True)
    error_message = Column(String, nullable=True)
    task_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Add composite index for common query patterns
    __table_args__ = (
        Index('idx_team_date_status', 'team_id', 'start_date', 'status'),
    )

    # Relationships
    team = relationship('TeamModel', backref='schedules')
    work_history_entries = relationship('EmployeeWorkHistoryModel', back_populates='schedule', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Schedule(id={self.id}, team_id={self.team_id}, start_date={self.start_date}, status={self.status})>"
