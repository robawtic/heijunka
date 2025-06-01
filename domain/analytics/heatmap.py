# domain/analytics/heatmap.py
"""
This module provides functionality for generating heatmaps of employee work data.

Generates two heatmaps:
 1) Total assignments per employee and station.
 2) Number of days each employee worked the A-B-C combo.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from collections import defaultdict
from datetime import datetime, timedelta
from sqlalchemy import func
from typing import Dict, List, Set, Tuple, Optional
from utilities.secure_logging import redact_log_message

from domain.models.EmployeeModel import EmployeeModel
from domain.models.WorkstationModel import WorkstationModel
from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel
from domain.models.db import Session


class WorkloadAnalysis:
    """
    Class for analyzing employee workload and generating visualizations.
    """

    def __init__(self, session=None):
        """
        Initialize the workload analysis with a database session.

        Args:
            session: SQLAlchemy session to access the database. If None, a new session will be created.
        """
        self.session = session if session is not None else Session()

    def get_employee_station_period_matrix(self):
        """
        Get a matrix of employee-station assignments across all periods.

        Returns:
            A pandas DataFrame with employees as rows and stations as columns.
            Each cell contains a list of counts per period.
        """
        import pandas as pd

        # Get all employees and stations
        employees = self.session.query(EmployeeModel.name).order_by(EmployeeModel.name).all()
        employees = [e[0] for e in employees]

        stations = self.session.query(WorkstationModel.name).order_by(WorkstationModel.name).all()
        stations = [s[0] for s in stations]

        # Get the maximum period
        max_period = self.session.query(func.max(EmployeeWorkHistoryModel.work_period)).scalar() or 0

        # Query all work history
        work_counts = (
            self.session.query(
                EmployeeModel.name.label("employee"),
                WorkstationModel.name.label("station"),
                EmployeeWorkHistoryModel.work_period.label("period"),
                func.count(EmployeeWorkHistoryModel.id).label("count")
            )
            .join(EmployeeModel, EmployeeModel.id == EmployeeWorkHistoryModel.employee_id)
            .join(WorkstationModel, WorkstationModel.id == EmployeeWorkHistoryModel.station_id)
            .group_by(EmployeeModel.name, WorkstationModel.name, EmployeeWorkHistoryModel.work_period)
            .all()
        )

        # Create a dictionary to store counts by employee, station, and period
        counts_by_emp_station_period = defaultdict(lambda: defaultdict(lambda: [0] * max_period))
        for emp, station, period, count in work_counts:
            counts_by_emp_station_period[emp][station][period - 1] = count

        # Create a DataFrame
        df = pd.DataFrame(index=employees)
        df['Employee'] = employees

        for station in stations:
            df[station] = [counts_by_emp_station_period[emp][station] for emp in employees]

        return df

    def generate_heatmaps(self, output_dir='.', 
                          setA={'H010'}, 
                          setB={'M050', 'M090'}, 
                          setC={'H170', 'BW010'}):
        """
        Generate heatmaps for employee-station assignments and ABC combo workdays.

        Args:
            output_dir: Directory to save the heatmap images
            setA: Set of station names in group A
            setB: Set of station names in group B
            setC: Set of station names in group C

        Returns:
            Tuple of (employee_station_heatmap_path, abc_combo_heatmap_path)
        """
        # 1) Employee-Station total assignments heatmap
        df_mat = self.get_employee_station_period_matrix()
        employees = df_mat['Employee'].tolist()
        station_cols = [col for col in df_mat.columns if col != 'Employee']

        # Build matrix of total assignments (sum over all periods)
        mat = np.zeros((len(employees), len(station_cols)), dtype=int)
        for i, emp in enumerate(employees):
            for j, st in enumerate(station_cols):
                counts = df_mat.loc[df_mat['Employee'] == emp, st].iloc[0]
                mat[i, j] = sum(counts)

        plt.figure(figsize=(12, 8))
        im1 = plt.imshow(mat, aspect='auto')
        plt.colorbar(im1, label='Total Assignments')
        plt.xticks(ticks=np.arange(len(station_cols)), labels=station_cols, rotation=45, ha='right')
        plt.yticks(ticks=np.arange(len(employees)), labels=employees)
        plt.title('Total Assignments per Employee and Station')
        plt.tight_layout()

        employee_station_path = f"{output_dir}/employee_station_heatmap.png"
        plt.savefig(employee_station_path)
        print(redact_log_message(f"Saved {employee_station_path}", file_paths=[employee_station_path]))

        # 2) Days with full A-B-C combo heatmap
        # Query all history entries
        recs = (
            self.session.query(
                EmployeeWorkHistoryModel.worked_date,
                EmployeeModel.name.label('Employee'),
                WorkstationModel.name.label('Station')
            )
            .join(EmployeeModel, EmployeeModel.id == EmployeeWorkHistoryModel.employee_id)
            .join(WorkstationModel, WorkstationModel.id == EmployeeWorkHistoryModel.station_id)
            .all()
        )

        # Collect stations worked per employee per date
        emp_dates = defaultdict(lambda: defaultdict(set))
        for date, emp_name, st in recs:
            emp_dates[emp_name][date].add(st)

        # Count days where employee had A, B and C sets all present
        combo_counts = []
        for emp in employees:
            days_with_combo = sum(
                1
                for date, sts in emp_dates[emp].items()
                if (setA & sts) and (setB & sts) and (setC & sts)
            )
            combo_counts.append(days_with_combo)

        arr = np.array(combo_counts).reshape(-1, 1)

        plt.figure(figsize=(4, 8))
        im2 = plt.imshow(arr, aspect='auto')
        plt.colorbar(im2, label='Days with A-B-C Combo')
        plt.xticks([0], ['ABC Combo'])
        plt.yticks(ticks=np.arange(len(employees)), labels=employees)
        plt.title('Days with A-B-C Combo per Employee')
        plt.tight_layout()

        abc_combo_path = f"{output_dir}/abc_combo_heatmap.png"
        plt.savefig(abc_combo_path)
        print(redact_log_message(f"Saved {abc_combo_path}", file_paths=[abc_combo_path]))

        return (employee_station_path, abc_combo_path)

    def generate_workload_balance_chart(self, output_dir='.', year=None):
        """
        Generate a line chart showing how evenly workload is distributed across employees over time.

        Args:
            output_dir: Directory to save the chart image
            year: Year to analyze (default: current year)

        Returns:
            Path to the saved chart image
        """
        # Default to current year if not specified
        if year is None:
            year = datetime.now().year

        # Query total assignments per employee per week
        query = self.session.query(
            func.to_char(EmployeeWorkHistoryModel.worked_date, 'YYYY-IW').label('week'),
            EmployeeModel.name,
            func.count(EmployeeWorkHistoryModel.id).label('count')
        ).join(EmployeeModel).filter(
            func.to_char(EmployeeWorkHistoryModel.worked_date, 'YYYY') == str(year)
        ).group_by('week', EmployeeModel.name).all()

        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(query, columns=['week', 'employee', 'count'])

        # Calculate standard deviation of counts per week
        std_devs = df.groupby('week')['count'].std().fillna(0)
        weeks = std_devs.index.tolist()

        # Plot
        plt.figure(figsize=(12, 6))
        plt.plot(range(len(weeks)), std_devs.values, marker='o')
        plt.title(f'Workload Balance Over Time for {year} (Lower is Better)')
        plt.xlabel('Week')
        plt.ylabel('Standard Deviation of Assignments')
        plt.xticks(range(len(weeks)), weeks, rotation=45)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()

        path = f"{output_dir}/workload_balance_chart_{year}.png"
        plt.savefig(path)
        print(redact_log_message(f"Saved {path}", file_paths=[path]))
        return path

    def generate_rotation_heatmap(self, output_dir='.'):
        """
        Create a heatmap showing how many days pass between an employee's assignments to the same station.

        Args:
            output_dir: Directory to save the heatmap image

        Returns:
            Path to the saved heatmap image
        """
        # Get all employees and stations
        employees = self.session.query(EmployeeModel.name).order_by(EmployeeModel.name).all()
        employees = [e[0] for e in employees]

        stations = self.session.query(WorkstationModel.name).order_by(WorkstationModel.name).all()
        stations = [s[0] for s in stations]

        # Get all assignments sorted by date
        assignments = self.session.query(
            EmployeeModel.name,
            WorkstationModel.name,
            EmployeeWorkHistoryModel.worked_date
        ).join(EmployeeModel).join(
            WorkstationModel, 
            WorkstationModel.id == EmployeeWorkHistoryModel.station_id
        ).order_by(
            EmployeeWorkHistoryModel.worked_date
        ).all()

        # Calculate average days between repeat assignments
        avg_days_between = np.zeros((len(employees), len(stations)))

        for i, emp in enumerate(employees):
            for j, station in enumerate(stations):
                # Get dates this employee worked this station
                dates = sorted([
                    date for e, s, date in assignments 
                    if e == emp and s == station
                ])

                if len(dates) > 1:
                    # Calculate days between assignments
                    days_between = [(dates[k] - dates[k-1]).days for k in range(1, len(dates))]
                    avg_days_between[i, j] = sum(days_between) / len(days_between) if days_between else 0

        # Plot
        plt.figure(figsize=(12, 8))
        im = plt.imshow(avg_days_between, aspect='auto', cmap='viridis')
        plt.colorbar(im, label='Avg Days Between Assignments')
        plt.xticks(ticks=np.arange(len(stations)), labels=stations, rotation=45, ha='right')
        plt.yticks(ticks=np.arange(len(employees)), labels=employees)
        plt.title('Station Rotation Effectiveness')
        plt.tight_layout()

        path = f"{output_dir}/rotation_effectiveness.png"
        plt.savefig(path)
        print(redact_log_message(f"Saved {path}", file_paths=[path]))
        return path

    def generate_fatigue_chart(self, output_dir='.', 
                              high_fatigue_stations={'H010', 'H170', 'BW010', 'M050', 'M090'}):
        """
        Create a chart showing the frequency of high-fatigue days per employee.

        Args:
            output_dir: Directory to save the chart image
            high_fatigue_stations: Set of station names considered high fatigue

        Returns:
            Path to the saved chart image
        """
        # Get all employees
        employees = self.session.query(EmployeeModel.name).order_by(EmployeeModel.name).all()
        employees = [e[0] for e in employees]

        # Query all history entries
        records = self.session.query(
            EmployeeWorkHistoryModel.worked_date,
            EmployeeModel.name,
            WorkstationModel.name
        ).join(EmployeeModel).join(
            WorkstationModel, 
            WorkstationModel.id == EmployeeWorkHistoryModel.station_id
        ).all()

        # Count high fatigue stations per employee per day
        fatigue_counts = defaultdict(list)

        for emp in employees:
            # Group by date
            by_date = defaultdict(set)
            for date, e, station in records:
                if e == emp:
                    by_date[date].add(station)

            # Count high fatigue stations per day
            for date, stations in by_date.items():
                count = len(stations & high_fatigue_stations)
                fatigue_counts[emp].append(count)

        # Calculate distribution of fatigue days
        fatigue_dist = []
        for emp in employees:
            counts = fatigue_counts[emp]
            if counts:
                # Count days with 0, 1, 2, 3+ high fatigue stations
                dist = [
                    sum(1 for c in counts if c == 0),
                    sum(1 for c in counts if c == 1),
                    sum(1 for c in counts if c == 2),
                    sum(1 for c in counts if c >= 3)
                ]
                # Convert to percentages
                total = sum(dist)
                dist = [100 * d / total for d in dist] if total > 0 else [0, 0, 0, 0]
                fatigue_dist.append(dist)
            else:
                fatigue_dist.append([0, 0, 0, 0])

        # Plot
        labels = ['0 stations', '1 station', '2 stations', '3+ stations']
        x = np.arange(len(employees))
        width = 0.2

        plt.figure(figsize=(12, 8))
        for i in range(4):
            plt.bar(x + i*width, [d[i] for d in fatigue_dist], width, label=labels[i])

        plt.xlabel('Employee')
        plt.ylabel('Percentage of Days')
        plt.title('Distribution of High-Fatigue Workdays')
        plt.xticks(x + 1.5*width, employees, rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()

        path = f"{output_dir}/fatigue_distribution.png"
        plt.savefig(path)
        print(redact_log_message(f"Saved {path}", file_paths=[path]))
        return path

    def generate_calendar_heatmap(self, output_dir='.', year=None):
        """
        Create a calendar heatmap showing team workload intensity by day.

        Args:
            output_dir: Directory to save the heatmap image
            year: Year to analyze (default: current year)

        Returns:
            Path to the saved heatmap image or None if calmap can't be imported
        """
        try:
            import calmap
        except ImportError:
            try:
                print("Warning: calmap package not installed. Installing it...")
                import subprocess
                subprocess.check_call(["pip", "install", "calmap"])
                import calmap
            except (ImportError, subprocess.CalledProcessError) as e:
                print(f"Error importing calmap: {e}")
                print("Calendar heatmap will not be generated.")
                return None

        # Default to current year if not specified
        if year is None:
            year = datetime.now().year

        # Query assignment counts by date
        query = self.session.query(
            EmployeeWorkHistoryModel.worked_date,
            func.count(EmployeeWorkHistoryModel.id)
        ).filter(
            func.to_char(EmployeeWorkHistoryModel.worked_date, 'YYYY') == str(year)
        ).group_by(EmployeeWorkHistoryModel.worked_date).all()

        # Convert to pandas Series
        if query:
            dates, counts = zip(*query)
            series = pd.Series(counts, index=pd.DatetimeIndex(dates))

            # Create a complete date range for the year
            date_range = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31', freq='D')
            # Reindex the series to include all days, filling missing values with 0
            series = series.reindex(date_range, fill_value=0)

            # Plot
            plt.figure(figsize=(16, 10))
            calmap.yearplot(series, year=year)
            plt.title(f'Team Workload Calendar View - {year}')
            plt.tight_layout()

            path = f"{output_dir}/calendar_heatmap_{year}.png"
            plt.savefig(path)
            print(f"Saved calendar heatmap to {path}")
            return path

        else:
            print(redact_log_message(f"No data available for calendar heatmap for year {year}", dates=[str(year)]))
            return None


def generate_heatmaps(output_dir='.', session=None):
    """
    Convenience function to generate heatmaps.

    Args:
        output_dir: Directory to save the heatmap images
        session: SQLAlchemy session to access the database. If None, a new session will be created.

    Returns:
        Tuple of (employee_station_heatmap_path, abc_combo_heatmap_path)
    """
    wa = WorkloadAnalysis(session)
    return wa.generate_heatmaps(output_dir)


def generate_advanced_analytics(output_dir='.', session=None, year=None):
    """
    Convenience function to generate all advanced analytics visualizations.

    Args:
        output_dir: Directory to save the visualization images
        session: SQLAlchemy session to access the database. If None, a new session will be created.
        year: Year to analyze for time-based visualizations (default: current year)

    Returns:
        Dictionary of paths to the generated visualization images
    """
    wa = WorkloadAnalysis(session)

    # Generate all visualizations
    balance_path = wa.generate_workload_balance_chart(output_dir, year)
    rotation_path = wa.generate_rotation_heatmap(output_dir)
    fatigue_path = wa.generate_fatigue_chart(output_dir)
    calendar_path = wa.generate_calendar_heatmap(output_dir, year)

    # Return paths to all generated files
    return {
        'workload_balance': balance_path,
        'rotation_effectiveness': rotation_path,
        'fatigue_analysis': fatigue_path,
        'calendar_heatmap': calendar_path
    }
