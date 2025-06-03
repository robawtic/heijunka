from sqlalchemy import Column, Integer, Date, ForeignKey
from sqlalchemy.orm import relationship
from .Base import Base

class AROAssignmentModel(Base):
    __tablename__ = 'aro_assignments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    from_team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    to_team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    assignment_date = Column(Date, nullable=False)
    period = Column(Integer, nullable=True)  # Null for full-day assignments

    employee = relationship('EmployeeModel', foreign_keys=[employee_id])
    from_team = relationship('TeamModel', foreign_keys=[from_team_id])
    to_team = relationship('TeamModel', foreign_keys=[to_team_id])

    def to_domain(self):
        from domain.contexts.assignment.aro_assignment import AROAssignment
        return AROAssignment(
            id=self.id,
            employee_id=self.employee_id,
            from_team_id=self.from_team_id,
            to_team_id=self.to_team_id,
            assignment_date=self.assignment_date,
            period=self.period
        )
