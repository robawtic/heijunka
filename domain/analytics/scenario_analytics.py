# domain/analytics/scenario_analytics.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Optional
import os
import logging

from domain.analytics.heatmap import WorkloadAnalysis
from domain.services.scenario_comparator import ScenarioComparator

logger = logging.getLogger(__name__)

class ScenarioAnalytics:
    """Advanced analytics for scenario comparison."""
    
    def __init__(self, results: Dict[str, Dict[str, Any]], session=None):
        """
        Initialize with scenario results.
        
        Args:
            results: Dictionary mapping scenario names to their results
            session: Database session for additional analytics
        """
        self.results = results
        self.session = session
        self.comparator = ScenarioComparator(results)
        self.workload_analysis = WorkloadAnalysis(session) if session else None
        
    def generate_advanced_analytics(self, output_dir: str = '.'):
        """
        Generate advanced analytics for scenario comparison.
        
        Args:
            output_dir: Directory to save the output
        """
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate basic comparison analytics
        self.comparator.generate_all_analytics(output_dir)
        
        # Generate advanced analytics if workload analysis is available
        if self.workload_analysis:
            self._generate_workload_distribution_chart(output_dir)
            self._generate_station_rotation_heatmap(output_dir)
            self._generate_fatigue_distribution_chart(output_dir)
    
    def _generate_workload_distribution_chart(self, output_dir: str):
        """
        Generate a chart showing the distribution of workload across employees for each scenario.
        
        Args:
            output_dir: Directory to save the output
        """
        try:
            # Get employee workload data
            employee_workload = self.comparator.compare_employee_workload()
            
            # Create a violin plot for each scenario
            plt.figure(figsize=(12, 8))
            sns.violinplot(x='Scenario', y='Assignments', data=employee_workload)
            plt.title('Employee Workload Distribution Across Scenarios')
            plt.ylabel('Number of Assignments')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "scenario_workload_distribution.png"))
            plt.close()
            logger.info(f"Generated workload distribution chart: {os.path.join(output_dir, 'scenario_workload_distribution.png')}")
        except Exception as e:
            logger.error(f"Error generating workload distribution chart: {str(e)}")
    
    def _generate_station_rotation_heatmap(self, output_dir: str):
        """
        Generate a heatmap showing station rotation effectiveness for each scenario.
        
        Args:
            output_dir: Directory to save the output
        """
        try:
            # For each scenario, calculate how many different stations each employee works at
            data = []
            
            for scenario_name, result in self.results.items():
                assignments = result['assignments']
                
                # Group by employee and count unique workstations
                employee_stations = {}
                for assignment in assignments:
                    emp_id = assignment.employee.id
                    ws_id = assignment.workstation.id
                    
                    if emp_id not in employee_stations:
                        employee_stations[emp_id] = set()
                    
                    employee_stations[emp_id].add(ws_id)
                
                # Calculate station rotation metrics
                for emp_id, stations in employee_stations.items():
                    emp_name = next((a.employee.name for a in assignments if a.employee.id == emp_id), f"Employee {emp_id}")
                    data.append({
                        'Scenario': scenario_name,
                        'Employee': emp_name,
                        'Unique Stations': len(stations)
                    })
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Create heatmap
            if not df.empty:
                plt.figure(figsize=(12, 10))
                pivot_table = df.pivot(index='Employee', columns='Scenario', values='Unique Stations')
                sns.heatmap(pivot_table, annot=True, cmap='viridis', fmt='d')
                plt.title('Station Rotation Effectiveness Across Scenarios')
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, "scenario_station_rotation.png"))
                plt.close()
                logger.info(f"Generated station rotation heatmap: {os.path.join(output_dir, 'scenario_station_rotation.png')}")
        except Exception as e:
            logger.error(f"Error generating station rotation heatmap: {str(e)}")
    
    def _generate_fatigue_distribution_chart(self, output_dir: str):
        """
        Generate a chart showing the distribution of consecutive assignments to the same station.
        
        Args:
            output_dir: Directory to save the output
        """
        try:
            # For each scenario, calculate consecutive assignments to the same station
            data = []
            
            for scenario_name, result in self.results.items():
                assignments = result['assignments']
                
                # Sort assignments by employee, date, and period
                sorted_assignments = sorted(
                    assignments, 
                    key=lambda a: (a.employee.id, a.period.date, a.period.period)
                )
                
                # Calculate consecutive assignments
                consecutive_counts = []
                current_emp = None
                current_ws = None
                current_count = 0
                
                for assignment in sorted_assignments:
                    if assignment.employee.id != current_emp or assignment.workstation.id != current_ws:
                        if current_count > 0:
                            consecutive_counts.append(current_count)
                        current_emp = assignment.employee.id
                        current_ws = assignment.workstation.id
                        current_count = 1
                    else:
                        current_count += 1
                
                # Add the last count
                if current_count > 0:
                    consecutive_counts.append(current_count)
                
                # Add data for this scenario
                for count in consecutive_counts:
                    data.append({
                        'Scenario': scenario_name,
                        'Consecutive Assignments': count
                    })
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Create chart
            if not df.empty:
                plt.figure(figsize=(12, 8))
                sns.boxplot(x='Scenario', y='Consecutive Assignments', data=df)
                plt.title('Distribution of Consecutive Assignments to Same Station')
                plt.ylabel('Number of Consecutive Assignments')
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, "scenario_fatigue_distribution.png"))
                plt.close()
                logger.info(f"Generated fatigue distribution chart: {os.path.join(output_dir, 'scenario_fatigue_distribution.png')}")
        except Exception as e:
            logger.error(f"Error generating fatigue distribution chart: {str(e)}")