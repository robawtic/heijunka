# domain/models/EmployeeAvailabilityModel.py
from sqlalchemy import Column, Integer, Date, String, ForeignKey, Enum, Boolean, text
from sqlalchemy.orm import relationship
from .Base import Base
from domain.entities.employee_availability import EmployeeAvailability, AvailabilityStatus


class EmployeeAvailabilityModel(Base):
    __tablename__ = 'employee_availability'

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    date = Column(Date, nullable=False)
    period = Column(Integer, nullable=True)
    is_partial = Column(Boolean, nullable=False, server_default=text('0'))
    is_call_in = Column(Boolean, nullable=False, server_default=text('0'))
    is_aro = Column(Boolean, nullable=False, server_default=text('0'))

    employee = relationship('EmployeeModel', back_populates='availability')

    def to_domain(self) -> 'EmployeeAvailability':
        # Convert boolean flags to status enum
        status = AvailabilityStatus.AVAILABLE
        if self.is_call_in:
            status = AvailabilityStatus.CALL_IN
        elif self.is_aro:
            status = AvailabilityStatus.ARO
        elif self.is_partial:
            status = AvailabilityStatus.PARTIAL

        return EmployeeAvailability(
            employee_id=self.employee_id,
            date=self.date,
            period=self.period,
            status=status
        )
