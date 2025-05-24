# domain/models/EmployeeAvailabilityModel.py
from sqlalchemy import Column, Integer, Date, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .Base import Base
from domain.entities.employee_availability import EmployeeAvailability, AvailabilityStatus


class EmployeeAvailabilityModel(Base):
    __tablename__ = 'employee_availability'

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    date = Column(Date, nullable=False)
    period = Column(Integer, nullable=True)
    status = Column(Enum(AvailabilityStatus), default=AvailabilityStatus.AVAILABLE)

    employee = relationship('EmployeeModel', back_populates='availability')

    def to_domain(self) -> 'EmployeeAvailability':
        return EmployeeAvailability(
            employee_id=self.employee_id,
            date=self.date,
            period=self.period,
            status=self.status
        )
