from enum import Enum
from sqlalchemy import Column, Integer, Date, Boolean, ForeignKey, Enum as SqlEnum
from sqlalchemy.orm import relationship
from .Base import Base

class WorkHistoryStatus(Enum):
    REGULAR = 'regular'
    GENERATED = 'generated'
    TEMPORARY = 'temporary'
    GENERATED_TEMPORARY = 'generated_temporary'

class EmployeeWorkHistoryModel(Base):
    __tablename__ = 'employee_work_history'

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    station_id = Column(Integer, ForeignKey('workstations.id'), nullable=False)
    schedule_id = Column(Integer, ForeignKey('schedules.id'), nullable=True)
    worked_date = Column(Date, nullable=False)
    work_period = Column(Integer, nullable=False)
    end_flag = Column(Boolean, nullable=False)
    status = Column(SqlEnum(WorkHistoryStatus), nullable=False, default=WorkHistoryStatus.REGULAR)

    # Relationships
    employee = relationship('EmployeeModel', back_populates='work_history')
    station = relationship('WorkstationModel', back_populates='work_history')
    schedule = relationship('ScheduleModel', back_populates='work_history_entries')
