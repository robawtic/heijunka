from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Enum, UniqueConstraint, Date, Text
from sqlalchemy.orm import relationship
from .Base import Base

class EmployeeStationSkillModel(Base):
    __tablename__ = "employee_station_skills"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    station_id = Column(Integer, ForeignKey("workstations.id"))

    status = Column(Enum("certified", "in_training", "expired", "flagged", "banned", name="skill_status_enum"))
    last_verified = Column(Date)
    reason = Column(String)  # Optional: "expired", "missed tack time", etc.
    notes = Column(Text)

    __table_args__ = (UniqueConstraint("id", "id"),)


    employee = relationship('EmployeeModel', back_populates='station_skills')
    station = relationship('WorkstationModel', back_populates='employee_skills')

    def __repr__(self):
        return f"<EmployeeStationSkill(id={self.employee_id}, station_id={self.station_id})>"
