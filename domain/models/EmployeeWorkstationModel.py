from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Enum, UniqueConstraint, Date
from sqlalchemy.orm import relationship
from .Base import Base

class EmployeeWorkstationModel(Base):
    __tablename__ = 'employee_workstations'

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    station_id = Column(Integer, ForeignKey('workstations.id'), nullable=False)
    last_worked_date = Column(Date, nullable=True)

    # Relationships
    employee = relationship('EmployeeModel', back_populates='workstations')
    workstation = relationship('WorkstationModel', back_populates='employees')

    def __repr__(self):
        return f"<EmployeeWorkstationModel(id={self.employee_id}, station_id={self.station_id})>"
