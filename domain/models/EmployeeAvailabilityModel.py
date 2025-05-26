# domain/models/EmployeeAvailabilityModel.py
from sqlalchemy import Column, Integer, Date, String, ForeignKey, Enum, Boolean, text
from sqlalchemy.orm import relationship
from .Base import Base
from domain.value_objects.employee_availability import EmployeeAvailability, AvailabilityStatus


class EmployeeAvailabilityModel(Base):
    __tablename__ = 'employee_availability'

    # Use a composite primary key instead of an auto-generated ID
    employee_id = Column(Integer, ForeignKey('employees.id'), primary_key=True)
    date = Column(Date, primary_key=True)
    # Use a default value of 0 for period when it's NULL in the domain object
    period = Column(Integer, primary_key=True, default=0)
    is_partial = Column(Boolean, nullable=False, server_default=text('false'))
    is_call_in = Column(Boolean, nullable=False, server_default=text('false'))
    is_aro = Column(Boolean, nullable=False, server_default=text('false'))

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

        # Convert period=0 to period=None for full-day statuses
        period = None if self.period == 0 else self.period

        return EmployeeAvailability(
            employee_id=self.employee_id,
            date=self.date,
            period=period,
            status=status
        )
