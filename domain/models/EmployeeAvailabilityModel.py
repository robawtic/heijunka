# domain/models/EmployeeAvailabilityModel.py
from sqlalchemy import Column, Integer, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .Base import Base
from domain.entities.employee_availability import EmployeeAvailability


class EmployeeAvailabilityModel(Base):
    __tablename__ = 'employee_availability'

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    date = Column(Date, nullable=False)
    period = Column(Integer, nullable=True)
    is_partial = Column(Boolean, default=False)
    is_call_in = Column(Boolean, default=False)
    is_aro = Column(Boolean, default=False)

    employee = relationship('EmployeeModel', back_populates='availability')


def to_domain(self) -> 'EmployeeAvailability':
    from domain.entities.employee_availability import EmployeeAvailability

    return EmployeeAvailability(
        id=self.id,
        employee_id=self.employee_id,
        date=self.date,
        period=self.period,
        is_partial=self.is_partial,
        is_call_in=self.is_call_in,
        is_aro=self.is_aro
    )

