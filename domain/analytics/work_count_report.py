# domain/analytics/work_count_report.py
"""
This module provides functionality for generating work count reports.
"""
from sqlalchemy import func
import pandas as pd
from domain.models.EmployeeModel import EmployeeModel
from domain.models.WorkstationModel import WorkstationModel
from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel


def generate_work_count_report(session):
    """
    Generates a report showing how many times each employee worked at each station and period.
    
    Args:
        session: SQLAlchemy session to access the database
        
    Returns:
        A pandas DataFrame containing the work count report
    """
    max_period = session.query(func.max(EmployeeWorkHistoryModel.work_period)).scalar()
    if max_period is None:
        print("No data in EmployeeWorkHistory.")
        return None

    # Query the work history to get counts grouped by employee, station, and period
    work_counts = (
        session.query(
            EmployeeModel.name.label("Employee"),
            WorkstationModel.name.label("Station"),
            EmployeeWorkHistoryModel.work_period.label("Period"),
            func.count(EmployeeWorkHistoryModel.id).label("Count")
        )
        .join(EmployeeModel, EmployeeModel.id == EmployeeWorkHistoryModel.employee_id)
        .join(WorkstationModel, WorkstationModel.id == EmployeeWorkHistoryModel.station_id)
        .group_by(EmployeeModel.name, WorkstationModel.name, EmployeeWorkHistoryModel.work_period)
        .order_by(EmployeeModel.name, WorkstationModel.name, EmployeeWorkHistoryModel.work_period)
        .all()
    )

    # Organize the data into a dictionary for tabular formatting
    data = {}
    for record in work_counts:
        employee, station, period, count = record
        if (employee, station) not in data:
            data[(employee, station)] = [0] * max_period
        data[(employee, station)][period - 1] = count

    rows = []
    for (employee, station), period_counts in data.items():
        row = [employee, station] + period_counts
        rows.append(row)

    # Define headers
    headers = ["Employee", "Station"] + [f"Period {i + 1}" for i in range(max_period)]
    pd.set_option('display.max_rows', None)
    df = pd.DataFrame(rows, columns=headers)
    df['Total'] = df.iloc[:, 2:].sum(axis=1)

    totals = df.groupby('Employee').sum().reset_index()
    totals['Station'] = 'Totals'

    final_df = pd.DataFrame(columns=df.columns)

    # Build Table
    for employee in df['Employee'].unique():
        employee_data = df[df['Employee'] == employee]
        total_data = totals[totals['Employee'] == employee]
        final_df = pd.concat([final_df, employee_data, total_data], ignore_index=True)

    print("Employee Work Count Report:")
    print(final_df)
    
    return final_df