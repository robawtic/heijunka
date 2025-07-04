# domain/contexts/workstation_management/services/workstation_validation_service.py
from typing import List, Dict, Any, Optional
import logging

from domain.contexts.workstation_management.entities.workstation import Workstation
from domain.contexts.workstation_management.value_objects.workstation_capacity import WorkstationCapacity
from domain.contexts.workstation_management.value_objects.line_type import LineType
from domain.contexts.workstation_management.repositories.interfaces.workstation_repository import WorkstationRepositoryInterface

logger = logging.getLogger(__name__)


class WorkstationValidationService:
    """
    Domain service responsible for workstation validation and business rules enforcement.
    
    This service encapsulates the business logic for validating workstations,
    checking capacity constraints, and enforcing workstation-related business rules.
    """
    
    def __init__(self, workstation_repository: WorkstationRepositoryInterface):
        """
        Initialize the workstation validation service.
        
        Args:
            workstation_repository: Repository for workstation data access
        """
        self.workstation_repository = workstation_repository
    
    def validate_workstation(self, workstation: Workstation) -> Dict[str, Any]:
        """
        Perform comprehensive validation of a workstation.
        
        Args:
            workstation: The workstation to validate
            
        Returns:
            Dictionary containing validation results
        """
        logger.debug(f"Validating workstation {workstation.id}")
        
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "business_rules": []
        }
        
        # Basic entity validation
        entity_validation = workstation.validate()
        if not entity_validation["is_valid"]:
            validation_results["errors"].extend(entity_validation["errors"])
            validation_results["is_valid"] = False
        
        # Business rule validations
        self._validate_name_uniqueness(workstation, validation_results)
        self._validate_team_assignment(workstation, validation_results)
        self._validate_line_type_consistency(workstation, validation_results)
        self._validate_workstation_properties(workstation, validation_results)
        
        return validation_results
    
    def validate_workstation_capacity(self, capacity: WorkstationCapacity) -> Dict[str, Any]:
        """
        Validate workstation capacity configuration.
        
        Args:
            capacity: The workstation capacity to validate
            
        Returns:
            Dictionary containing validation results
        """
        logger.debug("Validating workstation capacity")
        
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Capacity logic validation
        if capacity.is_understaffed():
            validation_results["warnings"].append(
                f"Workstation is understaffed: {capacity.current_employees}/{capacity.min_employees} minimum"
            )
        
        if capacity.current_employees > capacity.max_employees:
            validation_results["errors"].append(
                f"Current employees ({capacity.current_employees}) exceeds maximum capacity ({capacity.max_employees})"
            )
            validation_results["is_valid"] = False
        
        # Efficiency recommendations
        if not capacity.is_optimally_staffed() and not capacity.is_understaffed():
            if capacity.current_employees < capacity.optimal_employees:
                validation_results["recommendations"].append(
                    f"Consider adding {capacity.needs_additional_staff()} more employees for optimal efficiency"
                )
            elif capacity.current_employees > capacity.optimal_employees:
                validation_results["recommendations"].append(
                    f"Consider reducing staff by {capacity.current_employees - capacity.optimal_employees} for optimal efficiency"
                )
        
        # Capacity utilization warnings
        utilization = capacity.get_capacity_utilization()
        if utilization > 0.9:
            validation_results["warnings"].append(
                f"High capacity utilization ({utilization:.1%}). Consider increasing maximum capacity."
            )
        elif utilization < 0.3:
            validation_results["warnings"].append(
                f"Low capacity utilization ({utilization:.1%}). Consider reducing maximum capacity."
            )
        
        return validation_results
    
    def validate_line_type(self, line_type: LineType) -> Dict[str, Any]:
        """
        Validate line type configuration.
        
        Args:
            line_type: The line type to validate
            
        Returns:
            Dictionary containing validation results
        """
        logger.debug(f"Validating line type {line_type.name}")
        
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check for duplicate qualifications
        if len(line_type.required_qualifications) != len(set(line_type.required_qualifications)):
            validation_results["warnings"].append("Line type has duplicate required qualifications")
        
        # Check for reasonable number of qualifications
        if len(line_type.required_qualifications) > 10:
            validation_results["warnings"].append(
                f"Line type has many required qualifications ({len(line_type.required_qualifications)}). "
                "Consider consolidating or reviewing requirements."
            )
        
        return validation_results
    
    def validate_workstation_assignment(self, workstation: Workstation, team_id: int) -> Dict[str, Any]:
        """
        Validate assignment of a workstation to a team.
        
        Args:
            workstation: The workstation to assign
            team_id: The team ID to assign to
            
        Returns:
            Dictionary containing validation results
        """
        logger.debug(f"Validating workstation {workstation.id} assignment to team {team_id}")
        
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check if workstation is already assigned to a different team
        if workstation.team_id is not None and workstation.team_id != team_id:
            validation_results["warnings"].append(
                f"Workstation is currently assigned to team {workstation.team_id}. "
                f"Reassigning to team {team_id}."
            )
        
        # Check for team capacity (this would require team repository access)
        # For now, we'll add a placeholder validation
        validation_results["business_rules"].append(
            "Team capacity validation should be performed by team management context"
        )
        
        return validation_results
    
    def check_workstation_conflicts(self, workstations: List[Workstation]) -> Dict[str, Any]:
        """
        Check for conflicts between multiple workstations.
        
        Args:
            workstations: List of workstations to check for conflicts
            
        Returns:
            Dictionary containing conflict analysis results
        """
        logger.debug(f"Checking conflicts for {len(workstations)} workstations")
        
        conflict_results = {
            "has_conflicts": False,
            "name_conflicts": [],
            "team_distribution": {},
            "line_type_distribution": {}
        }
        
        # Check for name conflicts within the same team
        team_workstations = {}
        for workstation in workstations:
            if workstation.team_id not in team_workstations:
                team_workstations[workstation.team_id] = []
            team_workstations[workstation.team_id].append(workstation)
        
        for team_id, team_ws_list in team_workstations.items():
            names = [ws.name for ws in team_ws_list]
            if len(names) != len(set(names)):
                conflict_results["has_conflicts"] = True
                duplicates = [name for name in set(names) if names.count(name) > 1]
                conflict_results["name_conflicts"].extend([
                    f"Team {team_id} has duplicate workstation names: {', '.join(duplicates)}"
                ])
        
        # Analyze team distribution
        for team_id, team_ws_list in team_workstations.items():
            conflict_results["team_distribution"][team_id] = len(team_ws_list)
        
        # Analyze line type distribution
        line_type_counts = {}
        for workstation in workstations:
            line_type = workstation.line_type
            line_type_counts[line_type] = line_type_counts.get(line_type, 0) + 1
        conflict_results["line_type_distribution"] = line_type_counts
        
        return conflict_results
    
    def _validate_name_uniqueness(self, workstation: Workstation, validation_results: Dict[str, Any]) -> None:
        """Validate that workstation name is unique within the team."""
        if workstation.team_id is not None:
            team_workstations = self.workstation_repository.get_by_team_id(workstation.team_id)
            existing_names = [ws.name for ws in team_workstations if ws.id != workstation.id]
            
            if workstation.name in existing_names:
                validation_results["errors"].append(
                    f"Workstation name '{workstation.name}' already exists in team {workstation.team_id}"
                )
                validation_results["is_valid"] = False
    
    def _validate_team_assignment(self, workstation: Workstation, validation_results: Dict[str, Any]) -> None:
        """Validate team assignment business rules."""
        if workstation.team_id is None:
            validation_results["warnings"].append("Workstation is not assigned to any team")
        elif workstation.team_id <= 0:
            validation_results["errors"].append("Invalid team ID")
            validation_results["is_valid"] = False
    
    def _validate_line_type_consistency(self, workstation: Workstation, validation_results: Dict[str, Any]) -> None:
        """Validate line type consistency within team."""
        if workstation.team_id is not None and workstation.line_type:
            team_workstations = self.workstation_repository.get_by_team_id(workstation.team_id)
            team_line_types = set(ws.line_type for ws in team_workstations if ws.id != workstation.id and ws.line_type)
            
            if team_line_types and workstation.line_type not in team_line_types:
                validation_results["warnings"].append(
                    f"Workstation line type '{workstation.line_type}' differs from other workstations in team {workstation.team_id}"
                )
    
    def _validate_workstation_properties(self, workstation: Workstation, validation_results: Dict[str, Any]) -> None:
        """Validate workstation property combinations."""
        # Business rule: Heavy job workstations should typically require key skills
        if workstation.is_heavy_job and not workstation.is_key_skill_job:
            validation_results["warnings"].append(
                "Heavy job workstations typically require key skills for safety"
            )
        
        # Business rule: Loading job workstations have specific requirements
        if workstation.is_loading_job:
            validation_results["business_rules"].append(
                "Loading job workstations should be validated for equipment and safety requirements"
            )


class WorkstationValidationError(Exception):
    """Exception raised when workstation validation fails."""
    pass