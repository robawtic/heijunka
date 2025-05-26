import argparse
from sqlalchemy import text
from sqlalchemy.orm import Session
from domain.models.db import engine, Session as SessionFactory
from domain.models.Base import Base

# Import seeding modules
from tmp_seeder_directory.powertrain_seed import seed_powertrain_data
# Import other department seeding functions as they're developed

def reset_database():
    print("Dropping all tables...")

    # Check if we're using PostgreSQL
    if str(engine.url).startswith('postgresql'):
        # For PostgreSQL, we need to handle foreign key constraints
        print("Using PostgreSQL-specific approach to drop tables...")

        # Use SQLAlchemy's inspector to get all table names
        from sqlalchemy import inspect
        inspector = inspect(engine)

        # Get all table names
        table_names = inspector.get_table_names()

        # Create a connection and start a transaction
        with engine.begin() as connection:
            # Disable foreign key constraints for this transaction
            connection.execute(text("SET CONSTRAINTS ALL DEFERRED"))

            # Drop each table
            for table_name in table_names:
                try:
                    connection.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                    print(f"Dropped table {table_name}")
                except Exception as e:
                    print(f"Error dropping table {table_name}: {e}")
    else:
        # For other databases, use the standard approach
        Base.metadata.drop_all(engine)

    print("Recreating all tables...")
    Base.metadata.create_all(engine)
    print("Database reset complete.")

def main():
    parser = argparse.ArgumentParser(description='Seed the database with department data')
    parser.add_argument('--department', type=str, choices=['all', 'powertrain', 'trim', 'paint', 'body', 'materials', 'ipc'],
                        default='all', help='Department to seed')
    parser.add_argument('--reset-db', action='store_true', help='Reset the database before seeding')

    args = parser.parse_args()

    if args.reset_db:
        reset_database()

    session = SessionFactory()

    try:
        if args.department in ['all', 'powertrain']:
            print("Seeding Powertrain department data...")
            seed_powertrain_data(session)

        # Add other departments as they're implemented
        # if args.department in ['all', 'trim']:
        #     print("Seeding Trim department data...")
        #     seed_trim_data(session)

        print("Database seeding complete.")
    finally:
        session.close()

if __name__ == "__main__":
    main()
