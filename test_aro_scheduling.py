import os
import sys
import subprocess
from datetime import date

def main():
    """
    Test the ARO scheduling changes with live data.
    
    This script runs the generate command with the --department powertrain option
    and includes some call-ins to test the ARO scheduling logic.
    """
    print("Testing ARO scheduling changes with live data...")
    
    # Get the current date
    today = date.today()
    date_str = today.strftime("%Y-%m-%d")
    
    # Build the command
    cmd = [
        "python", "main.py", "generate",
        "--department", "powertrain",
        "--start-date", date_str,
        "--periods", "4",
        "--call-ins", "Lance", "Jerry", "Jason_2", "Vanessa", "Robert_5", "Edwin"
    ]
    
    # Print the command
    print(f"Running command: {' '.join(cmd)}")
    
    # Run the command
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Print the output
        print("\nCommand output:")
        print(result.stdout)
        
        # Print any errors
        if result.stderr:
            print("\nErrors:")
            print(result.stderr)
            
        # Check for success
        if result.returncode == 0:
            print("\nTest completed successfully!")
        else:
            print(f"\nTest failed with return code {result.returncode}")
            
    except Exception as e:
        print(f"Error running test: {e}")
        
if __name__ == "__main__":
    main()