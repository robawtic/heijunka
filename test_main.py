import sys
import subprocess

# Run the main.py script with the team name from the error message
team_name = "headsub"
cmd = [sys.executable, "main.py", "--team", team_name]

print(f"Running command: {' '.join(cmd)}")
result = subprocess.run(cmd, capture_output=True, text=True)

# Print the output
print("\nSTDOUT:")
print(result.stdout)

if result.stderr:
    print("\nSTDERR:")
    print(result.stderr)

# Check if the command was successful
if result.returncode == 0:
    print("\nCommand completed successfully!")
else:
    print(f"\nCommand failed with return code {result.returncode}")