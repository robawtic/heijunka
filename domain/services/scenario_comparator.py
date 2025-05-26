# domain/services/scenario_comparator.py
from typing import Dict, List, Any, Optional
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import date
import os
import logging

from domain.value_objects.scenario import Scenario
from domain.value_objects.work_assignment import WorkAssignment

logger = logging.getLogger(__name__)

class ScenarioComparator:
    """Utility for comparing results across multiple scenarios."""
    
    def __init__(self, results: Dict[str, Dict[str, Any]]):
        """
        Initialize with scenario results.
        
        Args:
            results: Dictionary mapping scenario names to their results
        """
        self.results = results
        
    def compare_metrics(self, metric_name: str) -> pd.DataFrame:
        """
        Compare a specific metric across all scenarios.
        
        Args:
            metric_name: Name of the metric to compare
            
        Returns:
            DataFrame with comparison results
        """
        comparison = {}
        
        for scenario_name, result in self.results.items():
            metrics = result['metrics']
            if metric_name in metrics:
                comparison[scenario_name] = metrics[metric_name]
                
        return pd.DataFrame(comparison)
    
    def compare_employee_workload(self) -> pd.DataFrame:
        """
        Compare employee workload across scenarios.
        
        Returns:
            DataFrame with employee workload comparison
        """
        data = []
        
        for scenario_name, result in self.results.items():
            metrics = result['metrics']
            for employee_name, count in metrics['assignments_per_employee'].items():
                data.append({
                    'Scenario': scenario_name,
                    'Employee': employee_name,
                    'Assignments': count
                })
                
        return pd.DataFrame(data)
    
    def compare_workstation_utilization(self) -> pd.DataFrame:
        """
        Compare workstation utilization across scenarios.
        
        Returns:
            DataFrame with workstation utilization comparison
        """
        data = []
        
        for scenario_name, result in self.results.items():
            metrics = result['metrics']
            for workstation_name, count in metrics['assignments_per_workstation'].items():
                data.append({
                    'Scenario': scenario_name,
                    'Workstation': workstation_name,
                    'Utilization': count
                })
                
        return pd.DataFrame(data)
    
    def generate_comparison_charts(self, output_dir: str = '.'):
        """
        Generate charts comparing scenarios.
        
        Args:
            output_dir: Directory to save the charts
        """
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Employee workload comparison
        try:
            employee_workload = self.compare_employee_workload()
            plt.figure(figsize=(12, 8))
            employee_pivot = employee_workload.pivot(index='Employee', columns='Scenario', values='Assignments')
            employee_pivot.plot(kind='bar')
            plt.title('Employee Workload Comparison Across Scenarios')
            plt.ylabel('Number of Assignments')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "scenario_employee_workload.png"))
            plt.close()
            logger.info(f"Generated employee workload comparison chart: {os.path.join(output_dir, 'scenario_employee_workload.png')}")
        except Exception as e:
            logger.error(f"Error generating employee workload comparison chart: {str(e)}")
        
        # Workstation utilization comparison
        try:
            workstation_util = self.compare_workstation_utilization()
            plt.figure(figsize=(12, 8))
            workstation_pivot = workstation_util.pivot(index='Workstation', columns='Scenario', values='Utilization')
            workstation_pivot.plot(kind='bar')
            plt.title('Workstation Utilization Comparison Across Scenarios')
            plt.ylabel('Number of Assignments')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "scenario_workstation_utilization.png"))
            plt.close()
            logger.info(f"Generated workstation utilization comparison chart: {os.path.join(output_dir, 'scenario_workstation_utilization.png')}")
        except Exception as e:
            logger.error(f"Error generating workstation utilization comparison chart: {str(e)}")
        
        # Total assignments comparison
        try:
            plt.figure(figsize=(10, 6))
            scenario_names = list(self.results.keys())
            total_assignments = [result['metrics']['total_assignments'] for result in self.results.values()]
            plt.bar(scenario_names, total_assignments)
            plt.title('Total Assignments Comparison')
            plt.ylabel('Number of Assignments')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "scenario_total_assignments.png"))
            plt.close()
            logger.info(f"Generated total assignments comparison chart: {os.path.join(output_dir, 'scenario_total_assignments.png')}")
        except Exception as e:
            logger.error(f"Error generating total assignments comparison chart: {str(e)}")
        
    def generate_comparison_report(self, output_file: str = 'scenario_comparison.csv'):
        """
        Generate a CSV report comparing key metrics across scenarios.
        
        Args:
            output_file: Path to save the CSV report
        """
        # Collect key metrics for each scenario
        data = []
        
        for scenario_name, result in self.results.items():
            scenario = result['scenario']
            metrics = result['metrics']
            
            row = {
                'Scenario': scenario_name,
                'Team ID': scenario.team_id,
                'Start Date': scenario.start_date,
                'Periods': scenario.periods_per_day,
                'Call-ins': len(scenario.call_ins) if scenario.call_ins else 0,
                'Offline': len(scenario.offline) if scenario.offline else 0,
                'Force Complete': scenario.force_complete,
                'Total Assignments': metrics['total_assignments'],
            }
            
            # Add employee assignment metrics if available
            if 'min_employee_assignments' in metrics:
                row['Min Employee Assignments'] = metrics['min_employee_assignments']
                row['Max Employee Assignments'] = metrics['max_employee_assignments']
                row['Avg Employee Assignments'] = metrics['avg_employee_assignments']
                if 'std_dev_employee_assignments' in metrics:
                    row['Std Dev Employee Assignments'] = metrics['std_dev_employee_assignments']
            
            # Add workstation utilization metrics if available
            if 'min_workstation_utilization' in metrics:
                row['Min Workstation Utilization'] = metrics['min_workstation_utilization']
                row['Max Workstation Utilization'] = metrics['max_workstation_utilization']
                row['Avg Workstation Utilization'] = metrics['avg_workstation_utilization']
            
            data.append(row)
            
        # Create DataFrame and save to CSV
        try:
            df = pd.DataFrame(data)
            df.to_csv(output_file, index=False)
            logger.info(f"Generated comparison report: {output_file}")
            return df
        except Exception as e:
            logger.error(f"Error generating comparison report: {str(e)}")
            return pd.DataFrame(data)  # Return DataFrame even if saving fails
    
    def generate_scenario_heatmap(self, output_dir: str = '.'):
        """
        Generate a heatmap comparing key metrics across scenarios.
        
        Args:
            output_dir: Directory to save the output
        """
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Extract key metrics for each scenario
            metrics_data = []
            
            for scenario_name, result in self.results.items():
                metrics = result['metrics']
                
                # Collect available metrics
                row = {'Scenario': scenario_name}
                
                # Add basic metrics
                row['Total Assignments'] = metrics['total_assignments']
                
                # Add employee assignment metrics if available
                if 'min_employee_assignments' in metrics:
                    row['Min Employee Assignments'] = metrics['min_employee_assignments']
                    row['Max Employee Assignments'] = metrics['max_employee_assignments']
                    row['Avg Employee Assignments'] = metrics['avg_employee_assignments']
                    if 'std_dev_employee_assignments' in metrics:
                        row['Employee Assignment Std Dev'] = metrics['std_dev_employee_assignments']
                
                # Add workstation utilization metrics if available
                if 'min_workstation_utilization' in metrics:
                    row['Min Workstation Utilization'] = metrics['min_workstation_utilization']
                    row['Max Workstation Utilization'] = metrics['max_workstation_utilization']
                    row['Avg Workstation Utilization'] = metrics['avg_workstation_utilization']
                
                metrics_data.append(row)
                
            df = pd.DataFrame(metrics_data)
            
            # Create a heatmap of normalized metrics
            metrics_cols = [col for col in df.columns if col != 'Scenario']
            df_norm = df.copy()
            
            # Normalize each metric column
            for col in metrics_cols:
                if df[col].max() > df[col].min():
                    df_norm[col] = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
                else:
                    df_norm[col] = 0
            
            # Create heatmap
            plt.figure(figsize=(12, len(df) * 0.8))
            heatmap_data = df_norm.set_index('Scenario')[metrics_cols]
            
            # Import seaborn for better heatmap
            try:
                import seaborn as sns
                sns.heatmap(heatmap_data, annot=df.set_index('Scenario')[metrics_cols], fmt='.2f', cmap='viridis')
            except ImportError:
                # Fallback to matplotlib if seaborn is not available
                plt.imshow(heatmap_data, cmap='viridis')
                plt.colorbar()
                plt.xticks(range(len(metrics_cols)), metrics_cols, rotation=45)
                plt.yticks(range(len(df)), df['Scenario'])
            
            plt.title('Scenario Comparison Heatmap')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "scenario_metrics_heatmap.png"))
            plt.close()
            logger.info(f"Generated scenario metrics heatmap: {os.path.join(output_dir, 'scenario_metrics_heatmap.png')}")
        except Exception as e:
            logger.error(f"Error generating scenario metrics heatmap: {str(e)}")
    
    def generate_all_analytics(self, output_dir: str = '.'):
        """
        Generate all analytics for scenario comparison.
        
        Args:
            output_dir: Directory to save the output
        """
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate basic comparison charts
        self.generate_comparison_charts(output_dir)
        
        # Generate scenario heatmap
        self.generate_scenario_heatmap(output_dir)
        
        # Generate comparison report
        self.generate_comparison_report(os.path.join(output_dir, "scenario_comparison.csv"))