# create_tables.py
import os
import importlib
import inspect
from sqlalchemy.ext.declarative import DeclarativeMeta
import sqlite3

# Import the Base class and engine
from domain.models.Base import Base
from domain.models.db import engine

# Get the database path from the engine URL
db_path = str(engine.url).replace('sqlite:///', '')

# Safety check - if database is corrupted, remove it
if os.path.exists(db_path):
    try:
        # Test if database is accessible and not corrupted
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Try to execute a simple query
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        if result[0] != "ok":
            raise sqlite3.DatabaseError("Database integrity check failed")
        conn.close()
    except sqlite3.DatabaseError as e:
        print(f"Detected corrupted database. Removing {db_path}...")
        os.remove(db_path)
        print(f"Corrupted database removed. Reason: {e}")

# Drop all tables first
print("Dropping existing tables...")
try:
    Base.metadata.drop_all(engine)
except Exception as e:
    print(f"Warning: Could not drop tables: {e}")
    print("Proceeding with table creation...")

# Directory containing the model files
models_dir = os.path.join('domain', 'models')

# Import all model classes that inherit from Base
for filename in os.listdir(models_dir):
    if filename.endswith('.py') and filename != '__init__.py' and filename != 'Base.py' and filename != 'db.py':
        module_name = filename[:-3]  # Remove .py extension
        module_path = f'domain.models.{module_name}'

        try:
            # Import the module
            module = importlib.import_module(module_path)

            # Find all classes in the module that inherit from Base
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and isinstance(obj, DeclarativeMeta) and obj != Base:
                    print(f"Found model: {name}")
        except ImportError as e:
            print(f"Error importing {module_path}: {e}")

# Create all tables
print("Creating tables...")
Base.metadata.create_all(engine)
print("Tables created successfully!")