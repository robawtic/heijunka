from contextlib import contextmanager
from typing import Optional, List, Dict, Tuple, Generator
from datetime import date
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.entities.employee import Employee
from domain.models import EmployeeWorkstationModel, EmployeeWorkHistoryModel
from domain.models.EmployeeModel import EmployeeModel
from domain.models.RoleModel import RoleModel
from domain.models.TeamModel import TeamModel
from domain.models.WorkstationModel import WorkstationModel
from domain.repositories.interfaces.employee_repository import EmployeeRepositoryInterface
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import redact_log_message, sanitize_exception, log_audit_event
from utilities.logging_factory import get_logger


class SqlAlchemyEmployeeRepository(BaseSqlAlchemyRepository[Employee, EmployeeModel], EmployeeRepositoryInterface):
    def __init__(self, session: Session):
        super().__init__(session, EmployeeModel, Employee)
        self.logger = get_logger("heijunka.repositories.employee")
        self.rate_limited_logger = get_logger("heijunka.repositories.employee", rate_limit=True)

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        try:
            yield self._session
            self._session.commit()
        except SQLAlchemyError as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Database operation failed: {error_msg}",
                extra={
                    "event_type": "database_error",
                    "error_type": type(e).__name__,
                    "repository": "employee"
                }
            )
            raise RepositoryError(f"Database operation failed: {error_msg}")
        except Exception as e:
            self._session.rollback()
            self.logger.error(
                f"Unexpected error in employee repository: {sanitize_exception(e)}",
                extra={
                    "event_type": "unexpected_error",
                    "error_type": type(e).__name__,
                    "repository": "employee"
                }
            )
            raise

    def get_by_team_id(self, team_id: int) -> List[Employee]:
        """Retrieve all employees for a specific team and return as domain entities."""
        self.logger.info(
            f"Retrieving employees for team ID: {team_id}",
            extra={
                "event_type": "team_employees_lookup",
                "team_id": team_id
            }
        )
        try:
            employee_models = self._session.query(EmployeeModel).filter(
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
            return [model.to_domain() for model in employee_models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving employees for team ID {team_id}: {error_msg}",
                extra={
                    "event_type": "team_employees_lookup_error",
                    "team_id": team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving employees for team: {error_msg}")

    def get_by_team_ids(self, team_ids: List[int]) -> List[Employee]:
        """Retrieve all employees for multiple teams in a single query."""
        if not team_ids:
            return []

        self.logger.info(
            f"Retrieving employees for {len(team_ids)} teams",
            extra={
                "event_type": "bulk_employees_lookup",
                "team_count": len(team_ids)
            }
        )

        try:
            # Use SQLAlchemy's in_() for efficient bulk fetching
            employee_models = self._session.query(EmployeeModel).filter(
                EmployeeModel.team_id.in_(team_ids)
            ).all()

            employee_count = len(employee_models)
            self.logger.info(
                f"Found {employee_count} employees for {len(team_ids)} teams",
                extra={
                    "event_type": "bulk_employees_lookup_success",
                    "team_count": len(team_ids),
                    "employee_count": employee_count
                }
            )

            return [model.to_domain() for model in employee_models]
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving employees for multiple teams: {error_msg}",
                extra={
                    "event_type": "bulk_employees_lookup_error",
                    "team_count": len(team_ids),
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving employees for multiple teams: {error_msg}")

    def is_available(self, employee_id: int, date_obj: date, period: Optional[int] = None) -> bool:
        """Check if employee is available on the given date and period."""
        try:
            employee = self._session.query(EmployeeModel).get(employee_id)
            if not employee:
                self.logger.warning("Availability check failed - employee not found", 
                                   extra={
                                       "event_type": "availability_check_failed",
                                       "employee_id": employee_id,
                                       "reason": "employee_not_found"
                                   })
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
                event_type="availability_check",
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
                f"Error checking availability for employee ID {employee_id}: {error_msg}",
                extra={
                    "event_type": "availability_check_error",
                    "employee_id": employee_id,
                    "error_type": type(e).__name__,
                    "date": str(date_obj) if date_obj else None,
                    "period": period
                }
            )
            raise RepositoryError(f"Error checking employee availability: {error_msg}")

    def assign_role(self, employee_id: int, role_name: str, team_id: int) -> Dict[str, str]:
        """Assign a role to an employee within a team."""
        try:
            employee = self._session.query(EmployeeModel).get(employee_id)
            team = self._session.query(TeamModel).get(team_id)

            if not employee or not team:
                self.logger.warning(
                    f"Role assignment failed - employee or team not found",
                    extra={"employee_id": employee_id, "team_id": team_id, "role": role_name}
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
            self.logger.info(result.message)

            for team_member in employee.teams:
                if team_member.team == team:
                    role = self._session.query(RoleModel).filter_by(role_name=role_name).first()
                    if not role:
                        self.logger.warning(f"Role '{role_name}' not found", 
                                          extra={"employee_id": employee_id, "team_id": team_id})
                        return {"status": "error", "message": f"Role '{role_name}' not found"}

                    if role in team_member.roles:
                        self.logger.info(
                            redact_log_message(
                                f"Employee {employee.name} already has role '{role_name}' in team {team.name}",
                                employee_names=[employee.name],
                                team_names=[team.name]
                            ).message
                        )
                        return {"status": "exists", "message": f"Already has role '{role_name}'"}

                    team_member.roles.append(role)
                    self._session.commit()

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
                        ).message
                    )
                    return {"status": "success", "message": f"Role '{role_name}' assigned"}

            self.logger.warning(
                redact_log_message(
                    f"Employee {employee.name} not in team {team.name}",
                    employee_names=[employee.name],
                    team_names=[team.name]
                ).message
            )
            return {"status": "error", "message": "Employee not in team"}
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(f"Database error while assigning role: {error_msg}")
            raise RepositoryError(f"Database error while assigning role: {error_msg}")

    def remove_role(self, employee_id: int, role_name: str, team_id: int) -> Dict[str, str]:
        """Remove a role from an employee within a team."""
        try:
            employee = self._session.query(EmployeeModel).get(employee_id)
            team = self._session.query(TeamModel).get(team_id)

            if not employee or not team:
                self.logger.warning(
                    f"Role removal failed - employee or team not found",
                    extra={"employee_id": employee_id, "team_id": team_id, "role": role_name}
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
            self.logger.info(result.message)

            for team_member in employee.teams:
                if team_member.team == team:
                    for role in team_member.roles:
                        if role.name == role_name:
                            team_member.roles.remove(role)
                            self._session.commit()

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
                                ).message
                            )
                            return {"status": "success", "message": f"Removed role '{role_name}'"}

            self.logger.warning(
                redact_log_message(
                    f"Role '{role_name}' not found for employee {employee.name} in team {team.name}",
                    employee_names=[employee.name],
                    team_names=[team.name]
                ).message
            )
            return {"status": "error", "message": f"Role '{role_name}' not found"}
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(f"Database error while removing role: {error_msg}")
            raise RepositoryError(f"Database error while removing role: {error_msg}")

    def assign_workstation(self, employee_id: int, workstation_id: int) -> Dict[str, str]:
        """Assign a workstation to an employee."""
        try:
            # Verify employee and workstation exist
            employee = self._session.query(EmployeeModel).get(employee_id)
            workstation = self._session.query(WorkstationModel).get(workstation_id)

            if not employee or not workstation:
                self.logger.warning(
                    f"Workstation assignment failed - employee or workstation not found",
                    extra={"employee_id": employee_id, "workstation_id": workstation_id}
                )
                return {"status": "error", "message": "Employee or workstation not found"}

            # Log with redaction
            result = redact_log_message(
                f"Assigning workstation {workstation.name} (ID: {workstation_id}) to employee {employee.name} (ID: {employee_id})",
                employee_names=[employee.name],
                employee_ids=[str(employee_id)],
                workstation_names=[workstation.name]
            )
            self.logger.info(result.message)

            existing = self._session.query(EmployeeWorkstationModel).filter_by(
                employee_id=employee_id,
                station_id=workstation_id
            ).first()

            if existing:
                self.logger.info(
                    redact_log_message(
                        f"Employee {employee.name} already assigned to workstation {workstation.name}",
                        employee_names=[employee.name],
                        workstation_names=[workstation.name]
                    ).message
                )
                return {"status": "exists", "message": f"Already assigned to {workstation.name}"}

            new_assignment = EmployeeWorkstationModel(
                employee_id=employee_id,
                station_id=workstation_id
            )
            self._session.add(new_assignment)
            self._session.commit()

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
                ).message
            )
            return {"status": "success", "message": f"Assigned to {workstation.name}"}

        except SQLAlchemyError as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(f"Database error while assigning workstation: {error_msg}")
            raise RepositoryError(f"Database error while assigning workstation: {error_msg}")

    def get_work_history(self, employee_id: int, workstation_id: int) -> list:
        """Get employee's work history for a specific workstation."""
        try:
            self.logger.info(f"Retrieving work history for employee ID: {employee_id} at workstation ID: {workstation_id}")

            # Get employee and workstation names for better logging
            employee = self._session.query(EmployeeModel).get(employee_id)
            workstation = self._session.query(WorkstationModel).get(workstation_id)

            if employee and workstation:
                # Log with redaction
                result = redact_log_message(
                    f"Retrieving work history for employee {employee.name} at workstation {workstation.name}",
                    employee_names=[employee.name],
                    workstation_names=[workstation.name]
                )
                self.logger.info(result.message)

            history = self._session.query(EmployeeWorkHistoryModel).filter(
                EmployeeWorkHistoryModel.employee_id == employee_id,
                EmployeeWorkHistoryModel.station_id == workstation_id
            ).all()

            self.logger.info(f"Found {len(history)} work history entries for employee ID: {employee_id} at workstation ID: {workstation_id}")
            return history
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(f"Error retrieving work history: {error_msg}")
            raise RepositoryError(f"Error retrieving work history: {error_msg}")

    def add_work_history(self, employee_id: int, workstation_id: int,
                         worked_date: date, work_period: int, end_flag: bool = False) -> bool:
        """Add a work history entry."""
        try:
            # Get employee and workstation names for better logging
            employee = self._session.query(EmployeeModel).get(employee_id)
            workstation = self._session.query(WorkstationModel).get(workstation_id)

            if employee and workstation:
                # Log with redaction
                result = redact_log_message(
                    f"Adding work history entry for employee {employee.name} at workstation {workstation.name} on {worked_date} period {work_period}",
                    employee_names=[employee.name],
                    workstation_names=[workstation.name],
                    dates=[str(worked_date)]
                )
                self.logger.info(result.message)
            else:
                self.logger.warning(
                    f"Adding work history for unknown employee or workstation",
                    extra={"employee_id": employee_id, "workstation_id": workstation_id}
                )

            self._session.add(EmployeeWorkHistoryModel(
                employee_id=employee_id,
                station_id=workstation_id,
                worked_date=worked_date,
                work_period=work_period,
                end_flag=end_flag
            ))
            self._session.commit()

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

            self.logger.info(f"Successfully added work history entry for employee ID: {employee_id}")
            return True
        except SQLAlchemyError as e:
            self._session.rollback()
            error_msg = sanitize_exception(e)
            self.logger.error(f"Error adding work history entry: {error_msg}")
            return False

    def get_last_worked_date(self, employee_id: int,
                             workstation_id: int) -> Tuple[Optional[date], Optional[int]]:
        """Get the last date an employee worked at a specific workstation."""
        try:
            # Use rate-limited logger for this high-frequency operation
            self.rate_limited_logger.info(
                f"Retrieving last worked date",
                event_type="last_worked_date_check",
                identifier=f"{employee_id}:{workstation_id}",
                extra={
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "operation": "get_last_worked_date"
                }
            )

            # Get employee and workstation names for better logging
            employee = self._session.query(EmployeeModel).get(employee_id)
            workstation = self._session.query(WorkstationModel).get(workstation_id)

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

            entry = self._session.query(EmployeeWorkHistoryModel).filter(
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
                f"Error retrieving last worked date: {error_msg}",
                extra={
                    "event_type": "last_worked_date_error",
                    "employee_id": employee_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving last worked date: {error_msg}")

    def _to_domain(self, model: EmployeeModel) -> Employee:
        """Convert a SQLAlchemy model to a domain entity using factory."""
        from domain.factories.employee_factory import EmployeeFactory
        return EmployeeFactory.create_from_model(model)

    def _to_model(self, entity: Employee) -> EmployeeModel:
        """Convert a domain entity to a SQLAlchemy model."""
        model = EmployeeModel(
            id=entity.id,
            name=entity.name,
            team_id=entity.team_id,
            is_active=entity.is_active
        )
        return model

    def _update_model(self, model: EmployeeModel, entity: Employee) -> None:
        """Update a SQLAlchemy model with values from a domain entity."""
        model.name = entity.name
        model.team_id = entity.team_id
        model.is_active = entity.is_active
        # Roles and qualifications would need to be updated through their respective relationships

    def get_by_name(self, name: str) -> Optional[Employee]:
        """Get an employee by name."""
        try:
            # Log with redaction since the name is sensitive
            result = redact_log_message(
                f"Retrieving employee by name: {name}",
                employee_names=[name]
            )

            self.logger.info(
                result.message,
                extra={
                    "event_type": "employee_lookup",
                    "lookup_type": "name",
                    "redacted": True,
                    "redacted_fields": result.redacted_fields
                }
            )

            employee_model = self._session.query(EmployeeModel).filter(EmployeeModel.name == name).first()
            if not employee_model:
                self.logger.info(
                    "No employee found with name matching the provided value",
                    extra={
                        "event_type": "employee_lookup_failed",
                        "lookup_type": "name"
                    }
                )
                return None

            self.logger.info(
                f"Found employee with ID: {employee_model.id}",
                extra={
                    "event_type": "employee_lookup_success",
                    "lookup_type": "name",
                    "employee_id": employee_model.id
                }
            )
            return employee_model.to_domain()
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving employee by name: {error_msg}",
                extra={
                    "event_type": "employee_lookup_error",
                    "lookup_type": "name",
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving employee by name: {error_msg}")

    def get(self, id: int) -> Optional[Employee]:
        """Retrieve an employee by their ID.

    Args:
        id: The unique identifier of the employee.

    Returns:
        Employee object if found, None otherwise.

    Raises:
        NotFoundError: If employee with given ID doesn't exist.
    """
        try:
            self.logger.info(
                f"Retrieving employee by ID: {id}",
                extra={
                    "event_type": "employee_lookup",
                    "lookup_type": "id",
                    "employee_id": id
                }
            )

            employee_model = self._session.query(EmployeeModel).filter(EmployeeModel.id == id).first()
            if not employee_model:
                self.logger.info(
                    f"No employee found with ID: {id}",
                    extra={
                        "event_type": "employee_lookup_failed",
                        "lookup_type": "id",
                        "employee_id": id
                    }
                )
                return None

            # Log with redaction since the employee name is sensitive
            result = redact_log_message(
                f"Found employee {employee_model.name} with ID: {id}",
                employee_names=[employee_model.name]
            )
            self.logger.info(
                result.message,
                extra={
                    "event_type": "employee_lookup_success",
                    "lookup_type": "id",
                    "employee_id": id,
                    "redacted": True,
                    "redacted_fields": result.redacted_fields
                }
            )

            return employee_model.to_domain()
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving employee by ID {id}: {error_msg}",
                extra={
                    "event_type": "employee_lookup_error",
                    "lookup_type": "id",
                    "employee_id": id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Error retrieving employee by ID: {error_msg}")
