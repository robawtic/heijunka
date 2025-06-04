import logging
from datetime import date
from domain.services.schedule_service import ScheduleService
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_schedule_generation():
    """Test schedule generation with empty prefetched_data to verify the fix."""
    logger.info("Starting schedule generation test")

    # Create a schedule service
    schedule_service = ScheduleService()

    # Create some test data
    employees = [
        Employee(id=1, name="Employee 1", team_id=1),
        Employee(id=2, name="Employee 2", team_id=1),
        Employee(id=3, name="Employee 3", team_id=1)
    ]

    workstations = [
        Workstation(id=1, name="Workstation 1", line_type="standard", team_id=1),
        Workstation(id=2, name="Workstation 2", line_type="standard", team_id=1)
    ]

    start_date = date.today()
    periods_per_day = 2
    team_name = "Test Team"

    # Create a prefetched_data dictionary with team information
    # Create a simple team object with id and name attributes
    class MockTeam:
        def __init__(self, id, name):
            self.id = id
            self.name = name

    # Create a mock team
    test_team = MockTeam(id=1, name="Test Team")

    # Add the team to prefetched_data
    prefetched_data = {
        'teams_by_name': {
            'Test Team': test_team
        }
    }

    try:
        # Generate a schedule
        assignments = schedule_service.generate_schedule(
            employees=employees,
            workstations=workstations,
            start_date=start_date,
            periods_per_day=periods_per_day,
            team_name=team_name,
            prefetched_data=prefetched_data
        )

        logger.info(f"Successfully generated {len(assignments)} assignments")
        logger.info("Test passed: No 'aro_assignments_by_team' error occurred")
        return True
    except Exception as e:
        logger.error(f"Error during schedule generation: {str(e)}")
        logger.error("Test failed")
        return False

if __name__ == "__main__":
    success = test_schedule_generation()
    print(f"Test {'passed' if success else 'failed'}")
