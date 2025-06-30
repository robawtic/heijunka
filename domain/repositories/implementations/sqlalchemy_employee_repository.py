# domain/repositories/implementations/refactored_sqlalchemy_employee_repository.py
from typing import Optional, List, Dict, Tuple
from datetime import date
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, func

from domain.entities.employee import Employee
from domain.models import EmployeeWorkstationModel, EmployeeWorkHistoryModel
from domain.models.EmployeeModel import EmployeeModel
from domain.models.RoleModel import RoleModel
from domain.models.TeamModel import TeamModel
from domain.models.WorkstationModel import WorkstationModel
from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from domain.factories.employee_factory import EmployeeFactory
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception, redact_log_message, log_audit_event
from utilities.logging_factory import get_logger


class SqlAlchemyEmployeeRepository(BaseSqlAlchemyRepository[Employee, EmployeeModel], EmployeeRepositoryInterface):
    """
    SQLAlchemy implementation of the EmployeeRepository interface.

    This repository is responsible for:
    1. Retrieving Employee entities from the database
    2. Persisting Employee entities to the database
    3. Converting between EmployeeModel and Employee using EmployeeFactory

    It does not contain any business logic, which is encapsulated in the domain entities.
    """

    def __init__(self, session_factory):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session_factory: The SQLAlchemy session factory to use for database operations.
        """
        super().__init__(session_factory, EmployeeModel, Employee)
        self.logger = get_logger("heijunka.repositories.employee")
        self.rate_limited_logger = get_logger("heijunka.repositories.employee", rate_limit=True)

    # -------------------------------------------------------------------------
    # Core CRUD Operations
    # -------------------------------------------------------------------------

    def get(self, employee_id: int) -> Optional[Employee]:
        """
        Retrieve an employee by their ID.

        Args:
            employee_id: The ID of the employee to retrieve.

        Returns:
            An employee object if found, None otherwise.

        Raises:
            RepositoryError: If there is an error retrieving the employee.
        """
        try:
            self.logger.info(
                f"Entering EmployeeRepository.get (id={employee_id})",
                extra={
                    "event_type": "employee_lookup",
                    "lookup_type": "id",
                    "employee_id": employee_id
                }
            )

            result = None
            with self.session_scope() as session:
                employee_model = session.query(EmployeeModel).get(employee_id)

                if employee_model is None:
                    self.logger.info(
                        f"No employee found with ID: {employee_id}",
                        extra={
                            "event_type": "employee_lookup_failed",
                            "lookup_type": "id",
                            "employee_id": employee_id,
                            "reason": "not_found"
                        }
                    )
                    return None

                self.logger.info(
                    f"Found employee with ID: {employee_id}",
                    extra={
                        "event_type": "employee_lookup_success",
                        "lookup_type": "id",
                        "employee_id": employee_id
                    }
                )

                self.logger.debug(
                    f"Converting EmployeeModel [id={employee_model.id}] to domain Employee",
                    extra={
                        "event_type": "model_to_domain_conversion",
                        "entity_id": employee_model.id,
                        "entity_type": "Employee"
                    }
                )

                result = self._to_domain(employee_model)

            return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeRepository.get: {error_msg}",
                extra={
                    "event_type": "employee_lookup_error",
                    "lookup_type": "id",
                    "employee_id": employee_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving employee by ID: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in EmployeeRepository.get: {error_msg}",
                extra={
                    "event_type": "employee_lookup_error",
                    "lookup_type": "id",
                    "employee_id": employee_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving employee by ID: {error_msg}")

    def get_all(self) -> List[Employee]:
        """
        Retrieve all employees.

        Returns:
            A list of all employees.

        Raises:
            RepositoryError: If there is an error retrieving the employees.
        """
        try:
            self.logger.info(
                "Entering EmployeeRepository.get_all",
                extra={
                    "event_type": "employees_lookup"
                }
            )

            employees = []
            with self.session_scope() as session:
                employee_models = session.query(EmployeeModel).all()

                employee_count = len(employee_models)
                self.logger.info(
                    f"Found {employee_count} employees",
                    extra={
                        "event_type": "employees_lookup_success",
                        "employee_count": employee_count
                    }
                )

                for employee_model in employee_models:
                    self.logger.debug(
                        f"Converting EmployeeModel [id={employee_model.id}] to domain Employee",
                        extra={
                            "event_type": "model_to_domain_conversion",
                            "entity_id": employee_model.id,
                            "entity_type": "Employee"
                        }
                    )

                    employee = self._to_domain(employee_model)
                    employees.append(employee)

                    self.rate_limited_logger.debug(
                        f"Processed employee: {employee.name}",
                        event_type="employee_processed",
                        identifier=str(employee.id),
                        extra={
                            "employee_id": employee.id,
                            "employee_name": employee.name
                        }
                    )

            return employees
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeRepository.get_all: {error_msg}",
                extra={
                    "event_type": "employees_lookup_error",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving all employees: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in EmployeeRepository.get_all: {error_msg}",
                extra={
                    "event_type": "employees_lookup_error",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving all employees: {error_msg}")

    def get_by_name(self, name: str) -> Optional[Employee]:
        """
        Retrieve an employee by their name (case-insensitive).

        Args:
            name: The name of the employee to retrieve.

        Returns:
            The employee if found, None otherwise.

        Raises:
            RepositoryError: If there is an error retrieving the employee.
        """
        try:
            self.logger.info(
                f"Entering EmployeeRepository.get_by_name (name={name})",
                extra={
                    "event_type": "employee_lookup",
                    "lookup_type": "name",
                    "employee_name": name
                }
            )

            result = None
            with self.session_scope() as session:
                employee_model = session.query(EmployeeModel).filter(
                    func.lower(EmployeeModel.name) == func.lower(name)
                ).first()

                if employee_model is None:
                    self.logger.info(
                        f"No employee found with name: {name}",
                        extra={
                            "event_type": "employee_lookup_failed",
                            "lookup_type": "name",
                            "employee_name": name,
                            "reason": "not_found"
                        }
                    )
                    return None

                self.logger.info(
                    f"Found employee with ID: {employee_model.id}",
                    extra={
                        "event_type": "employee_lookup_success",
                        "lookup_type": "name",
                        "employee_name": name,
                        "employee_id": employee_model.id
                    }
                )

                self.logger.debug(
                    f"Converting EmployeeModel [id={employee_model.id}] to domain Employee",
                    extra={
                        "event_type": "model_to_domain_conversion",
                        "entity_id": employee_model.id,
                        "entity_type": "Employee"
                    }
                )

                result = self._to_domain(employee_model)

            return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeRepository.get_by_name: {error_msg}",
                extra={
                    "event_type": "employee_lookup_error",
                    "lookup_type": "name",
                    "employee_name": name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving employee by name: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in EmployeeRepository.get_by_name: {error_msg}",
                extra={
                    "event_type": "employee_lookup_error",
                    "lookup_type": "name",
                    "employee_name": name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving employee by name: {error_msg}")

    # -------------------------------------------------------------------------
    # Team-Related Operations
    # -------------------------------------------------------------------------

    def get_by_team_id(self, team_id: int) -> List[Employee]:
        """
        Retrieve all employees for a specific team.

        Args:
            team_id: The ID of the team.

        Returns:
            A list of employees belonging to the team.

        Raises:
            RepositoryError: If there is an error retrieving the employees.
        """
        try:
            self.logger.info(
                f"Entering EmployeeRepository.get_by_team_id (team_id={team_id})",
                extra={
                    "event_type": "team_employees_lookup",
                    "team_id": team_id
                }
            )

            employees = []
            with self.session_scope() as session:
                employee_models = session.query(EmployeeModel).filter(
                    EmployeeModel.team_id == team_id
                ).all()

                employee_count = len(employee_models)
                self.logger.info(
                    f"Found {employee_count} employees for team ID: {team_id}",
                    extra={
                        "event_type": "team_employees_lookup_success",
                        "team_id": team_id,
                        "employee_count": employee_count
                    }
                )

                for employee_model in employee_models:
                    self.logger.debug(
                        f"Converting EmployeeModel [id={employee_model.id}] to domain Employee",
                        extra={
                            "event_type": "model_to_domain_conversion",
                            "entity_id": employee_model.id,
                            "entity_type": "Employee"
                        }
                    )
                    employees.append(self._to_domain(employee_model))

            return employees
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeRepository.get_by_team_id: {error_msg}",
                extra={
                    "event_type": "team_employees_lookup_error",
                    "team_id": team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving employees for team: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in EmployeeRepository.get_by_team_id: {error_msg}",
                extra={
                    "event_type": "team_employees_lookup_error",
                    "team_id": team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving employees for team: {error_msg}")

    def get_by_team_ids(self, team_ids: List[int]) -> List[Employee]:
        """
        Retrieve all employees for multiple teams in a single query with eager loading.

        Args:
            team_ids: List of team IDs to fetch employees for.

        Returns:
            List of Employee domain objects.

        Raises:
            RepositoryError: If there is an error retrieving the employees.
        """
        if not team_ids:
            return []

        try:
            self.logger.info(
                f"Entering EmployeeRepository.get_by_team_ids (team_count={len(team_ids)})",
                extra={
                    "event_type": "bulk_employees_lookup",
                    "team_count": len(team_ids)
                }
            )

            employees = []
            # Use SQLAlchemy's selectinload for eager loading related data
            with self.session_scope() as session:
                employee_models = session.query(EmployeeModel).filter(
                    EmployeeModel.team_id.in_(team_ids)
                ).options(
                    selectinload(EmployeeModel.teams),
                    selectinload(EmployeeModel.workstations),
                    selectinload(EmployeeModel.availability),
                    selectinload(EmployeeModel.station_skills)
                ).all()

                employee_count = len(employee_models)
                self.logger.info(
                    f"Found {employee_count} employees for {len(team_ids)} teams with eager loading",
                    extra={
                        "event_type": "bulk_employees_lookup_success",
                        "team_count": len(team_ids),
                        "employee_count": employee_count
                    }
                )

                for employee_model in employee_models:
                    self.logger.debug(
                        f"Converting EmployeeModel [id={employee_model.id}] to domain Employee",
                        extra={
                            "event_type": "model_to_domain_conversion",
                            "entity_id": employee_model.id,
                            "entity_type": "Employee"
                        }
                    )
                    employees.append(self._to_domain(employee_model))

            return employees
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeRepository.get_by_team_ids: {error_msg}",
                extra={
                    "event_type": "bulk_employees_lookup_error",
                    "team_count": len(team_ids),
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving employees for multiple teams: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in EmployeeRepository.get_by_team_ids: {error_msg}",
                extra={
                    "event_type": "bulk_employees_lookup_error",
                    "team_count": len(team_ids),
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving employees for multiple teams: {error_msg}")

    def assign_role(self, employee_id: int, role_name: str, team_id: int) -> Dict[str, str]:
        """
        Assign a role to an employee within a team.

        Args:
            employee_id: The ID of the employee.
            role_name: The name of the role to assign.
            team_id: The ID of the team.

        Returns:
            A dictionary with status and message.

        Raises:
            RepositoryError: If there is an error assigning the role.
        """
        try:
            self.logger.info(
                f"Entering EmployeeRepository.assign_role (employee_id={employee_id}, role_name={role_name}, team_id={team_id})",
                extra={
                    "event_type": "role_assignment",
                    "employee_id": employee_id,
                    "role_name": role_name,
                    "team_id": team_id
                }
            )

            with self.session_scope() as session:
                employee = session.query(EmployeeModel).get(employee_id)
                team = session.query(TeamModel).get(team_id)

                if not employee or not team:
                    self.logger.warning(
                        f"Role assignment failed - employee or team not found",
                        extra={
                            "event_type": "role_assignment_failed",
                            "employee_id": employee_id,
                            "team_id": team_id,
                            "role": role_name,
                            "reason": "entity_not_found"
                        }
                    )
                    return {"status": "error", "message": "Employee or team not found"}

                # Log with redaction
                result = redact_log_message(
                    f"Assigning role '{role_name}' to employee {employee.name} (ID: {employee_id}) in team {team.name} (ID: {team_id})",
                    employee_names=[employee.name],
                    employee_ids=[str(employee_id)],
                    team_names=[team.name],
                    team_ids=[str(team_id)]
                )
                self.logger.info(
                    result.message,
                    extra={
                        "event_type": "role_assignment_attempt",
                        "employee_id": employee_id,
                        "role_name": role_name,
                        "team_id": team_id,
                        "redacted": True,
                        "redacted_fields": result.redacted_fields
                    }
                )

                for team_member in employee.teams:
                    if team_member.team == team:
                        role = session.query(RoleModel).filter_by(role_name=role_name).first()
                        if not role:
                            self.logger.warning(
                                f"Role '{role_name}' not found",
                                extra={
                                    "event_type": "role_assignment_failed",
                                    "employee_id": employee_id,
                                    "team_id": team_id,
                                    "role_name": role_name,
                                    "reason": "role_not_found"
                                }
                            )
                            return {"status": "error", "message": f"Role '{role_name}' not found"}

                        if role in team_member.roles:
                            self.logger.info(
                                redact_log_message(
                                    f"Employee {employee.name} already has role '{role_name}' in team {team.name}",
                                    employee_names=[employee.name],
                                    team_names=[team.name]
                                ).message,
                                extra={
                                    "event_type": "role_assignment_skipped",
                                    "employee_id": employee_id,
                                    "role_name": role_name,
                                    "team_id": team_id,
                                    "reason": "already_assigned"
                                }
                            )
                            return {"status": "exists", "message": f"Already has role '{role_name}'"}

                        team_member.roles.append(role)
                        session.commit()

                        # Log audit event for this security-relevant operation
                        log_audit_event(
                            event_type="role_assignment",
                            message=f"Role '{role_name}' assigned to employee in team",
                            employee_names=[employee.name],
                            employee_ids=[str(employee_id)],
                            team_names=[team.name],
                            team_ids=[str(team_id)],
                            custom_data={"role": role_name}
                        )

                        self.logger.info(
                            redact_log_message(
                                f"Successfully assigned role '{role_name}' to employee {employee.name} in team {team.name}",
                                employee_names=[employee.name],
                                team_names=[team.name]
                            ).message,
                            extra={
                                "event_type": "role_assignment_success",
                                "employee_id": employee_id,
                                "role_name": role_name,
                                "team_id": team_id
                            }
                        )
                        return {"status": "success", "message": f"Role '{role_name}' assigned"}

                self.logger.warning(
                    redact_log_message(
                        f"Employee {employee.name} not in team {team.name}",
                        employee_names=[employee.name],
                        team_names=[team.name]
                    ).message,
                    extra={
                        "event_type": "role_assignment_failed",
                        "employee_id": employee_id,
                        "role_name": role_name,
                        "team_id": team_id,
                        "reason": "not_in_team"
                    }
                )
                return {"status": "error", "message": "Employee not in team"}
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeRepository.assign_role: {error_msg}",
                extra={
                    "event_type": "role_assignment_error",
                    "employee_id": employee_id,
                    "role_name": role_name,
                    "team_id": team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Database error while assigning role: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in EmployeeRepository.assign_role: {error_msg}",
                extra={
                    "event_type": "role_assignment_error",
                    "employee_id": employee_id,
                    "role_name": role_name,
                    "team_id": team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error assigning role: {error_msg}")

    def remove_role(self, employee_id: int, role_name: str, team_id: int) -> Dict[str, str]:
        """
        Remove a role from an employee within a team.

        Args:
            employee_id: The ID of the employee.
            role_name: The name of the role to remove.
            team_id: The ID of the team.

        Returns:
            A dictionary with status and message.

        Raises:
            RepositoryError: If there is an error removing the role.
        """
        try:
            self.logger.info(
                f"Entering EmployeeRepository.remove_role (employee_id={employee_id}, role_name={role_name}, team_id={team_id})",
                extra={
                    "event_type": "role_removal",
                    "employee_id": employee_id,
                    "role_name": role_name,
                    "team_id": team_id
                }
            )

            with self.session_scope() as session:
                employee = session.query(EmployeeModel).get(employee_id)
                team = session.query(TeamModel).get(team_id)

                if not employee or not team:
                    self.logger.warning(
                        f"Role removal failed - employee or team not found",
                        extra={
                            "event_type": "role_removal_failed",
                            "employee_id": employee_id,
                            "team_id": team_id,
                            "role": role_name,
                            "reason": "entity_not_found"
                        }
                    )
                    return {"status": "error", "message": "Employee or team not found"}

                # Log with redaction
                result = redact_log_message(
                    f"Removing role '{role_name}' from employee {employee.name} (ID: {employee_id}) in team {team.name} (ID: {team_id})",
                    employee_names=[employee.name],
                    employee_ids=[str(employee_id)],
                    team_names=[team.name],
                    team_ids=[str(team_id)]
                )
                self.logger.info(
                    result.message,
                    extra={
                        "event_type": "role_removal_attempt",
                        "employee_id": employee_id,
                        "role_name": role_name,
                        "team_id": team_id,
                        "redacted": True,
                        "redacted_fields": result.redacted_fields
                    }
                )

                for team_member in employee.teams:
                    if team_member.team == team:
                        for role in team_member.roles:
                            if role.name == role_name:
                                team_member.roles.remove(role)
                                session.commit()

                                # Log audit event for this security-relevant operation
                                log_audit_event(
                                    event_type="role_removal",
                                    message=f"Role '{role_name}' removed from employee in team",
                                    employee_names=[employee.name],
                                    employee_ids=[str(employee_id)],
                                    team_names=[team.name],
                                    team_ids=[str(team_id)],
                                    custom_data={"role": role_name}
                                )

                                self.logger.info(
                                    redact_log_message(
                                        f"Successfully removed role '{role_name}' from employee {employee.name} in team {team.name}",
                                        employee_names=[employee.name],
                                        team_names=[team.name]
                                    ).message,
                                    extra={
                                        "event_type": "role_removal_success",
                                        "employee_id": employee_id,
                                        "role_name": role_name,
                                        "team_id": team_id
                                    }
                                )
                                return {"status": "success", "message": f"Removed role '{role_name}'"}

                self.logger.warning(
                    redact_log_message(
                        f"Role '{role_name}' not found for employee {employee.name} in team {team.name}",
                        employee_names=[employee.name],
                        team_names=[team.name]
                    ).message,
                    extra={
                        "event_type": "role_removal_failed",
                        "employee_id": employee_id,
                        "role_name": role_name,
                        "team_id": team_id,
                        "reason": "role_not_found"
                    }
                )
                return {"status": "error", "message": f"Role '{role_name}' not found"}
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeRepository.remove_role: {error_msg}",
                extra={
                    "event_type": "role_removal_error",
                    "employee_id": employee_id,
                    "role_name": role_name,
                    "team_id": team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Database error while removing role: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in EmployeeRepository.remove_role: {error_msg}",
                extra={
                    "event_type": "role_removal_error",
                    "employee_id": employee_id,
                    "role_name": role_name,
                    "team_id": team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error removing role: {error_msg}")

    # -------------------------------------------------------------------------
    # Workstation-Related Operations
    # -------------------------------------------------------------------------

    def assign_workstation(self, employee_id: int, workstation_id: int) -> Dict[str, str]:
        """
        Assign a workstation to an employee.

        Args:
            employee_id: The ID of the employee.
            workstation_id: The ID of the workstation.

        Returns:
            A dictionary with status and message.

        Raises:
            RepositoryError: If there is an error assigning the workstation.
        """
        try:
            self.logger.info(
                f"Entering EmployeeRepository.assign_workstation (employee_id={employee_id}, workstation_id={workstation_id})",
                extra={
                    "event_type": "workstation_assignment",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id
                }
            )

            # Verify employee and workstation exist
            with self.session_scope() as session:
                employee = session.query(EmployeeModel).get(employee_id)
                workstation = session.query(WorkstationModel).get(workstation_id)

                if not employee or not workstation:
                    self.logger.warning(
                        f"Workstation assignment failed - employee or workstation not found",
                        extra={
                            "event_type": "workstation_assignment_failed",
                            "employee_id": employee_id,
                            "workstation_id": workstation_id,
                            "reason": "entity_not_found"
                        }
                    )
                    return {"status": "error", "message": "Employee or workstation not found"}

                # Log with redaction
                result = redact_log_message(
                    f"Assigning workstation {workstation.name} (ID: {workstation_id}) to employee {employee.name} (ID: {employee_id})",
                    employee_names=[employee.name],
                    employee_ids=[str(employee_id)],
                    workstation_names=[workstation.name]
                )
                self.logger.info(
                    result.message,
                    extra={
                        "event_type": "workstation_assignment_attempt",
                        "employee_id": employee_id,
                        "workstation_id": workstation_id,
                        "redacted": True,
                        "redacted_fields": result.redacted_fields
                    }
                )

                existing = session.query(EmployeeWorkstationModel).filter_by(
                    employee_id=employee_id,
                    station_id=workstation_id
                ).first()

                if existing:
                    self.logger.info(
                        redact_log_message(
                            f"Employee {employee.name} already assigned to workstation {workstation.name}",
                            employee_names=[employee.name],
                            workstation_names=[workstation.name]
                        ).message,
                        extra={
                            "event_type": "workstation_assignment_skipped",
                            "employee_id": employee_id,
                            "workstation_id": workstation_id,
                            "reason": "already_assigned"
                        }
                    )
                    return {"status": "exists", "message": f"Already assigned to {workstation.name}"}

                new_assignment = EmployeeWorkstationModel(
                    employee_id=employee_id,
                    station_id=workstation_id
                )
                session.add(new_assignment)
                session.commit()

                # Log audit event for this security-relevant operation
                log_audit_event(
                    event_type="workstation_assignment",
                    message=f"Workstation assigned to employee",
                    employee_names=[employee.name],
                    employee_ids=[str(employee_id)],
                    workstation_names=[workstation.name],
                    custom_data={"workstation_id": workstation_id}
                )

                self.logger.info(
                    redact_log_message(
                        f"Successfully assigned workstation {workstation.name} to employee {employee.name}",
                        employee_names=[employee.name],
                        workstation_names=[workstation.name]
                    ).message,
                    extra={
                        "event_type": "workstation_assignment_success",
                        "employee_id": employee_id,
                        "workstation_id": workstation_id
                    }
                )
                return {"status": "success", "message": f"Assigned to {workstation.name}"}
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeRepository.assign_workstation: {error_msg}",
                extra={
                    "event_type": "workstation_assignment_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Database error while assigning workstation: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in EmployeeRepository.assign_workstation: {error_msg}",
                extra={
                    "event_type": "workstation_assignment_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error assigning workstation: {error_msg}")

    def get_work_history(self, employee_id: int, workstation_id: int) -> list:
        """
        Get employee's work history for a specific workstation.

        Args:
            employee_id: The ID of the employee.
            workstation_id: The ID of the workstation.

        Returns:
            A list of work history entries.

        Raises:
            RepositoryError: If there is an error retrieving the work history.
        """
        try:
            self.logger.info(
                f"Entering EmployeeRepository.get_work_history (employee_id={employee_id}, workstation_id={workstation_id})",
                extra={
                    "event_type": "work_history_lookup",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id
                }
            )

            # Get employee and workstation names for better logging
            with self.session_scope() as session:
                employee = session.query(EmployeeModel).get(employee_id)
                workstation = session.query(WorkstationModel).get(workstation_id)

                if employee and workstation:
                    # Log with redaction
                    result = redact_log_message(
                        f"Retrieving work history for employee {employee.name} at workstation {workstation.name}",
                        employee_names=[employee.name],
                        workstation_names=[workstation.name]
                    )
                    self.logger.info(
                        result.message,
                        extra={
                            "event_type": "work_history_lookup_detail",
                            "employee_id": employee_id,
                            "workstation_id": workstation_id,
                            "redacted": True,
                            "redacted_fields": result.redacted_fields
                        }
                    )

            with self.session_scope() as session:
                history = session.query(EmployeeWorkHistoryModel).filter(
                    EmployeeWorkHistoryModel.employee_id == employee_id,
                    EmployeeWorkHistoryModel.station_id == workstation_id
                ).all()

            self.logger.info(
                f"Found {len(history)} work history entries for employee ID: {employee_id} at workstation ID: {workstation_id}",
                extra={
                    "event_type": "work_history_lookup_success",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "entry_count": len(history)
                }
            )
            return history
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeRepository.get_work_history: {error_msg}",
                extra={
                    "event_type": "work_history_lookup_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving work history: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in EmployeeRepository.get_work_history: {error_msg}",
                extra={
                    "event_type": "work_history_lookup_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving work history: {error_msg}")

    def add_work_history(self, employee_id: int, workstation_id: int,
                         worked_date: date, work_period: int, end_flag: bool = False) -> bool:
        """
        Add a work history entry.

        Args:
            employee_id: The ID of the employee.
            workstation_id: The ID of the workstation.
            worked_date: The date the work was performed.
            work_period: The period of the day the work was performed.
            end_flag: Whether this is the end of a work session.

        Returns:
            True if the entry was added successfully, False otherwise.

        Raises:
            RepositoryError: If there is an error adding the work history entry.
        """
        try:
            self.logger.info(
                f"Entering EmployeeRepository.add_work_history (employee_id={employee_id}, workstation_id={workstation_id}, worked_date={worked_date}, work_period={work_period}, end_flag={end_flag})",
                extra={
                    "event_type": "work_history_add",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "worked_date": str(worked_date),
                    "work_period": work_period,
                    "end_flag": end_flag
                }
            )

            # Get employee and workstation names for better logging
            with self.session_scope() as session:
                employee = session.query(EmployeeModel).get(employee_id)
                workstation = session.query(WorkstationModel).get(workstation_id)

                if employee and workstation:
                    # Log with redaction
                    result = redact_log_message(
                        f"Adding work history entry for employee {employee.name} at workstation {workstation.name} on {worked_date} period {work_period}",
                        employee_names=[employee.name],
                        workstation_names=[workstation.name],
                        dates=[str(worked_date)]
                    )
                    self.logger.info(
                        result.message,
                        extra={
                            "event_type": "work_history_add_detail",
                            "employee_id": employee_id,
                            "workstation_id": workstation_id,
                            "worked_date": str(worked_date),
                            "work_period": work_period,
                            "end_flag": end_flag,
                            "redacted": True,
                            "redacted_fields": result.redacted_fields
                        }
                    )
                else:
                    self.logger.warning(
                        f"Adding work history for unknown employee or workstation",
                        extra={
                            "event_type": "work_history_add_warning",
                            "employee_id": employee_id,
                            "workstation_id": workstation_id,
                            "reason": "entity_not_found"
                        }
                    )

                session.add(EmployeeWorkHistoryModel(
                    employee_id=employee_id,
                    station_id=workstation_id,
                    worked_date=worked_date,
                    work_period=work_period,
                    end_flag=end_flag
                ))
                session.commit()

                # Log audit event for this security-relevant operation
                if employee and workstation:
                    log_audit_event(
                        event_type="work_history_added",
                        message=f"Work history entry added for employee at workstation",
                        employee_names=[employee.name],
                        employee_ids=[str(employee_id)],
                        workstation_names=[workstation.name],
                        dates=[str(worked_date)],
                        custom_data={"work_period": work_period, "end_flag": end_flag}
                    )

                self.logger.info(
                    f"Successfully added work history entry for employee ID: {employee_id}",
                    extra={
                        "event_type": "work_history_add_success",
                        "employee_id": employee_id,
                        "workstation_id": workstation_id,
                        "worked_date": str(worked_date),
                        "work_period": work_period,
                        "end_flag": end_flag
                    }
                )
                return True
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeRepository.add_work_history: {error_msg}",
                extra={
                    "event_type": "work_history_add_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "worked_date": str(worked_date) if worked_date else None,
                    "work_period": work_period,
                    "end_flag": end_flag,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error adding work history entry: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in EmployeeRepository.add_work_history: {error_msg}",
                extra={
                    "event_type": "work_history_add_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "worked_date": str(worked_date) if worked_date else None,
                    "work_period": work_period,
                    "end_flag": end_flag,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error adding work history entry: {error_msg}")

    def get_last_worked_date(self, employee_id: int, workstation_id: int) -> Tuple[Optional[date], Optional[int]]:
        """
        Get the last date an employee worked at a specific workstation.

        Args:
            employee_id: The ID of the employee.
            workstation_id: The ID of the workstation.

        Returns:
            A tuple containing the date and period, or (None, None) if no history exists.

        Raises:
            RepositoryError: If there is an error retrieving the last worked date.
        """
        try:
            self.logger.info(
                f"Entering EmployeeRepository.get_last_worked_date (employee_id={employee_id}, workstation_id={workstation_id})",
                extra={
                    "event_type": "last_worked_date_check",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id
                }
            )

            # Get employee and workstation names for better logging
            with self.session_scope() as session:
                employee = session.query(EmployeeModel).get(employee_id)
                workstation = session.query(WorkstationModel).get(workstation_id)

                if employee and workstation:
                    # Log with redaction
                    result = redact_log_message(
                        f"Retrieving last worked date for employee {employee.name} at workstation {workstation.name}",
                        employee_names=[employee.name],
                        workstation_names=[workstation.name]
                    )

                    self.rate_limited_logger.info(
                        result.message,
                        event_type="last_worked_date_check_detail",
                        identifier=f"{employee_id}:{workstation_id}",
                        extra={
                            "employee_id": employee_id,
                            "workstation_id": workstation_id,
                            "redacted": True,
                            "redacted_fields": result.redacted_fields
                        }
                    )

            with self.session_scope() as session:
                entry = session.query(EmployeeWorkHistoryModel).filter(
                    and_(
                        EmployeeWorkHistoryModel.employee_id == employee_id,
                        EmployeeWorkHistoryModel.station_id == workstation_id
                    )
                ).order_by(
                    EmployeeWorkHistoryModel.worked_date.desc(),
                    EmployeeWorkHistoryModel.work_period.desc()
                ).first()

            if entry:
                self.rate_limited_logger.info(
                    f"Found last worked date",
                    event_type="last_worked_date_result",
                    identifier=f"{employee_id}:{workstation_id}",
                    extra={
                        "employee_id": employee_id,
                        "workstation_id": workstation_id,
                        "found": True,
                        "date": str(entry.worked_date),
                        "period": entry.work_period
                    }
                )
                return entry.worked_date, entry.work_period
            else:
                self.rate_limited_logger.info(
                    f"No work history found",
                    event_type="last_worked_date_result",
                    identifier=f"{employee_id}:{workstation_id}",
                    extra={
                        "employee_id": employee_id,
                        "workstation_id": workstation_id,
                        "found": False
                    }
                )
                return None, None
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeRepository.get_last_worked_date: {error_msg}",
                extra={
                    "event_type": "last_worked_date_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving last worked date: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in EmployeeRepository.get_last_worked_date: {error_msg}",
                extra={
                    "event_type": "last_worked_date_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving last worked date: {error_msg}")

    def is_available(self, employee_id: int, date_obj: date, period: Optional[int] = None) -> bool:
        """
        Check if employee is available on the given date and period.

        Args:
            employee_id: The ID of the employee.
            date_obj: The date to check availability for.
            period: Optional period of the day to check.

        Returns:
            True if the employee is available, False otherwise.

        Raises:
            RepositoryError: If there is an error checking availability.
        """
        try:
            self.logger.info(
                f"Entering EmployeeRepository.is_available (employee_id={employee_id}, date={date_obj}, period={period})",
                extra={
                    "event_type": "availability_check",
                    "employee_id": employee_id,
                    "date": str(date_obj),
                    "period": period
                }
            )

            with self.session_scope() as session:
                employee = session.query(EmployeeModel).get(employee_id)
                if not employee:
                    self.logger.warning(
                        "Availability check failed - employee not found",
                        extra={
                            "event_type": "availability_check_failed",
                            "employee_id": employee_id,
                            "reason": "employee_not_found"
                        }
                    )
                    return False

                # Log with redaction using rate-limited logger
                result = redact_log_message(
                    f"Checking availability for employee {employee.name} (ID: {employee_id}) on {date_obj}",
                    employee_names=[employee.name],
                    employee_ids=[str(employee_id)],
                    dates=[str(date_obj)]
                )

                # Use rate-limited logger for this high-frequency operation
                self.rate_limited_logger.info(
                    result.message,
                    event_type="availability_check_detail",
                    identifier=f"{employee_id}:{date_obj}",
                    extra={
                        "employee_id": employee_id,
                        "date": str(date_obj),
                        "period": period,
                        "redacted": True,
                        "redacted_fields": result.redacted_fields
                    }
                )

                # Check availability logic
                is_available = True
                for av in employee.availability:
                    if av.date != date_obj:
                        continue
                    if av.is_call_in or av.is_aro:
                        is_available = False
                        break
                    if av.is_partial and period is not None and av.period == period:
                        is_available = False
                        break

                # Log result with redaction using rate-limited logger
                result = redact_log_message(
                    f"Employee {employee.name} (ID: {employee_id}) is {'available' if is_available else 'not available'} on {date_obj}",
                    employee_names=[employee.name],
                    employee_ids=[str(employee_id)],
                    dates=[str(date_obj)]
                )

                self.rate_limited_logger.info(
                    result.message,
                    event_type="availability_result",
                    identifier=f"{employee_id}:{date_obj}",
                    extra={
                        "employee_id": employee_id,
                        "date": str(date_obj),
                        "period": period,
                        "is_available": is_available,
                        "redacted": True,
                        "redacted_fields": result.redacted_fields
                    }
                )

                return is_available
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error in EmployeeRepository.is_available: {error_msg}",
                extra={
                    "event_type": "availability_check_error",
                    "employee_id": employee_id,
                    "date": str(date_obj) if date_obj else None,
                    "period": period,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error checking employee availability: {error_msg}")
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Unexpected error in EmployeeRepository.is_available: {error_msg}",
                extra={
                    "event_type": "availability_check_error",
                    "employee_id": employee_id,
                    "date": str(date_obj) if date_obj else None,
                    "period": period,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error checking employee availability: {error_msg}")

    # -------------------------------------------------------------------------
    # Conversion Helpers
    # -------------------------------------------------------------------------

    def _to_domain(self, model: EmployeeModel) -> Employee:
        """
        Convert a SQLAlchemy model to a domain entity using the EmployeeFactory.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.

        Raises:
            Exception: If there is an error converting the model.
        """
        try:
            self.logger.debug(
                f"Converting EmployeeModel [id={model.id}] to domain Employee",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "entity_type": "Employee"
                }
            )

            return EmployeeFactory.create_from_model(model)
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting employee model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: Employee) -> EmployeeModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.

        Raises:
            Exception: If there is an error converting the entity.
        """
        try:
            entity_id = entity.id if entity.id is not None else "new"
            self.logger.debug(
                f"Converting Employee domain entity [id={entity_id}] to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "entity_id": entity_id,
                    "entity_type": "Employee"
                }
            )

            model = EmployeeModel(
                id=entity.id,
                name=entity.name,
                team_id=entity.team_id,
                is_active=entity.is_active
            )

            return model
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting employee domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "entity_id": entity.id if entity and hasattr(entity, 'id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: EmployeeModel, entity: Employee) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.

        Raises:
            Exception: If there is an error updating the model.
        """
        try:
            self.logger.debug(
                f"Updating EmployeeModel [id={model.id}] from domain entity",
                extra={
                    "event_type": "model_update",
                    "entity_id": model.id,
                    "entity_type": "Employee"
                }
            )

            # Check for significant changes and log them
            if model.name != entity.name:
                self.logger.info(
                    "Changing employee name",
                    extra={
                        "event_type": "employee_field_change",
                        "entity_id": model.id,
                        "field": "name",
                        "old_value": model.name,
                        "new_value": entity.name
                    }
                )

            if model.team_id != entity.team_id:
                self.logger.info(
                    "Changing employee team",
                    extra={
                        "event_type": "employee_field_change",
                        "entity_id": model.id,
                        "field": "team_id",
                        "old_value": model.team_id,
                        "new_value": entity.team_id
                    }
                )

            if model.is_active != entity.is_active:
                self.logger.info(
                    "Changing employee active status",
                    extra={
                        "event_type": "employee_field_change",
                        "entity_id": model.id,
                        "field": "is_active",
                        "old_value": model.is_active,
                        "new_value": entity.is_active
                    }
                )

            # Update basic fields
            model.name = entity.name
            model.team_id = entity.team_id
            model.is_active = entity.is_active

            # Update timestamp if available
            self._stamp_updated(model)

            self.logger.debug(
                "Successfully updated employee model",
                extra={
                    "event_type": "model_update_success",
                    "entity_id": model.id,
                    "entity_type": "Employee"
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating employee model: {error_msg}",
                extra={
                    "event_type": "model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise
