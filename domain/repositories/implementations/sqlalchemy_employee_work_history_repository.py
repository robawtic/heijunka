# heijunka/domain/repositories/implementations/sqlalchemy_employee_work_history_repository.py
from typing import List, Optional, Tuple
from datetime import date
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from domain.value_objects.work_history_entry import WorkHistoryEntry
from domain.models.EmployeeWorkHistoryModel import EmployeeWorkHistoryModel
from domain.repositories.interfaces.employee_work_history_repository import EmployeeWorkHistoryRepositoryInterface
from domain.repositories.implementations.base_sqlalchemy_repository import BaseSqlAlchemyRepository
from infrastructure.exceptions import RepositoryError


class SqlAlchemyEmployeeWorkHistoryRepository(BaseSqlAlchemyRepository[WorkHistoryEntry, EmployeeWorkHistoryModel], EmployeeWorkHistoryRepositoryInterface):
    """
    SQLAlchemy implementation of the EmployeeWorkHistoryRepository interface.

    This class provides the actual implementation for accessing and manipulating
    employee work history entries in the database using SQLAlchemy.
    """

    def __init__(self, session: Session):
        """
        Initialize the repository with a SQLAlchemy session.

        Args:
            session: The SQLAlchemy session to use
        """
        super().__init__(session, EmployeeWorkHistoryModel, WorkHistoryEntry)

    def add(self, work_history_entry: WorkHistoryEntry) -> WorkHistoryEntry:
        """
        Add a new work history entry.

        Args:
            work_history_entry: The work history entry to add

        Returns:
            The added work history entry
        """
        try:
            model = EmployeeWorkHistoryModel(
                employee_id=work_history_entry.employee_id,
                station_id=work_history_entry.workstation_id,
                worked_date=work_history_entry.worked_date,
                work_period=work_history_entry.work_period,
                end_flag=work_history_entry.end_flag,
                is_generated=False  # Default value
            )
            self._session.add(model)
            self._session.flush()
            return work_history_entry
        except SQLAlchemyError as e:
            self._session.rollback()
            raise RepositoryError(f"Failed to add work history entry: {str(e)}")

    def get_by_employee_and_workstation(self, employee_id: int, workstation_id: int) -> List[WorkHistoryEntry]:
        """
        Get all work history entries for a specific employee and workstation.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation

        Returns:
            A list of work history entries
        """
        try:
            models = self._session.query(EmployeeWorkHistoryModel).filter(
                and_(
                    EmployeeWorkHistoryModel.employee_id == employee_id,
                    EmployeeWorkHistoryModel.station_id == workstation_id
                )
            ).all()

            return [
                WorkHistoryEntry(
                    employee_id=model.employee_id,
                    workstation_id=model.station_id,
                    worked_date=model.worked_date,
                    work_period=model.work_period,
                    end_flag=model.end_flag
                )
                for model in models
            ]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get work history entries: {str(e)}")

    def get_last_worked_date(self, employee_id: int, workstation_id: int) -> Tuple[Optional[date], Optional[int]]:
        """
        Get the last date an employee worked at a specific workstation.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation

        Returns:
            A tuple containing the date and period, or (None, None) if no history exists
        """
        try:
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
                return entry.worked_date, entry.work_period
            return None, None
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get last worked date: {str(e)}")

    def get_by_date_range(self, start_date: date, end_date: date) -> List[WorkHistoryEntry]:
        """
        Get all work history entries within a date range.

        Args:
            start_date: The start date (inclusive)
            end_date: The end date (inclusive)

        Returns:
            A list of work history entries
        """
        try:
            models = self._session.query(EmployeeWorkHistoryModel).filter(
                and_(
                    EmployeeWorkHistoryModel.worked_date >= start_date,
                    EmployeeWorkHistoryModel.worked_date <= end_date
                )
            ).all()

            return [
                WorkHistoryEntry(
                    employee_id=model.employee_id,
                    workstation_id=model.station_id,
                    worked_date=model.worked_date,
                    work_period=model.work_period,
                    end_flag=model.end_flag
                )
                for model in models
            ]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get work history entries by date range: {str(e)}")

    def get_by_employee_date_range(self, employee_id: int, start_date: date, end_date: date) -> List[WorkHistoryEntry]:
        """
        Get all work history entries for a specific employee within a date range.

        Args:
            employee_id: The ID of the employee
            start_date: The start date (inclusive)
            end_date: The end date (inclusive)

        Returns:
            A list of work history entries
        """
        try:
            models = self._session.query(EmployeeWorkHistoryModel).filter(
                and_(
                    EmployeeWorkHistoryModel.employee_id == employee_id,
                    EmployeeWorkHistoryModel.worked_date >= start_date,
                    EmployeeWorkHistoryModel.worked_date <= end_date
                )
            ).all()

            return [
                WorkHistoryEntry(
                    employee_id=model.employee_id,
                    workstation_id=model.station_id,
                    worked_date=model.worked_date,
                    work_period=model.work_period,
                    end_flag=model.end_flag
                )
                for model in models
            ]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get work history entries by employee and date range: {str(e)}")

    def delete(self, employee_id: int, workstation_id: int, worked_date: date, work_period: int) -> bool:
        """
        Delete a work history entry.

        Args:
            employee_id: The ID of the employee
            workstation_id: The ID of the workstation
            worked_date: The date the work was performed
            work_period: The period of the day the work was performed

        Returns:
            True if deleted, False if not found
        """
        try:
            entry = self._session.query(EmployeeWorkHistoryModel).filter(
                and_(
                    EmployeeWorkHistoryModel.employee_id == employee_id,
                    EmployeeWorkHistoryModel.station_id == workstation_id,
                    EmployeeWorkHistoryModel.worked_date == worked_date,
                    EmployeeWorkHistoryModel.work_period == work_period
                )
            ).first()

            if not entry:
                return False

            self._session.delete(entry)
            self._session.flush()
            return True
        except SQLAlchemyError as e:
            self._session.rollback()
            raise RepositoryError(f"Failed to delete work history entry: {str(e)}")

    def get(self, id: int) -> Optional[WorkHistoryEntry]:
        """
        Get an entity by ID.

        This method is required by the BaseRepository interface but is not applicable
        for WorkHistoryEntry since it doesn't have a single ID field.

        Args:
            id: The ID of the entity to retrieve

        Returns:
            None (not applicable for WorkHistoryEntry)
        """
        return None

    def get_all_entities(self) -> List[WorkHistoryEntry]:
        """
        Get all entities.

        Returns:
            A list of all work history entries
        """
        try:
            models = self._session.query(EmployeeWorkHistoryModel).all()

            return [
                WorkHistoryEntry(
                    employee_id=model.employee_id,
                    workstation_id=model.station_id,
                    worked_date=model.worked_date,
                    work_period=model.work_period,
                    end_flag=model.end_flag
                )
                for model in models
            ]
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get all work history entries: {str(e)}")

    def _to_domain(self, model: EmployeeWorkHistoryModel) -> WorkHistoryEntry:
        """
        Convert a SQLAlchemy model to a domain entity.

        Args:
            model: The SQLAlchemy model to convert

        Returns:
            The domain entity
        """
        return WorkHistoryEntry(
            employee_id=model.employee_id,
            workstation_id=model.station_id,
            worked_date=model.worked_date,
            work_period=model.work_period,
            end_flag=model.end_flag
        )

    def _to_model(self, entity: WorkHistoryEntry) -> EmployeeWorkHistoryModel:
        """
        Convert a domain entity to a SQLAlchemy model.

        Args:
            entity: The domain entity to convert

        Returns:
            The SQLAlchemy model
        """
        return EmployeeWorkHistoryModel(
            employee_id=entity.employee_id,
            station_id=entity.workstation_id,
            worked_date=entity.worked_date,
            work_period=entity.work_period,
            end_flag=entity.end_flag,
            is_generated=False  # Default value
        )

    def _update_model(self, model: EmployeeWorkHistoryModel, entity: WorkHistoryEntry) -> None:
        """
        Update a SQLAlchemy model with values from a domain entity.

        Args:
            model: The SQLAlchemy model to update
            entity: The domain entity with updated values
        """
        model.employee_id = entity.employee_id
        model.station_id = entity.workstation_id
        model.worked_date = entity.worked_date
        model.work_period = entity.work_period
        model.end_flag = entity.end_flag
        # We don't update is_generated as it's not part of the WorkHistoryEntry entity

    def get_filtered(self, team_id: Optional[int] = None, employee_id: Optional[int] = None, 
                    workstation_id: Optional[int] = None, start_date: Optional[date] = None, 
                    end_date: Optional[date] = None, period: Optional[int] = None,
                    skip: int = 0, limit: int = 100) -> Tuple[List[WorkHistoryEntry], int]:
        """
        Get work history entries with filtering applied at the database level.

        Args:
            team_id: Filter by team ID
            employee_id: Filter by employee ID
            workstation_id: Filter by workstation ID
            start_date: Filter by start date (inclusive)
            end_date: Filter by end date (inclusive)
            period: Filter by work period
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            A tuple containing a list of work history entries and the total count
        """
        from domain.models.EmployeeModel import EmployeeModel
        from domain.models.WorkstationModel import WorkstationModel

        try:
            # Start with a base query that joins with Employee and Workstation
            query = self._session.query(EmployeeWorkHistoryModel).\
                join(EmployeeModel, EmployeeWorkHistoryModel.employee_id == EmployeeModel.id).\
                join(WorkstationModel, EmployeeWorkHistoryModel.station_id == WorkstationModel.id)

            # Apply filters
            if team_id is not None:
                # We can filter by either employee's team or workstation's team
                query = query.filter(
                    or_(
                        EmployeeModel.team_id == team_id,
                        WorkstationModel.team_id == team_id
                    )
                )

            if employee_id is not None:
                query = query.filter(EmployeeWorkHistoryModel.employee_id == employee_id)

            if workstation_id is not None:
                query = query.filter(EmployeeWorkHistoryModel.station_id == workstation_id)

            if start_date is not None:
                query = query.filter(EmployeeWorkHistoryModel.worked_date >= start_date)

            if end_date is not None:
                query = query.filter(EmployeeWorkHistoryModel.worked_date <= end_date)

            if period is not None:
                query = query.filter(EmployeeWorkHistoryModel.work_period == period)

            # Get total count for pagination
            total = query.count()

            # Apply pagination
            query = query.order_by(EmployeeWorkHistoryModel.worked_date.desc()).\
                offset(skip).limit(limit)

            # Execute query
            models = query.all()

            # Convert to domain entities
            return [self._to_domain(model) for model in models], total

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to get filtered work history entries: {str(e)}")
