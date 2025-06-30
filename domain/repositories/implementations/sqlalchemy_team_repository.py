from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from domain.entities.team import Team
from domain.entities.employee import Employee
from domain.entities.workstation import Workstation
from domain.models import TeamMemberModel
from domain.models.TeamModel import TeamModel
from domain.models.EmployeeModel import EmployeeModel
from domain.models.WorkstationModel import WorkstationModel
from domain.repositories.interfaces.team_repository import TeamRepositoryInterface
from infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError
from utilities.secure_logging import sanitize_exception
from utilities.logging_factory import get_logger
from domain.factories.team_factory import TeamFactory
from domain.factories.employee_factory import EmployeeFactory
from domain.factories.workstation_factory import WorkstationFactory


class SqlAlchemyTeamRepository(BaseSqlAlchemyRepository[Team, TeamModel], TeamRepositoryInterface):
    """
    SQLAlchemy implementation of the TeamRepository interface.

    This class provides the actual implementation for accessing and manipulating
    Team entities in the database using SQLAlchemy.
    """

    def __init__(self, session_factory):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session_factory: The SQLAlchemy session factory to use for database operations.
        """
        super().__init__(session_factory, TeamModel, Team)
        self.logger = get_logger("heijunka.repositories.team")
        self.rate_limited_logger = get_logger("heijunka.repositories.team", rate_limit=True)

    # Core CRUD Operations

    def get(self, id: int) -> Optional[Team]:
        """
        Retrieve a Team aggregate by its ID.

        Args:
            id: The unique identifier of the team.

        Returns:
            A Team entity if found; otherwise, None.
        """
        return self.get_by_id(id)  # Use the base class implementation

    def get_all(self) -> List[Team]:
        """
        Retrieve all teams.

        Returns:
            A list of all Team entities.
        """
        return self.list_all()  # Use the base class implementation

    def get_by_name(self, name: str) -> Optional[Team]:
        """
        Retrieve a team by its name (case-insensitive).

        Args:
            name: The name of the team.

        Returns:
            The team if found, None otherwise.
        """
        try:
            self.logger.info(
                f"Retrieving team by name: {name}",
                extra={
                    "event_type": "team_lookup",
                    "lookup_type": "name",
                    "team_name": name
                }
            )

            with self.session_scope() as session:
                team_model = session.query(TeamModel).filter(
                    func.lower(TeamModel.name) == func.lower(name)
                ).first()

                if team_model is None:
                    self.logger.info(
                        f"No team found with name: {name}",
                        extra={
                            "event_type": "team_lookup_failed",
                            "lookup_type": "name",
                            "team_name": name,
                            "reason": "not_found"
                        }
                    )
                    return None

                self.logger.info(
                    f"Found team with name: {name}",
                    extra={
                        "event_type": "team_lookup_success",
                        "lookup_type": "name",
                        "team_name": name,
                        "team_id": team_model.id
                    }
                )

                return self._to_domain(team_model)
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving team by name: {error_msg}",
                extra={
                    "event_type": "team_lookup_error",
                    "lookup_type": "name",
                    "team_name": name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get team by name: {error_msg}")

    # Team Member Operations

    def add_member(self, team_id: int, employee: Employee) -> bool:
        """
        Add an employee to a team.

        Args:
            team_id: The ID of the team.
            employee: The employee to add.

        Returns:
            True if the employee was added successfully, False otherwise.
        """
        try:
            self.logger.info(
                f"Adding employee ID: {employee.id} to team ID: {team_id}",
                extra={
                    "event_type": "team_member_add",
                    "team_id": team_id,
                    "employee_id": employee.id,
                    "employee_name": employee.name if hasattr(employee, 'name') else "Unknown"
                }
            )

            with self.session_scope() as session:
                team = session.query(TeamModel).get(team_id)
                employee_model = session.query(EmployeeModel).get(employee.id)

                if not team or not employee_model:
                    self.logger.info(
                        f"Failed to add employee to team: team or employee not found",
                        extra={
                            "event_type": "team_member_add_failed",
                            "team_id": team_id,
                            "employee_id": employee.id,
                            "reason": "not_found",
                            "team_exists": team is not None,
                            "employee_exists": employee_model is not None
                        }
                    )
                    return False

                # Check if the employee is already a member of the team
                for member in team.members:
                    if member.employee_id == employee.id:
                        self.logger.info(
                            f"Employee ID: {employee.id} is already a member of team ID: {team_id}",
                            extra={
                                "event_type": "team_member_add_skipped",
                                "team_id": team_id,
                                "employee_id": employee.id,
                                "reason": "already_member"
                            }
                        )
                        return True  # Already a member

                # Add the employee to the team
                team_member = TeamMemberModel(team_id=team_id, employee_id=employee.id)
                session.add(team_member)

                self.logger.info(
                    f"Successfully added employee ID: {employee.id} to team ID: {team_id}",
                    extra={
                        "event_type": "team_member_add_success",
                        "team_id": team_id,
                        "employee_id": employee.id,
                        "employee_name": employee.name if hasattr(employee, 'name') else "Unknown"
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error adding employee to team: {error_msg}",
                extra={
                    "event_type": "team_member_add_error",
                    "team_id": team_id,
                    "employee_id": employee.id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to add employee to team: {error_msg}")

    def remove_member(self, team_id: int, employee_id: int) -> bool:
        """
        Remove an employee from a team.

        Args:
            team_id: The ID of the team.
            employee_id: The ID of the employee to remove.

        Returns:
            True if the employee was removed successfully, False otherwise.
        """
        try:
            self.logger.info(
                f"Removing employee ID: {employee_id} from team ID: {team_id}",
                extra={
                    "event_type": "team_member_remove",
                    "team_id": team_id,
                    "employee_id": employee_id
                }
            )

            with self.session_scope() as session:
                team_member = session.query(TeamMemberModel).filter(
                    TeamMemberModel.team_id == team_id,
                    TeamMemberModel.employee_id == employee_id
                ).first()

                if not team_member:
                    self.logger.info(
                        f"Failed to remove employee from team: team member not found",
                        extra={
                            "event_type": "team_member_remove_failed",
                            "team_id": team_id,
                            "employee_id": employee_id,
                            "reason": "not_found"
                        }
                    )
                    return False

                session.delete(team_member)

                self.logger.info(
                    f"Successfully removed employee ID: {employee_id} from team ID: {team_id}",
                    extra={
                        "event_type": "team_member_remove_success",
                        "team_id": team_id,
                        "employee_id": employee_id
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error removing employee from team: {error_msg}",
                extra={
                    "event_type": "team_member_remove_error",
                    "team_id": team_id,
                    "employee_id": employee_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to remove employee from team: {error_msg}")

    def get_members(self, team_id: int) -> List[Employee]:
        """
        Get all members of a team.

        Args:
            team_id: The ID of the team.

        Returns:
            A list of employees that are members of the team.
        """
        try:
            self.logger.info(
                f"Retrieving members for team ID: {team_id}",
                extra={
                    "event_type": "team_members_lookup",
                    "team_id": team_id
                }
            )

            with self.session_scope() as session:
                team = session.query(TeamModel).get(team_id)
                if not team:
                    self.logger.info(
                        f"No team found with ID: {team_id}",
                        extra={
                            "event_type": "team_members_lookup_failed",
                            "team_id": team_id,
                            "reason": "team_not_found"
                        }
                    )
                    return []

                members = []
                for member in team.members:
                    if member.employee:
                        employee = EmployeeFactory.create_from_model(member.employee)
                        members.append(employee)

                member_count = len(members)
                self.logger.info(
                    f"Retrieved {member_count} members for team ID: {team_id}",
                    extra={
                        "event_type": "team_members_lookup_success",
                        "team_id": team_id,
                        "member_count": member_count
                    }
                )

                return members
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving team members: {error_msg}",
                extra={
                    "event_type": "team_members_lookup_error",
                    "team_id": team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get team members: {error_msg}")

    # Team Workstation Operations

    def add_workstation(self, team_id: int, workstation: Workstation) -> bool:
        """
        Add a workstation to a team.

        Args:
            team_id: The ID of the team.
            workstation: The workstation to add.

        Returns:
            True if the workstation was added successfully, False otherwise.
        """
        try:
            self.logger.info(
                f"Adding workstation ID: {workstation.id} to team ID: {team_id}",
                extra={
                    "event_type": "team_workstation_add",
                    "team_id": team_id,
                    "workstation_id": workstation.id,
                    "workstation_name": workstation.name if hasattr(workstation, 'name') else "Unknown"
                }
            )

            with self.session_scope() as session:
                team = session.query(TeamModel).get(team_id)
                workstation_model = session.query(WorkstationModel).get(workstation.id)

                if not team or not workstation_model:
                    self.logger.info(
                        f"Failed to add workstation to team: team or workstation not found",
                        extra={
                            "event_type": "team_workstation_add_failed",
                            "team_id": team_id,
                            "workstation_id": workstation.id,
                            "reason": "not_found",
                            "team_exists": team is not None,
                            "workstation_exists": workstation_model is not None
                        }
                    )
                    return False

                # Check if the workstation is already assigned to the team
                if workstation_model.team_id == team_id:
                    self.logger.info(
                        f"Workstation ID: {workstation.id} is already assigned to team ID: {team_id}",
                        extra={
                            "event_type": "team_workstation_add_skipped",
                            "team_id": team_id,
                            "workstation_id": workstation.id,
                            "reason": "already_assigned"
                        }
                    )
                    return True  # Already assigned

                # Log the change if the workstation is already assigned to another team
                if workstation_model.team_id is not None:
                    self.logger.info(
                        f"Reassigning workstation ID: {workstation.id} from team ID: {workstation_model.team_id} to team ID: {team_id}",
                        extra={
                            "event_type": "workstation_team_change",
                            "workstation_id": workstation.id,
                            "old_team_id": workstation_model.team_id,
                            "new_team_id": team_id
                        }
                    )

                # Assign the workstation to the team
                workstation_model.team_id = team_id

                self.logger.info(
                    f"Successfully added workstation ID: {workstation.id} to team ID: {team_id}",
                    extra={
                        "event_type": "team_workstation_add_success",
                        "team_id": team_id,
                        "workstation_id": workstation.id,
                        "workstation_name": workstation.name if hasattr(workstation, 'name') else "Unknown"
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error adding workstation to team: {error_msg}",
                extra={
                    "event_type": "team_workstation_add_error",
                    "team_id": team_id,
                    "workstation_id": workstation.id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to add workstation to team: {error_msg}")

    def remove_workstation(self, team_id: int, workstation_id: int) -> bool:
        """
        Remove a workstation from a team.

        Args:
            team_id: The ID of the team.
            workstation_id: The ID of the workstation to remove.

        Returns:
            True if the workstation was removed successfully, False otherwise.
        """
        try:
            self.logger.info(
                f"Removing workstation ID: {workstation_id} from team ID: {team_id}",
                extra={
                    "event_type": "team_workstation_remove",
                    "team_id": team_id,
                    "workstation_id": workstation_id
                }
            )

            with self.session_scope() as session:
                workstation = session.query(WorkstationModel).filter(
                    WorkstationModel.id == workstation_id,
                    WorkstationModel.team_id == team_id
                ).first()

                if not workstation:
                    self.logger.info(
                        f"Failed to remove workstation from team: workstation not found or not assigned to team",
                        extra={
                            "event_type": "team_workstation_remove_failed",
                            "team_id": team_id,
                            "workstation_id": workstation_id,
                            "reason": "not_found_or_not_assigned"
                        }
                    )
                    return False

                # This is a bit tricky - we don't want to delete the workstation,
                # just unassign it from the team. In a real system, you might set
                # id to NULL or reassign it to a default team.
                workstation.team_id = None

                self.logger.info(
                    f"Successfully removed workstation ID: {workstation_id} from team ID: {team_id}",
                    extra={
                        "event_type": "team_workstation_remove_success",
                        "team_id": team_id,
                        "workstation_id": workstation_id,
                        "workstation_name": workstation.name
                    }
                )
                return True
        except RepositoryError:
            # This will be caught and logged by session_scope
            raise
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error removing workstation from team: {error_msg}",
                extra={
                    "event_type": "team_workstation_remove_error",
                    "team_id": team_id,
                    "workstation_id": workstation_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to remove workstation from team: {error_msg}")

    def get_workstations(self, team_id: int) -> List[Workstation]:
        """
        Get all workstations of a team.

        Args:
            team_id: The ID of the team.

        Returns:
            A list of workstations that belong to the team.
        """
        try:
            self.logger.info(
                f"Retrieving workstations for team ID: {team_id}",
                extra={
                    "event_type": "team_workstations_lookup",
                    "team_id": team_id
                }
            )

            result = []
            with self.session_scope() as session:
                workstations = session.query(WorkstationModel).filter(
                    WorkstationModel.team_id == team_id
                ).all()

                workstation_count = len(workstations)
                self.logger.info(
                    f"Retrieved {workstation_count} workstations for team ID: {team_id}",
                    extra={
                        "event_type": "team_workstations_lookup_success",
                        "team_id": team_id,
                        "workstation_count": workstation_count
                    }
                )

                result = [WorkstationFactory.create_from_model(ws) for ws in workstations]

            return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving team workstations: {error_msg}",
                extra={
                    "event_type": "team_workstations_lookup_error",
                    "team_id": team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get team workstations: {error_msg}")

    # Team Hierarchy Operations

    def get_by_group_name(self, group_name: str) -> List[Team]:
        """
        Retrieve all teams that belong to a group with the given name.

        Args:
            group_name: The name of the group.

        Returns:
            A list of teams that belong to the group.
        """
        try:
            self.logger.info(
                f"Retrieving teams by group name: {group_name}",
                extra={
                    "event_type": "teams_by_group_lookup",
                    "group_name": group_name
                }
            )

            from domain.models.GroupModel import GroupModel

            with self.session_scope() as session:
                # Find the group by name (case-insensitive)
                group = session.query(GroupModel).filter(
                    func.lower(GroupModel.name) == func.lower(group_name)).first()
                if not group:
                    self.logger.info(
                        f"No group found with name: {group_name}",
                        extra={
                            "event_type": "teams_by_group_lookup_failed",
                            "group_name": group_name,
                            "reason": "group_not_found"
                        }
                    )
                    return []

                # Get all teams that belong to this group
                team_models = session.query(TeamModel).filter(TeamModel.group_id == group.id).all()

                team_count = len(team_models)
                self.logger.info(
                    f"Retrieved {team_count} teams for group name: {group_name}",
                    extra={
                        "event_type": "teams_by_group_lookup_success",
                        "group_name": group_name,
                        "group_id": group.id,
                        "team_count": team_count
                    }
                )

                result = [self._to_domain(team_model) for team_model in team_models]

                return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving teams by group name: {error_msg}",
                extra={
                    "event_type": "teams_by_group_lookup_error",
                    "group_name": group_name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get teams by group name: {error_msg}")

    def get_by_department_name(self, department_name: str) -> List[Team]:
        """
        Retrieve all teams that belong to a department with the given name.

        Args:
            department_name: The name of the department.

        Returns:
            A list of teams that belong to the department (directly or through groups).
        """
        try:
            self.logger.info(
                f"Retrieving teams by department name: {department_name}",
                extra={
                    "event_type": "teams_by_department_lookup",
                    "department_name": department_name
                }
            )

            from domain.models.DepartmentModel import DepartmentModel
            from domain.models.GroupModel import GroupModel

            with self.session_scope() as session:
                # Find the department by name (case-insensitive)
                department = session.query(DepartmentModel).filter(
                    func.lower(DepartmentModel.name) == func.lower(department_name)).first()
                if not department:
                    self.logger.info(
                        f"No department found with name: {department_name}",
                        extra={
                            "event_type": "teams_by_department_lookup_failed",
                            "department_name": department_name,
                            "reason": "department_not_found"
                        }
                    )
                    return []

                # Get all groups that belong to this department
                groups = session.query(GroupModel).filter(GroupModel.department_id == department.id).all()
                if not groups:
                    self.logger.info(
                        f"No groups found for department: {department_name}",
                        extra={
                            "event_type": "teams_by_department_lookup_failed",
                            "department_name": department_name,
                            "department_id": department.id,
                            "reason": "no_groups"
                        }
                    )
                    return []

                # Get all teams that belong to any of these groups
                group_ids = [group.id for group in groups]
                team_models = session.query(TeamModel).filter(TeamModel.group_id.in_(group_ids)).all()

                team_count = len(team_models)
                group_count = len(groups)
                self.logger.info(
                    f"Retrieved {team_count} teams from {group_count} groups for department: {department_name}",
                    extra={
                        "event_type": "teams_by_department_lookup_success",
                        "department_name": department_name,
                        "department_id": department.id,
                        "group_count": group_count,
                        "team_count": team_count
                    }
                )

                result = [self._to_domain(team_model) for team_model in team_models]

                return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving teams by department name: {error_msg}",
                extra={
                    "event_type": "teams_by_department_lookup_error",
                    "department_name": department_name,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get teams by department name: {error_msg}")

    def get_by_department_id(self, department_id: int) -> List[Team]:
        """
        Retrieve all teams that belong to a department with the given ID.

        Args:
            department_id: The ID of the department.

        Returns:
            A list of teams that belong to the department (directly or through groups).
        """
        try:
            self.logger.info(
                f"Retrieving teams by department ID: {department_id}",
                extra={
                    "event_type": "teams_by_department_lookup",
                    "department_id": department_id
                }
            )

            from domain.models.GroupModel import GroupModel

            with self.session_scope() as session:
                # Get all groups that belong to this department
                groups = session.query(GroupModel).filter(GroupModel.department_id == department_id).all()
                if not groups:
                    self.logger.info(
                        f"No groups found for department ID: {department_id}",
                        extra={
                            "event_type": "teams_by_department_lookup_failed",
                            "department_id": department_id,
                            "reason": "no_groups"
                        }
                    )
                    return []

                # Get all teams that belong to any of these groups
                group_ids = [group.id for group in groups]
                team_models = session.query(TeamModel).filter(TeamModel.group_id.in_(group_ids)).all()

                team_count = len(team_models)
                group_count = len(groups)
                self.logger.info(
                    f"Retrieved {team_count} teams from {group_count} groups for department ID: {department_id}",
                    extra={
                        "event_type": "teams_by_department_lookup_success",
                        "department_id": department_id,
                        "group_count": group_count,
                        "team_count": team_count
                    }
                )

                result = [self._to_domain(team_model) for team_model in team_models]

                return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving teams by department ID: {error_msg}",
                extra={
                    "event_type": "teams_by_department_lookup_error",
                    "department_id": department_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get teams by department ID: {error_msg}")

    def get_group(self, team_id: int) -> Optional[Any]:
        """
        Retrieve the group that a team belongs to.

        Args:
            team_id: The ID of the team.

        Returns:
            The group if found, None otherwise.
        """
        try:
            self.logger.info(
                f"Retrieving group for team ID: {team_id}",
                extra={
                    "event_type": "team_group_lookup",
                    "team_id": team_id
                }
            )

            with self.session_scope() as session:
                team_model = session.query(TeamModel).get(team_id)
                if not team_model:
                    self.logger.info(
                        f"No team found with ID: {team_id}",
                        extra={
                            "event_type": "team_group_lookup_failed",
                            "team_id": team_id,
                            "reason": "team_not_found"
                        }
                    )
                    return None

                if not team_model.group:
                    self.logger.info(
                        f"Team with ID: {team_id} does not belong to any group",
                        extra={
                            "event_type": "team_group_lookup_failed",
                            "team_id": team_id,
                            "reason": "no_group"
                        }
                    )
                    return None

                self.logger.info(
                    f"Found group ID: {team_model.group.id} for team ID: {team_id}",
                    extra={
                        "event_type": "team_group_lookup_success",
                        "team_id": team_id,
                        "group_id": team_model.group.id,
                        "group_name": team_model.group.name
                    }
                )

                result = team_model.group.to_domain() if hasattr(team_model.group, 'to_domain') else team_model.group

                return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving group for team: {error_msg}",
                extra={
                    "event_type": "team_group_lookup_error",
                    "team_id": team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get group for team: {error_msg}")

    def get_department(self, department_id: int) -> Optional[Any]:
        """
        Retrieve a department by its ID.

        Args:
            department_id: The ID of the department.

        Returns:
            The department if found, None otherwise.
        """
        try:
            self.logger.info(
                f"Retrieving department by ID: {department_id}",
                extra={
                    "event_type": "department_lookup",
                    "department_id": department_id
                }
            )

            from domain.models.DepartmentModel import DepartmentModel
            from domain.factories.department_factory import DepartmentFactory

            with self.session_scope() as session:
                department_model = session.query(DepartmentModel).filter(DepartmentModel.id == department_id).first()
                if not department_model:
                    self.logger.info(
                        f"No department found with ID: {department_id}",
                        extra={
                            "event_type": "department_lookup_failed",
                            "department_id": department_id,
                            "reason": "not_found"
                        }
                    )
                    return None

                self.logger.info(
                    f"Found department with ID: {department_id}",
                    extra={
                        "event_type": "department_lookup_success",
                        "department_id": department_id,
                        "department_name": department_model.name
                    }
                )

                # Convert the model to a domain entity to ensure it doesn't depend on the session
                result = DepartmentFactory.create_from_model(department_model)

                return result
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving department by ID: {error_msg}",
                extra={
                    "event_type": "department_lookup_error",
                    "department_id": department_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get department by ID: {error_msg}")

    # Utility Operations

    def get_with_counts(self, team_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a team with employee and workstation counts.

        Args:
            team_id: The ID of the team.

        Returns:
            A dictionary containing the team and counts if found, None otherwise.
            Example: {'team': team, 'employee_count': 10, 'workstation_count': 5}
        """
        try:
            self.logger.info(
                f"Retrieving team with counts for team ID: {team_id}",
                extra={
                    "event_type": "team_with_counts_lookup",
                    "team_id": team_id
                }
            )

            with self.session_scope() as session:
                result = session.query(
                    TeamModel,
                    func.count(distinct(EmployeeModel.id)).label('employee_count'),
                    func.count(distinct(WorkstationModel.id)).label('workstation_count')
                ).outerjoin(
                    TeamMemberModel, TeamMemberModel.team_id == TeamModel.id
                ).outerjoin(
                    EmployeeModel, EmployeeModel.id == TeamMemberModel.employee_id
                ).outerjoin(
                    WorkstationModel, WorkstationModel.team_id == TeamModel.id
                ).filter(
                    TeamModel.id == team_id
                ).group_by(
                    TeamModel.id
                ).first()

                if not result:
                    self.logger.info(
                        f"No team found with ID: {team_id}",
                        extra={
                            "event_type": "team_with_counts_lookup_failed",
                            "team_id": team_id,
                            "reason": "team_not_found"
                        }
                    )
                    return None

                team, employee_count, workstation_count = result

                self.logger.info(
                    f"Retrieved team with counts for team ID: {team_id}",
                    extra={
                        "event_type": "team_with_counts_lookup_success",
                        "team_id": team_id,
                        "team_name": team.name,
                        "employee_count": employee_count,
                        "workstation_count": workstation_count
                    }
                )

                return {
                    'team': self._to_domain(team),
                    'employee_count': employee_count,
                    'workstation_count': workstation_count
                }
        except SQLAlchemyError as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error retrieving team with counts: {error_msg}",
                extra={
                    "event_type": "team_with_counts_lookup_error",
                    "team_id": team_id,
                    "error_type": type(e).__name__
                }
            )
            raise RepositoryError(f"Failed to get team with counts: {error_msg}")

    # Conversion Methods

    def _to_domain(self, model: TeamModel) -> Team:
        """
        Convert a SQLAlchemy model to a domain entity using TeamFactory.

        Args:
            model: The SQLAlchemy model to convert.

        Returns:
            The domain entity.
        """
        try:
            self.logger.debug(
                "Converting team model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion",
                    "entity_id": model.id,
                    "entity_name": model.name
                }
            )

            team = TeamFactory.create_from_model(model)

            self.logger.debug(
                "Successfully converted team model to domain entity",
                extra={
                    "event_type": "model_to_domain_conversion_success",
                    "entity_id": model.id
                }
            )

            return team
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting team model to domain entity: {error_msg}",
                extra={
                    "event_type": "model_to_domain_conversion_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _to_model(self, entity: Team) -> TeamModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert.

        Returns:
            The SQLAlchemy model.
        """
        try:
            self.logger.debug(
                "Converting team domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion",
                    "entity_id": entity.id,
                    "entity_name": entity.name
                }
            )

            model = TeamModel(
                id=entity.id,
                name=entity.name,
                description=entity.description
            )

            self.logger.debug(
                "Successfully converted team domain entity to model",
                extra={
                    "event_type": "domain_to_model_conversion_success",
                    "entity_id": entity.id
                }
            )

            return model
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error converting team domain entity to model: {error_msg}",
                extra={
                    "event_type": "domain_to_model_conversion_error",
                    "entity_id": entity.id if entity and hasattr(entity, 'id') else None,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _update_model(self, model: TeamModel, entity: Team) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update.
            entity: The domain entity with updated values.
        """
        try:
            self.logger.debug(
                "Updating team model from domain entity",
                extra={
                    "event_type": "team_model_update",
                    "entity_id": model.id,
                    "entity_name": model.name
                }
            )

            # Check for significant changes and log them
            if model.name != entity.name:
                self.logger.info(
                    "Changing team name",
                    extra={
                        "event_type": "team_field_change",
                        "entity_id": model.id,
                        "field": "name",
                        "old_value": model.name,
                        "new_value": entity.name
                    }
                )

            if model.description != entity.description:
                self.logger.info(
                    "Changing team description",
                    extra={
                        "event_type": "team_field_change",
                        "entity_id": model.id,
                        "field": "description",
                        "old_value": model.description,
                        "new_value": entity.description
                    }
                )

            # Update the model
            model.name = entity.name
            model.description = entity.description
            # Members and workstations would need to be updated through their respective relationships

            self.logger.debug(
                "Successfully updated team model",
                extra={
                    "event_type": "team_model_update_success",
                    "entity_id": model.id
                }
            )
        except Exception as e:
            error_msg = sanitize_exception(e)
            self.logger.error(
                f"Error updating team model: {error_msg}",
                extra={
                    "event_type": "team_model_update_error",
                    "entity_id": model.id if model else None,
                    "error_type": type(e).__name__
                }
            )
            raise
