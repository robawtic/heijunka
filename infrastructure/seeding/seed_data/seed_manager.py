# seed_manager.py
import argparse
import subprocess
from sqlalchemy import text
from sqlalchemy.orm import Session
from domain.models.db import engine, Session as SessionFactory
from domain.models.Base import Base

# Import seeding modules
from infrastructure.seeding.seed_data.powertrain_seed import seed_powertrain_data
# (…other seeds as they’re implemented…)

def reset_database():
    print("Dropping all tables…")

    # Check if we're using PostgreSQL
    if str(engine.url).startswith('postgresql'):
        print("Using PostgreSQL-specific approach to drop tables…")
        from sqlalchemy import inspect
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        # Drop each table (cascade removes FKs)
        with engine.begin() as conn:
            # Defer constraints so we can drop in any order
            conn.execute(text("SET CONSTRAINTS ALL DEFERRED"))
            for t in table_names:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {t} CASCADE"))
                    print(f"Dropped table {t}")
                except Exception as e:
                    print(f"Error dropping table {t}: {e}")
    else:
        # For non-Postgres engines, this is enough:
        Base.metadata.drop_all(engine)

    print("Recreating all tables…")
    Base.metadata.create_all(engine)
    print("Database reset complete (tables recreated).")

    # ───────────────────────────────────────────────────────────────────────
    # Now that the schema matches what your SQLAlchemy models declare,
    # Alembic needs to be told “this is at the latest migration already.”
    # We do that by running: alembic stamp head
    # ───────────────────────────────────────────────────────────────────────
    try:
        # Use subprocess to run the Alembic stamp command. Adjust the path to alembic.ini
        subprocess.check_call(
            ["alembic", "stamp", "head"],
            cwd=".",  # or wherever your alembic.ini lives
        )
        print("Alembic stamped to head—version table is now in sync.")
    except subprocess.CalledProcessError as e:
        print(f"Error stamping Alembic: {e}")
    # ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed the database with department data")
    parser.add_argument(
        "--department",
        type=str,
        choices=["all", "powertrain", "trim", "paint", "body", "materials", "ipc"],
        default="all",
        help="Department to seed",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Reset the database (drop & recreate tables) before seeding",
    )

    args = parser.parse_args()

    if args.reset_db:
        reset_database()

    session = SessionFactory()
    try:
        if args.department in ["all", "powertrain"]:
            print("Seeding Powertrain department data…")
            seed_powertrain_data(session)

        # Add other departments as implemented…
        print("Database seeding complete.")
    finally:
        session.close()

if __name__ == "__main__":
    main()
