import sqlite3
from datetime import datetime

# Connect to the database
conn = sqlite3.connect('heijunka.db')
cursor = conn.cursor()

# Check if the columns already exist
cursor.execute("PRAGMA table_info(teams)")
columns = cursor.fetchall()
column_names = [column[1] for column in columns]
print("Current columns in teams table:", column_names)

# Add the description column if it doesn't exist
if 'description' not in column_names:
    print("Adding description column...")
    cursor.execute("ALTER TABLE teams ADD COLUMN description TEXT")

# Add the created_at column if it doesn't exist
if 'created_at' not in column_names:
    print("Adding created_at column...")
    cursor.execute("ALTER TABLE teams ADD COLUMN created_at TIMESTAMP")

# Add the updated_at column if it doesn't exist
if 'updated_at' not in column_names:
    print("Adding updated_at column...")
    cursor.execute("ALTER TABLE teams ADD COLUMN updated_at TIMESTAMP")

# Update existing rows with current timestamp
current_time = datetime.now().isoformat()
print(f"Updating existing rows with timestamp: {current_time}")
cursor.execute(f"UPDATE teams SET created_at = '{current_time}', updated_at = '{current_time}' WHERE created_at IS NULL")

# Commit the changes
conn.commit()

# Verify the changes
cursor.execute("PRAGMA table_info(teams)")
columns = cursor.fetchall()
column_names = [column[1] for column in columns]
print("Updated columns in teams table:", column_names)

# Close the connection
conn.close()

print("Teams table update completed successfully.")