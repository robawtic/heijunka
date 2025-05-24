import sqlite3

# Connect to the database
conn = sqlite3.connect('heijunka.db')
cursor = conn.cursor()

# Query the schema information for the employee_availability table
cursor.execute("PRAGMA table_info(employee_availability)")
columns = cursor.fetchall()

# Print the column information
print("Columns in employee_availability table:")
for column in columns:
    print(f"  {column[1]} ({column[2]})")

# Close the connection
conn.close()