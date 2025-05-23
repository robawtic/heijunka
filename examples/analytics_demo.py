#!/usr/bin/env python3
"""
analytics_demo.py

Demonstrates the use of the analytics functionality in the Heijunka application.

Usage:
    python examples/analytics_demo.py [--team TEAM_NAME] [--output-dir OUTPUT_DIR]

Options:
    --team TEAM_NAME       Name of the team to analyze (default: all teams) 
    --output-dir OUTPUT_DIR  Directory to save output files (default: current directory)
"""
import argparse
import os
import sqlite3
import sys

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from sqlalchemy import inspect
from domain.models.db import Session, engine
from domain.models.Base import Base
from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel
from domain.analytics.work_count_report import generate_work_count_report
from domain.analytics.heatmap import generate_heatmaps, generate_advanced_analytics, WorkloadAnalysis
from datetime import datetime


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate analytics reports and visualizations')
    parser.add_argument('--team', help='Name of the team to analyze (default: all teams)')
    parser.add_argument('--output-dir', default=os.path.dirname(os.path.abspath(__file__)),
                        help='Directory to save output files (default: current script directory)')
    parser.add_argument('--year', type=int, default=datetime.now().year,
                        help='Year to analyze for time-based visualizations (default: current year)')
    parser.add_argument('--advanced', action='store_true',
                        help='Generate advanced analytics visualizations')
    return parser.parse_args()


def ensure_tables_exist():
    """Ensure that the required database tables exist."""
    # Change to project root directory before importing models
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)

    from domain.models.EmployeeModel import EmployeeModel
    from domain.models.WorkstationModel import WorkstationModel

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    required_tables = ['employee_work_history', 'employees', 'workstations']
    missing_tables = [table for table in required_tables if table not in existing_tables]

    if missing_tables:
        print(f"Missing tables: {', '.join(missing_tables)}. Creating required tables...")
        # Create all tables to ensure proper relationships
        Base.metadata.create_all(engine)
        print("Tables created successfully.")
    else:
        print("Required tables already exist.")


def main():
    """Main function to demonstrate analytics functionality."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.path.dirname(script_dir))  # Change to parent directory for database

    args = parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Ensure required tables exist
    ensure_tables_exist()

    # Create a database session
    session = Session()

    try:
        # Generate work count report
        print("\n=== Generating Work Count Report ===\n")
        df = generate_work_count_report(session)

        if df is not None:
            # Save the report to a CSV file
            csv_path = os.path.join(args.output_dir, 'work_count_report.csv')
            df.to_csv(csv_path, index=False)
            print(f"\nWork count report saved to {csv_path}")

        # Generate heatmaps
        print("\n=== Generating Heatmaps ===\n")
        employee_station_path, abc_combo_path = generate_heatmaps(args.output_dir, session)

        # List of generated files
        generated_files = []
        if df is not None:
            generated_files.append(os.path.basename(csv_path))
        generated_files.append(os.path.basename(employee_station_path))
        generated_files.append(os.path.basename(abc_combo_path))

        # Generate advanced analytics if requested
        if args.advanced:
            print("\n=== Generating Advanced Analytics ===\n")

            # Generate all advanced analytics
            print("Generating advanced analytics visualizations...")
            advanced_paths = generate_advanced_analytics(
                args.output_dir, session, args.year)

            # Add paths to the list of generated files
            for name, path in advanced_paths.items():
                if path:  # Some paths might be None if no data is available
                    generated_files.append(os.path.basename(path))

        print("\nAnalytics generation complete!")
        print(f"Files saved to {args.output_dir}:")
        for file in generated_files:
            print(f"- {file}")

    finally:
        # Close the session
        session.close()


if __name__ == '__main__':
    main()
