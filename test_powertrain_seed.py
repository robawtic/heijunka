import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).resolve().parent))

from infrastructure.seeding.seed_data.powertrain_seed import seed_powertrain_data
from domain.models.db import Session as SessionFactory

def main():
    print("Starting powertrain seed test...")
    
    # Create a database session
    session = SessionFactory()
    
    try:
        # Call the seed_powertrain_data function
        seed_powertrain_data(session)
        print("Powertrain seed test completed successfully.")
    except Exception as e:
        print(f"Error during powertrain seed test: {e}")
        # Rollback the session in case of error
        session.rollback()
    finally:
        # Close the session
        session.close()

if __name__ == "__main__":
    main()