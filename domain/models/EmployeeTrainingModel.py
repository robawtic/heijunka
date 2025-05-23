from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Enum, UniqueConstraint, Date
from sqlalchemy.orm import relationship
from .Base import Base


class EmployeeTrainingModel(Base):
    __tablename__ = 'employee_training'

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'))
    station_id = Column(Integer, ForeignKey('workstations.id'))
    required_training = Column(Boolean, default=True)
    date_completed = Column(Date, nullable=True)

    # Relationships
    employee = relationship('EmployeeModel')
    workstation = relationship('WorkstationModel')

    def __repr__(self):
        return f"<EmployeeTrainingModel(employee_id={self.employee_id}, station_id={self.station_id}, required_training={self.required_training})>"