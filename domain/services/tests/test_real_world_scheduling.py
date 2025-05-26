import unittest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.entities.team import Team
from domain.services.schedule_service import ScheduleService
from domain.models.EmployeeModel import EmployeeModel
from domain.models.WorkstationModel import WorkstationModel
from domain.models.TeamModel import TeamModel
from domain.repositories.implementations.sqlalchemy_employee_repository import SqlAlchemyEmployeeRepository
from domain.repositories.implementations.sqlalchemy_workstation_repository import SqlAlchemyWorkstationRepository
from domain.repositories.implementations.sqlalchemy_team_repository import SqlAlchemyTeamRepository


class TestRealWorldScheduling(unittest.TestCase):
    @unittest.skip("This test requires a database connection and real data")
    def test_generate_schedule_real_world(self):
        """Test generating a schedule with real-world data."""
        # Create a database connection
        engine = create_engine("sqlite:///heijunka.db")
        Session = sessionmaker(bind=engine)
        session = Session()

        # Create repositories
        employee_repo = SqlAlchemyEmployeeRepository(session)
        workstation_repo = SqlAlchemyWorkstationRepository(session)
        team_repo = SqlAlchemyTeamRepository(session)

        # Get a real team
        team_name = "headsub"
        team = team_repo.get_by_name(team_name)

        if not team:
            self.skipTest(f"Team {team_name} not found in the database")

        # Get real employees for the team
        employees = employee_repo.get_by_team_id(team.id)

        if not employees:
            self.skipTest(f"No employees found for team {team_name}")

        # Get real workstations for the team
        workstations = workstation_repo.get_by_team_id(team.id)

        if not workstations:
            self.skipTest(f"No workstations found for team {team_name}")

        # Create a schedule service
        schedule_service = ScheduleService()

        # Generate a schedule
        start_date = date.today()
        periods_per_day = 4

        # Generate the schedule
        assignments = schedule_service.generate_schedule(
            employees=employees,
            workstations=workstations,
            start_date=start_date,
            periods_per_day=periods_per_day,
            team_name=team_name,
            session=session,
            team_repository=team_repo
        )

        # Verify that assignments were generated
        self.assertIsNotNone(assignments)
        self.assertTrue(len(assignments) > 0)

        # Verify that each assignment has the correct date
        for assignment in assignments:
            self.assertEqual(assignment.period.date, start_date)

        # Verify that each employee is assigned to at most one workstation per period
        for period in range(1, periods_per_day + 1):
            employee_assignments = {}
            for assignment in assignments:
                if assignment.period.period == period:
                    employee_id = assignment.employee.id
                    self.assertNotIn(employee_id, employee_assignments, 
                                    f"Employee {employee_id} assigned to multiple workstations in period {period}")
                    employee_assignments[employee_id] = assignment.workstation.id

        # Verify that each workstation has at most one employee per period
        for period in range(1, periods_per_day + 1):
            workstation_assignments = {}
            for assignment in assignments:
                if assignment.period.period == period:
                    workstation_id = assignment.workstation.id
                    self.assertNotIn(workstation_id, workstation_assignments, 
                                    f"Workstation {workstation_id} assigned to multiple employees in period {period}")
                    workstation_assignments[workstation_id] = assignment.employee.id

        # Verify that employees are only assigned to workstations they are qualified for
        for assignment in assignments:
            employee = assignment.employee
            workstation = assignment.workstation
            self.assertTrue(employee.can_work(workstation), 
                           f"Employee {employee.id} assigned to workstation {workstation.id} but is not qualified")

        # Print some statistics about the schedule
        print(f"Generated {len(assignments)} assignments for {len(employees)} employees and {len(workstations)} workstations")
        print(f"Assignments per period:")
        for period in range(1, periods_per_day + 1):
            period_assignments = [a for a in assignments if a.period.period == period]
            print(f"  Period {period}: {len(period_assignments)} assignments")

        # Close the session
        session.close()


if __name__ == '__main__':
    unittest.main()
