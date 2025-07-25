from typing import Optional, List


class SeedDatabaseCommand:
    """Command to seed the database with initial data."""
    
    def __init__(
        self,
        department: Optional[str] = None,
        group: Optional[str] = None,
        team: Optional[str] = None,
        reset_database: bool = False
    ):
        """
        Initialize the command.
        
        Args:
            department: Optional department name to seed
            group: Optional group name to seed
            team: Optional team name to seed
            reset_database: Whether to reset the database before seeding
        """
        self.department = department
        self.group = group
        self.team = team
        self.reset_database = reset_database