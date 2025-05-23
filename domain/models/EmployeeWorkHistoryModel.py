from sqlalchemy import Column, Integer, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .Base import Base

class EmployeeWorkHistoryModel(Base):
    __tablename__ = 'employee_work_history'

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    station_id = Column(Integer, ForeignKey('workstations.id'), nullable=False)
    schedule_id = Column(Integer, ForeignKey('schedules.id'), nullable=True)
    worked_date = Column(Date, nullable=False)
    work_period = Column(Integer, nullable=False)
    end_flag = Column(Boolean, nullable=False)
    is_generated = Column(Boolean, nullable=False, default=False)
    is_temporary = Column(Boolean, nullable=False, default=False)  # Indicates a temporary assignment

    # Relationships
    employee = relationship('EmployeeModel', back_populates='work_history')
    station = relationship('WorkstationModel', back_populates='work_history')
    schedule = relationship('ScheduleModel', back_populates='work_history_entries')
