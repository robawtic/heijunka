```mermaid
---
title: repositories
---
classDiagram
    class FileSeedDataRepository {
        - __init__(self, base_path) None
        - _load_json_file(self, file_path) Optional[Dict[str, Any]]
        - _parse_date(self, date_str) Optional[date]
        + load_workstation_data(self, team_name) List[WorkstationSeedData]
        + load_employee_data(self, team_name) List[EmployeeSeedData]
        + load_team_data(self, team_name) TeamSeedData
        + load_group_data(self, group_name) GroupSeedData
        + load_department_data(self, department_name) DepartmentSeedData
        + get_available_departments(self) List[str]
        + get_available_groups(self, department_name) List[str]
        + get_available_teams(self, department_name, group_name) List[str]
        - _find_team_directory(self, team_name) Optional[str]
        - _find_group_directory(self, group_name, department_name) Optional[str]
    }

    class SqlAlchemyAROAssignmentRepository {
        - __init__(self, session) None
        + session_scope(self) Generator[Session, None, None]
        + get_by_date(self, assignment_date) List[AROAssignment]
        + get_by_employee_id(self, employee_id, assignment_date) List[AROAssignment]
        + get_by_from_team_id(self, team_id, assignment_date) List[AROAssignment]
        + get_by_to_team_id(self, team_id, assignment_date) List[AROAssignment]
        + get_employees_leaving(self, team_id, assignment_date, period) List[int]
        + get_employees_joining(self, team_id, assignment_date, period) List[int]
        - _to_domain(self, model) AROAssignment
        - _to_model(self, entity) AROAssignmentModel
        - _update_model(self, model, entity) None
    }

    class SqlAlchemyAssignmentRepository {
        - __init__(self, session) None
        + get_all(self, page, page_size) Tuple[List[WorkAssignment], int]
        + get_by_id(self, assignment_id) Optional[WorkAssignment]
        + add(self, assignment) WorkAssignment
        + update(self, assignment) WorkAssignment
        + delete(self, assignment_id) bool
        + get_by_employee_id(self, employee_id) List[WorkAssignment]
        + get_by_workstation_id(self, workstation_id) List[WorkAssignment]
        + get_by_schedule_id(self, schedule_id) List[WorkAssignment]
        + get_by_date(self, assignment_date) List[WorkAssignment]
        + get_by_date_and_period(self, assignment_date, period) List[WorkAssignment]
        + get_by_employee_and_date(self, employee_id, assignment_date) List[WorkAssignment]
        + get_by_team_and_workstation(self, team_id, workstation_id) List[WorkAssignment]
        + save_all(self, assignments, batch_size) bool
        + delete_existing_entries_for_date(self, date_obj) int
        + delete_by_schedule_id(self, schedule_id) bool
        + create_temporary_assignment(self, employee_id, workstation_id, date_obj, period, schedule_id) bool
        - _format_date(self, date_obj) str
        - _convert_models_to_domain(self, models) List[WorkAssignment]
        - _to_domain(self, model) Optional[WorkAssignment]
        - _to_model(self, entity) EmployeeWorkHistoryModel
        - _update_model(self, model, entity) None
    }

    class SqlAlchemyDepartmentRepository {
        - __init__(self, session) None
        + get_by_name(self, department_name) Optional[Department]
        + get_all_with_groups(self) List[Department]
        - _to_domain(self, model) Department
        - _to_model(self, entity) DepartmentModel
        - _update_model(self, model, entity) None
    }

    class SqlAlchemyEmployeeRepository {
        - __init__(self, session) None
        + get(self, employee_id) Optional[Employee]
        + get_all(self) List[Employee]
        + get_by_name(self, name) Optional[Employee]
        + get_by_team_id(self, team_id) List[Employee]
        + get_by_team_ids(self, team_ids) List[Employee]
        + assign_role(self, employee_id, role_name, team_id) Dict[str, str]
        + remove_role(self, employee_id, role_name, team_id) Dict[str, str]
        + assign_workstation(self, employee_id, workstation_id) Dict[str, str]
        + get_work_history(self, employee_id, workstation_id) list
        + add_work_history(self, employee_id, workstation_id, worked_date, work_period, end_flag) bool
        + get_last_worked_date(self, employee_id, workstation_id) Tuple[Optional[date], Optional[int]]
        + is_available(self, employee_id, date_obj, period) bool
        - _to_domain(self, model) Employee
        - _to_model(self, entity) EmployeeModel
        - _update_model(self, model, entity) None
    }

    class SqlAlchemyEmployeeTrainingRepository {
        - __init__(self, session) None
        + add(self, training) EmployeeTraining
        + get_by_employee_and_workstation(self, employee_id, workstation_id) Optional[EmployeeTraining]
        + get_by_employee(self, employee_id) List[EmployeeTraining]
        + get_by_workstation(self, workstation_id) List[EmployeeTraining]
        + get_completed_trainings(self, employee_id) List[EmployeeTraining]
        + get_required_trainings(self, employee_id) List[EmployeeTraining]
        + update_training_status(self, employee_id, workstation_id, required, date_completed) Optional[EmployeeTraining]
        + delete(self, employee_id, workstation_id) bool
        + get(self, id) Optional[EmployeeTraining]
        + get_all_entities(self) List[EmployeeTraining]
    }

    class SqlAlchemyEmployeeWorkstationRepository {
        - __init__(self, session) None
        + add(self, assignment) WorkstationAssignment
        + get_by_employee_and_workstation(self, employee_id, workstation_id) Optional[WorkstationAssignment]
        + get_by_employee(self, employee_id) List[WorkstationAssignment]
        + get_by_workstation(self, workstation_id) List[WorkstationAssignment]
        + update_last_worked_date(self, employee_id, workstation_id, last_worked_date) Optional[WorkstationAssignment]
        + delete(self, employee_id, workstation_id) bool
        + get(self, id) Optional[WorkstationAssignment]
        + get_all_entities(self) List[WorkstationAssignment]
        - _to_domain(self, model) WorkstationAssignment
        - _to_model(self, entity) EmployeeWorkstationModel
        - _update_model(self, model, entity) None
    }

    class SqlAlchemyEmployeeWorkHistoryRepository {
        - __init__(self, session) None
        + add(self, work_history_entry) WorkHistoryEntry
        + create(self, employee_id, workstation_id, date_obj, period, schedule_id, status, is_generated, is_temporary) WorkHistoryEntry
        + get_by_employee_and_workstation(self, employee_id, workstation_id) List[WorkHistoryEntry]
        + get_last_worked_date(self, employee_id, workstation_id) Tuple[Optional[date], Optional[int]]
        + get_by_date_range(self, start_date, end_date) List[WorkHistoryEntry]
        + get_by_employee_date_range(self, employee_id, start_date, end_date) List[WorkHistoryEntry]
        + delete(self, employee_id, workstation_id, worked_date, work_period) bool
        + delete_by_id(self, id) bool
        + get(self, id) Optional[WorkHistoryEntry]
        + get_by_id(self, id) Optional[WorkHistoryEntry]
        + get_all_entities(self) List[WorkHistoryEntry]
        - _to_domain(self, model) WorkHistoryEntry
        - _to_model(self, entity) EmployeeWorkHistoryModel
        - _update_model(self, model, entity) None
        + update_by_id(self, id, employee_id, workstation_id, date_obj, period, schedule_id, status, is_generated, is_temporary) Optional[WorkHistoryEntry]
        + get_filtered(self, team_id, employee_id, workstation_id, start_date, end_date, period, status, is_generated, skip, limit) Tuple[List[WorkHistoryEntry], int]
        + get_distinct_stations(self, employee_id, since, until) Set[int]
        + get_distinct_station_periods(self, employee_id, since, until) Set[Tuple[int, int]]
        + get_station_period_counts(self, employee_id, since, until) Dict[int, Dict[int, int]]
    }

    class SqlAlchemyGroupRepository {
        - __init__(self, session) None
        + get_by_name(self, group_name) Optional[Group]
        - _to_domain(self, model) Group
        - _to_model(self, entity) GroupModel
        - _update_model(self, model, entity) None
        + get_by_id(self, entity_id) Optional[Group]
        + add(self, entity) Group
        + update(self, entity) Group
        + delete(self, entity_id) bool
        + list_all(self) List[Group]
    }

    class SqlAlchemyLineTypeRepository {
        - __init__(self, session) None
        - _to_domain(self, model) LineType
        - _to_model(self, entity) LineTypeModel
        - _update_model(self, model, entity) None
        + add(self, line_type) LineType
        + get_by_id(self, line_type_id) Optional[LineType]
        + get_by_name(self, name) Optional[LineType]
        + get_all(self) List[LineType]
        + update(self, line_type_id, line_type) LineType
        + delete(self, line_type_id) bool
    }

    class SqlAlchemyRefreshTokenRepository {
        - __init__(self, session) None
        + session_scope(self) Generator[Session, None, None]
        + get_by_token_id(self, token_id) Optional[RefreshToken]
        + get_active_tokens_for_user(self, user_id) List[RefreshToken]
        + revoke_token(self, token_id, source_ip, user_agent) bool
        + revoke_all_tokens_for_user(self, user_id, source_ip, user_agent) int
        + delete_expired_tokens(self, before_date) int
        + token_exists(self, token_id) bool
        - _to_domain(self, model) RefreshToken
        - _to_model(self, entity) RefreshTokenModel
        - _update_model(self, model, entity) None
    }

    class SqlAlchemyScheduleRepository {
        + session_scope(self) Generator[Session, None, None]
        - __init__(self, session) None
        + get_by_task_id(self, task_id) Optional[Schedule]
        + get_by_team_id(self, team_id, start_date, end_date, status, skip, limit) List[Schedule]
        + create_schedule(self, team_id, start_date, periods_per_day, call_ins, offline, force_complete) Schedule
        + update_status(self, schedule_id, status, error_message) Optional[Schedule]
        + count(self, team_id, start_date, end_date, status) int
        - _to_domain(self, model) Schedule
        - _to_model(self, entity) ScheduleModel
        - _update_model(self, model, entity) None
    }

    class SqlAlchemyTeamAroRepository {
        - __init__(self, session) None
        + session_scope(self) Generator[Session, None, None]
        + get(self, team_aro_id) Optional[TeamAro]
        + get_by_employee_id(self, employee_id) List[TeamAro]
        + get_by_team_id(self, team_id) List[TeamAro]
        + get_by_status(self, status) List[TeamAro]
        + update_status(self, team_aro_id, new_status) bool
        + remove(self, team_aro_id) bool
        - _to_domain(self, model) TeamAro
        - _to_model(self, entity) TeamAroModel
        - _update_model(self, model, entity) None
    }

    class SqlAlchemyTeamMemberRepository {
        - __init__(self, session) None
        + session_scope(self) Generator[Session, None, None]
        + get_by_team_id(self, team_id) List[TeamMember]
        + get_by_employee_id(self, employee_id) List[TeamMember]
        + add_role(self, team_member_id, role_name) bool
        + remove_role(self, team_member_id, role_name) bool
        + get_roles(self, team_member_id) List[str]
        + get_by_team_and_employee(self, team_id, employee_id) Optional[TeamMember]
        - _to_domain(self, model) TeamMember
        - _to_model(self, entity) TeamMemberModel
        - _update_model(self, model, entity) None
    }

    class SqlAlchemyTeamRepository {
        - __init__(self, session) None
        + get(self, id) Optional[Team]
        + get_all(self) List[Team]
        + get_by_name(self, name) Optional[Team]
        + add_member(self, team_id, employee) bool
        + remove_member(self, team_id, employee_id) bool
        + get_members(self, team_id) List[Employee]
        + add_workstation(self, team_id, workstation) bool
        + remove_workstation(self, team_id, workstation_id) bool
        + get_workstations(self, team_id) List[Workstation]
        + get_by_group_name(self, group_name) List[Team]
        + get_by_department_name(self, department_name) List[Team]
        + get_by_department_id(self, department_id) List[Team]
        + get_group(self, team_id) Optional[Any]
        + get_department(self, department_id) Optional[Any]
        + get_with_counts(self, team_id) Optional[Dict[str, Any]]
        - _to_domain(self, model) Team
        - _to_model(self, entity) TeamModel
        - _update_model(self, model, entity) None
    }

    class SqlAlchemyUserRepository {
        - __init__(self, session) None
        + session_scope(self) Generator[Session, None, None]
        + get_by_username(self, username) Optional[User]
        + get_by_email(self, email) Optional[User]
        + username_exists(self, username) bool
        + email_exists(self, email) bool
        + update_last_login(self, user_id, ip_address, user_agent) bool
        + add_role(self, user_id, role_name, source_ip, user_agent) bool
        + remove_role(self, user_id, role_name, source_ip, user_agent) bool
        + get_users_by_role(self, role_name) List[User]
        + activate_user(self, user_id, source_ip, user_agent) bool
        + deactivate_user(self, user_id, source_ip, user_agent) bool
        - _to_domain(self, model) User
        - _to_model(self, entity) UserModel
        - _update_model(self, model, entity) None
    }

    class SqlAlchemyWorkstationRepository {
        - __init__(self, session) None
        + get(self, id) Optional[Workstation]
        + add(self, entity) Workstation
        + update(self, entity) Workstation
        + delete(self, entity_id) bool
        + get_filtered(self, team_id, team_ids, is_active, skip, limit, eager, count_total) Tuple[List[Workstation], Optional[int]]
        + get_all(self, team_id, is_active, skip, limit) List[Workstation]
        + get_by_name(self, name) Optional[Workstation]
        + get_by_team_id(self, team_id) List[Workstation]
        + get_by_team_ids(self, team_ids) List[Workstation]
        - _fetch_line_type(self, name) LineTypeModel
        - _to_domain(self, model) Workstation
        - _to_model(self, entity, for_update) WorkstationModel
        - _update_model(self, model, entity) None
    }

    class ApiKeyRepositoryInterface {
        + get_by_key_id(self, key_id) Optional[ApiKey]
        + get_by_key_value(self, key_value) Optional[ApiKey]
        + get_active_keys_for_user(self, user_id) List[ApiKey]
        + deactivate_key(self, key_id) bool
        + deactivate_all_keys_for_user(self, user_id) int
        + key_exists(self, key_value) bool
    }

    class AROAssignmentRepositoryInterface {
        + get_by_date(self, assignment_date) List[AROAssignment]
        + get_by_employee_id(self, employee_id, assignment_date) List[AROAssignment]
        + get_by_from_team_id(self, team_id, assignment_date) List[AROAssignment]
        + get_by_to_team_id(self, team_id, assignment_date) List[AROAssignment]
        + get_employees_leaving(self, team_id, assignment_date, period) List[int]
        + get_employees_joining(self, team_id, assignment_date, period) List[int]
    }

    class AssignmentRepositoryInterface {
        + save_all(self, assignments) bool
        + get_by_employee_id(self, employee_id) List[WorkAssignment]
        + get_by_workstation_id(self, workstation_id) List[WorkAssignment]
        + get_by_schedule_id(self, schedule_id) List[WorkAssignment]
        + create_temporary_assignment(self, employee_id, workstation_id, date, period, schedule_id) bool
    }

    class BaseRepository {
        + get_by_id(self, entity_id) Optional[T]
        + list_all(self) List[T]
        + add(self, entity) T
        + update(self, entity) T
        + delete(self, entity_id) bool
    }

    class DepartmentRepositoryInterface {
        + get_by_name(self, department_name) Optional[Department]
        + get_all_with_groups(self) List[Department]
    }

    class EmployeeRepositoryInterface {
        + get(self, employee_id) Optional[Employee]
        + get_by_team_id(self, team_id) List[Employee]
        + is_available(self, employee_id, date_obj, period) bool
        + assign_role(self, employee_id, role_name, team_id) Dict[str, str]
        + remove_role(self, employee_id, role_name, team_id) Dict[str, str]
        + assign_workstation(self, employee_id, workstation_id) Dict[str, str]
        + get_work_history(self, employee_id, workstation_id) list
        + add_work_history(self, employee_id, workstation_id, worked_date, work_period, end_flag) bool
        + get_last_worked_date(self, employee_id, workstation_id) Tuple[Optional[date], Optional[int]]
        + get_by_team_ids(self, team_ids) List[Employee]
    }

    class EmployeeTrainingRepositoryInterface {
        + add(self, training) EmployeeTraining
        + get_by_employee_and_workstation(self, employee_id, workstation_id) Optional[EmployeeTraining]
        + get_by_employee(self, employee_id) List[EmployeeTraining]
        + get_by_workstation(self, workstation_id) List[EmployeeTraining]
        + get_completed_trainings(self, employee_id) List[EmployeeTraining]
        + get_required_trainings(self, employee_id) List[EmployeeTraining]
        + update_training_status(self, employee_id, workstation_id, required, date_completed) Optional[EmployeeTraining]
        + delete(self, employee_id, workstation_id) bool
    }

    class EmployeeWorkstationRepositoryInterface {
        + add(self, assignment) WorkstationAssignment
        + get_by_employee_and_workstation(self, employee_id, workstation_id) Optional[WorkstationAssignment]
        + get_by_employee(self, employee_id) List[WorkstationAssignment]
        + get_by_workstation(self, workstation_id) List[WorkstationAssignment]
        + update_last_worked_date(self, employee_id, workstation_id, last_worked_date) Optional[WorkstationAssignment]
        + delete(self, employee_id, workstation_id) bool
    }

    class EmployeeWorkHistoryRepositoryInterface {
        + add(self, work_history_entry) WorkHistoryEntry
        + create(self, employee_id, workstation_id, date_obj, period, schedule_id, status) WorkHistoryEntry
        + get_by_employee_and_workstation(self, employee_id, workstation_id) List[WorkHistoryEntry]
        + get_last_worked_date(self, employee_id, workstation_id) Tuple[Optional[date], Optional[int]]
        + get_by_date_range(self, start_date, end_date) List[WorkHistoryEntry]
        + get_by_employee_date_range(self, employee_id, start_date, end_date) List[WorkHistoryEntry]
        + delete(self, employee_id, workstation_id, worked_date, work_period) bool
        + get_filtered(self, team_id, employee_id, workstation_id, start_date, end_date, period, status, is_generated, skip, limit) Tuple[List[WorkHistoryEntry], int]
        + get_distinct_stations(self, employee_id, since, until) Set[int]
        + get_distinct_station_periods(self, employee_id, since, until) Set[Tuple[int, int]]
        + get_station_period_counts(self, employee_id, since, until) Dict[int, Dict[int, int]]
        + update_by_id(self, id, employee_id, workstation_id, date_obj, period, schedule_id, status, is_generated, is_temporary) Optional[WorkHistoryEntry]
    }

    class GroupRepositoryInterface {
        + get_by_name(self, group_name) Optional[Group]
    }

    class LineTypeRepositoryInterface {
        + add(self, line_type) LineType
        + get_by_id(self, line_type_id) Optional[LineType]
        + get_by_name(self, name) Optional[LineType]
        + get_all(self) List[LineType]
        + update(self, line_type_id, line_type) LineType
        + delete(self, line_type_id) bool
    }

    class RefreshTokenRepositoryInterface {
        + get_by_token_id(self, token_id) Optional[RefreshToken]
        + get_active_tokens_for_user(self, user_id) List[RefreshToken]
        + revoke_token(self, token_id) bool
        + revoke_all_tokens_for_user(self, user_id) int
        + delete_expired_tokens(self, before_date) int
        + token_exists(self, token_id) bool
    }

    class RoleRepositoryInterface {
        + get_by_name(self, name) Optional[Role]
        + name_exists(self, name) bool
        + get_all_roles(self) List[Role]
        + create_role(self, name, description) Role
        + update_role(self, role_id, name, description) Optional[Role]
        + delete_role(self, role_id) bool
        + get_roles_for_team_member(self, team_member_id) List[Role]
        + assign_role_to_team_member(self, team_member_id, role_id) bool
        + remove_role_from_team_member(self, team_member_id, role_id) bool
    }

    class ScheduleRepository {
        + create(self, team_id, start_date, periods, call_ins, offline, force_complete) ScheduleModel
        + get_by_id(self, schedule_id) Optional[ScheduleModel]
        + get_by_task_id(self, task_id) Optional[ScheduleModel]
        + update(self, schedule_id, **kwargs) Optional[ScheduleModel]
        + get_all(self, team_id, start_date, end_date, status, skip, limit) List[ScheduleModel]
        + count(self, team_id, start_date, end_date, status) int
    }

    class ScheduleRepositoryInterface {
        + get_by_task_id(self, task_id) Optional[Schedule]
        + get_by_team_id(self, team_id, start_date, end_date, status, skip, limit) List[Schedule]
        + create_schedule(self, team_id, start_date, periods, call_ins, offline, force_complete) Schedule
        + update_status(self, schedule_id, status, error_message) Optional[Schedule]
        + count(self, team_id, start_date, end_date, status) int
    }

    class SeedDataRepositoryInterface {
        + load_workstation_data(self, team_name) List[WorkstationSeedData]
        + load_employee_data(self, team_name) List[EmployeeSeedData]
        + load_team_data(self, team_name) TeamSeedData
        + load_group_data(self, group_name) GroupSeedData
        + load_department_data(self, department_name) DepartmentSeedData
        + get_available_departments(self) List[str]
        + get_available_groups(self, department_name) List[str]
        + get_available_teams(self, department_name, group_name) List[str]
    }

    class TeamAroRepositoryInterface {
        + get(self, team_aro_id) Optional[TeamAro]
        + get_by_employee_id(self, employee_id) List[TeamAro]
        + get_by_team_id(self, team_id) List[TeamAro]
        + get_by_status(self, status) List[TeamAro]
        + add(self, team_aro) TeamAro
        + update_status(self, team_aro_id, new_status) bool
        + remove(self, team_aro_id) bool
    }

    class TeamMemberRepositoryInterface {
        + get_by_team_id(self, team_id) List[TeamMember]
        + get_by_employee_id(self, employee_id) List[TeamMember]
        + add_role(self, team_member_id, role_name) bool
        + remove_role(self, team_member_id, role_name) bool
        + get_roles(self, team_member_id) List[str]
        + get_by_team_and_employee(self, team_id, employee_id) Optional[TeamMember]
    }

    class TeamRepositoryInterface {
        + get(self, team_id) Optional[Team]
        + get_by_name(self, name) Optional[Team]
        + add_member(self, team_id, employee) bool
        + remove_member(self, team_id, employee_id) bool
        + add_workstation(self, team_id, workstation) bool
        + remove_workstation(self, team_id, workstation_id) bool
        + get_members(self, team_id) List[Employee]
        + get_workstations(self, team_id) List[Workstation]
        + get_with_counts(self, team_id) Optional[dict]
        + get_by_group_name(self, group_name) List[Team]
        + get_by_department_name(self, department_name) List[Team]
        + get_group(self, team_id) Optional[Any]
        + get_department(self, department_id) Optional[Any]
    }

    class UserRepositoryInterface {
        + get_by_username(self, username) Optional[User]
        + get_by_email(self, email) Optional[User]
        + username_exists(self, username) bool
        + email_exists(self, email) bool
        + update_last_login(self, user_id, ip_address, user_agent) bool
        + add_role(self, user_id, role_name) bool
        + remove_role(self, user_id, role_name) bool
        + get_users_by_role(self, role_name) List[User]
        + activate_user(self, user_id) bool
        + deactivate_user(self, user_id) bool
    }

    class WorkstationRepositoryInterface {
        + get_by_team_id(self, team_id) List[Workstation]
        + get_all(self, team_id, is_active, skip, limit) List[Workstation]
        + get_by_team_ids(self, team_ids) List[Workstation]
    }

    class MockAssignmentRepository {
        - __init__(self) None
        + get_by_id(self, entity_id) Optional[WorkAssignment]
        + list_all(self) List[WorkAssignment]
        + add(self, entity) WorkAssignment
        + update(self, entity) WorkAssignment
        + delete(self, entity_id) bool
        + save_all(self, assignments) bool
        + get_by_employee_id(self, employee_id) List[WorkAssignment]
        + get_by_workstation_id(self, workstation_id) List[WorkAssignment]
    }

    class MockDepartmentRepository {
        - __init__(self) None
        + add(self, entity) Department
        + get(self, id) Optional[Department]
        + get_all(self) List[Department]
        + update(self, entity) Department
        + delete(self, id) bool
        + get_by_name(self, department_name) Optional[Department]
        + get_all_with_groups(self) List[Department]
    }

    class MockEmployeeRepository {
        - __init__(self) None
        + get_by_id(self, entity_id) Optional[Employee]
        + list_all(self) List[Employee]
        + add(self, entity) Employee
        + update(self, entity) Employee
        + delete(self, entity_id) bool
        + get_by_team_id(self, team_id) List[Employee]
        + is_available(self, employee_id, date_obj, period) bool
        + assign_role(self, employee_id, role_name, team_id) Dict[str, str]
        + remove_role(self, employee_id, role_name, team_id) Dict[str, str]
        + assign_workstation(self, employee_id, workstation_id) Dict[str, str]
        + get_work_history(self, employee_id, workstation_id) list
        + add_work_history(self, employee_id, workstation_id, worked_date, work_period, end_flag) bool
        + get_last_worked_date(self, employee_id, workstation_id) Tuple[Optional[date], Optional[int]]
    }

    class MockEmployeeTrainingRepository {
        - __init__(self) None
        + add(self, training) EmployeeTraining
        + get_by_employee_and_workstation(self, employee_id, workstation_id) Optional[EmployeeTraining]
        + get_by_employee(self, employee_id) List[EmployeeTraining]
        + get_by_workstation(self, workstation_id) List[EmployeeTraining]
        + get_completed_trainings(self, employee_id) List[EmployeeTraining]
        + get_required_trainings(self, employee_id) List[EmployeeTraining]
        + update_training_status(self, employee_id, workstation_id, required, date_completed) Optional[EmployeeTraining]
        + delete(self, employee_id, workstation_id) bool
        + get(self, id) Optional[EmployeeTraining]
        + get_all_entities(self) List[EmployeeTraining]
        + clear(self) None
    }

    class MockEmployeeWorkstationRepository {
        - __init__(self) None
        + add(self, assignment) WorkstationAssignment
        + get_by_employee_and_workstation(self, employee_id, workstation_id) Optional[WorkstationAssignment]
        + get_by_employee(self, employee_id) List[WorkstationAssignment]
        + get_by_workstation(self, workstation_id) List[WorkstationAssignment]
        + update_last_worked_date(self, employee_id, workstation_id, last_worked_date) Optional[WorkstationAssignment]
        + delete(self, employee_id, workstation_id) bool
        + get(self, id) Optional[WorkstationAssignment]
        + get_all_entities(self) List[WorkstationAssignment]
        + clear(self) None
    }

    class MockEmployeeWorkHistoryRepository {
        - __init__(self) None
        + add(self, work_history_entry) WorkHistoryEntry
        + get_by_employee_and_workstation(self, employee_id, workstation_id) List[WorkHistoryEntry]
        + get_last_worked_date(self, employee_id, workstation_id) Tuple[Optional[date], Optional[int]]
        + get_by_date_range(self, start_date, end_date) List[WorkHistoryEntry]
        + get_by_employee_date_range(self, employee_id, start_date, end_date) List[WorkHistoryEntry]
        + delete(self, employee_id, workstation_id, worked_date, work_period) bool
        + get(self, id) Optional[WorkHistoryEntry]
        + get_all_entities(self) List[WorkHistoryEntry]
        + clear(self) None
    }

    class MockGroupRepository {
        - __init__(self) None
        + get_by_id(self, entity_id) Optional[Group]
        + list_all(self) List[Group]
        + add(self, entity) Group
        + update(self, entity) Group
        + delete(self, entity_id) bool
        + get_by_name(self, group_name) Optional[Group]
    }

    class MockLineTypeRepository {
        - __init__(self) None
        + add(self, line_type) LineType
        + get_by_id(self, line_type_id) Optional[LineType]
        + get_by_name(self, name) Optional[LineType]
        + get_all(self) List[LineType]
        + update(self, line_type_id, line_type) LineType
        + delete(self, line_type_id) bool
        + get(self, id) Optional[LineType]
        + get_all_entities(self) List[LineType]
    }

    class MockScheduleRepository {
        - __init__(self) None
        + get_by_id(self, entity_id) Optional[Schedule]
        + list_all(self) List[Schedule]
        + add(self, entity) Schedule
        + update(self, entity) Schedule
        + delete(self, entity_id) bool
        + get_by_task_id(self, task_id) Optional[Schedule]
        + get_by_team_id(self, team_id, start_date, end_date, status, skip, limit) List[Schedule]
        + create_schedule(self, team_id, start_date, days, periods_per_day, call_ins, offline, force_complete) Schedule
        + update_status(self, schedule_id, status, error_message) Optional[Schedule]
        + count(self, team_id, start_date, end_date, status) int
    }

    class MockTeamMemberRepository {
        - __init__(self) None
        + get_by_id(self, entity_id) Optional[TeamMember]
        + list_all(self) List[TeamMember]
        + add(self, entity) TeamMember
        + update(self, entity) TeamMember
        + delete(self, entity_id) bool
        + get_by_team_id(self, team_id) List[TeamMember]
        + get_by_employee_id(self, employee_id) List[TeamMember]
        + add_role(self, team_member_id, role_name) bool
        + remove_role(self, team_member_id, role_name) bool
        + get_roles(self, team_member_id) List[str]
        + get_by_team_and_employee(self, team_id, employee_id) Optional[TeamMember]
    }

    class MockTeamRepository {
        - __init__(self) None
        + get_by_id(self, entity_id) Optional[Team]
        + list_all(self) List[Team]
        + add(self, entity) Team
        + update(self, entity) Team
        + delete(self, entity_id) bool
        + get_by_name(self, team_name) Optional[Team]
        + add_member(self, team_id, employee) bool
        + remove_member(self, team_id, employee_id) bool
        + add_workstation(self, team_id, workstation) bool
        + remove_workstation(self, team_id, workstation_id) bool
        + get_members(self, team_id) List[Employee]
        + get_workstations(self, team_id) List[Workstation]
    }

    class MockWorkstationRepository {
        - __init__(self) None
        + get_by_id(self, entity_id) Optional[Workstation]
        + list_all(self) List[Workstation]
        + add(self, entity) Workstation
        + update(self, entity) Workstation
        + delete(self, entity_id) bool
        + get_by_team_id(self, team_id) List[Workstation]
    }

    class TestEmployeeRepository {
        + setUp(self)
        + test_get_by_id(self)
        + test_list_all(self)
        + test_add(self)
        + test_update(self)
        + test_delete(self)
        + test_get_by_team_id(self)
        + test_assign_role(self)
        + test_remove_role(self)
        + test_work_history(self)
    }

    class TestScheduleRepository {
        + setUp(self)
        + test_get_by_id(self)
        + test_list_all(self)
        + test_add(self)
        + test_update(self)
        + test_delete(self)
        + test_get_by_task_id(self)
        + test_get_by_team_id(self)
        + test_create_schedule(self)
        + test_update_status(self)
        + test_count(self)
    }

    FileSeedDataRepository --|> `domain.repositories.interfaces.seed_data_repository.SeedDataRepositoryInterface`

    SqlAlchemyAROAssignmentRepository --|> `BaseSqlAlchemyRepository[AROAssignment, AROAssignmentModel]`

    SqlAlchemyAROAssignmentRepository --|> `domain.repositories.interfaces.aro_assignment_repository.AROAssignmentRepositoryInterface`

    SqlAlchemyAssignmentRepository --|> `BaseSqlAlchemyRepository[WorkAssignment, EmployeeWorkHistoryModel]`

    SqlAlchemyAssignmentRepository --|> `domain.repositories.interfaces.assignment_repository.AssignmentRepositoryInterface`

    SqlAlchemyDepartmentRepository --|> `BaseSqlAlchemyRepository[Department, DepartmentModel]`

    SqlAlchemyDepartmentRepository --|> `domain.repositories.interfaces.department_repository.DepartmentRepositoryInterface`

    SqlAlchemyEmployeeRepository --|> `BaseSqlAlchemyRepository[Employee, EmployeeModel]`

    SqlAlchemyEmployeeRepository --|> `domain.repositories.interfaces.employee_repository.EmployeeRepositoryInterface`

    SqlAlchemyEmployeeTrainingRepository --|> `BaseSqlAlchemyRepository[EmployeeTraining, EmployeeTrainingModel]`

    SqlAlchemyEmployeeTrainingRepository --|> `domain.repositories.interfaces.employee_training_repository.EmployeeTrainingRepositoryInterface`

    SqlAlchemyEmployeeWorkstationRepository --|> `BaseSqlAlchemyRepository[WorkstationAssignment, EmployeeWorkstationModel]`

    SqlAlchemyEmployeeWorkstationRepository --|> `domain.repositories.interfaces.employee_workstation_repository.EmployeeWorkstationRepositoryInterface`

    SqlAlchemyEmployeeWorkHistoryRepository --|> `BaseSqlAlchemyRepository[WorkHistoryEntry, EmployeeWorkHistoryModel]`

    SqlAlchemyEmployeeWorkHistoryRepository --|> `domain.repositories.interfaces.employee_work_history_repository.EmployeeWorkHistoryRepositoryInterface`

    SqlAlchemyGroupRepository --|> `BaseSqlAlchemyRepository[Group, GroupModel]`

    SqlAlchemyGroupRepository --|> `domain.repositories.interfaces.group_repository.GroupRepositoryInterface`

    SqlAlchemyLineTypeRepository --|> `infrastructure.repositories.sqlalchemy.base_sqlalchemy_repository.BaseSqlAlchemyRepository`

    SqlAlchemyLineTypeRepository --|> `domain.repositories.interfaces.line_type_repository.LineTypeRepositoryInterface`

    SqlAlchemyRefreshTokenRepository --|> `BaseSqlAlchemyRepository[RefreshToken, RefreshTokenModel]`

    SqlAlchemyRefreshTokenRepository --|> `domain.repositories.interfaces.refresh_token_repository.RefreshTokenRepositoryInterface`

    SqlAlchemyScheduleRepository --|> `BaseSqlAlchemyRepository[Schedule, ScheduleModel]`

    SqlAlchemyScheduleRepository --|> `domain.repositories.interfaces.schedule_repository_interface.ScheduleRepositoryInterface`

    SqlAlchemyTeamAroRepository --|> `BaseSqlAlchemyRepository[TeamAro, TeamAroModel]`

    SqlAlchemyTeamAroRepository --|> `domain.repositories.interfaces.team_aro_repository.TeamAroRepositoryInterface`

    SqlAlchemyTeamMemberRepository --|> `BaseSqlAlchemyRepository[TeamMember, TeamMemberModel]`

    SqlAlchemyTeamMemberRepository --|> `domain.repositories.interfaces.team_member_repository.TeamMemberRepositoryInterface`

    SqlAlchemyTeamRepository --|> `BaseSqlAlchemyRepository[Team, TeamModel]`

    SqlAlchemyTeamRepository --|> `domain.repositories.interfaces.team_repository.TeamRepositoryInterface`

    SqlAlchemyUserRepository --|> `BaseSqlAlchemyRepository[User, UserModel]`

    SqlAlchemyUserRepository --|> `domain.repositories.interfaces.user_repository.UserRepositoryInterface`

    SqlAlchemyWorkstationRepository --|> `BaseSqlAlchemyRepository[Workstation, WorkstationModel]`

    SqlAlchemyWorkstationRepository --|> `domain.repositories.interfaces.workstation_repository.WorkstationRepositoryInterface`

    ApiKeyRepositoryInterface --|> `BaseRepository[ApiKey]`

    AROAssignmentRepositoryInterface --|> `BaseRepository[AROAssignment]`

    AssignmentRepositoryInterface --|> `BaseRepository[WorkAssignment]`

    BaseRepository --|> `Generic[T]`

    BaseRepository --|> `abc.ABC`

    DepartmentRepositoryInterface --|> `BaseRepository[Department]`

    EmployeeRepositoryInterface --|> `BaseRepository[Employee]`

    EmployeeTrainingRepositoryInterface --|> `BaseRepository[EmployeeTraining]`

    EmployeeWorkstationRepositoryInterface --|> `BaseRepository[WorkstationAssignment]`

    EmployeeWorkHistoryRepositoryInterface --|> `BaseRepository[WorkHistoryEntry]`

    GroupRepositoryInterface --|> `BaseRepository[Group]`

    LineTypeRepositoryInterface --|> `BaseRepository[LineType]`

    RefreshTokenRepositoryInterface --|> `BaseRepository[RefreshToken]`

    RoleRepositoryInterface --|> `BaseRepository[Role]`

    ScheduleRepository --|> `abc.ABC`

    ScheduleRepositoryInterface --|> `BaseRepository[Schedule]`

    TeamAroRepositoryInterface --|> `BaseRepository[TeamAro]`

    TeamMemberRepositoryInterface --|> `BaseRepository[TeamMember]`

    TeamRepositoryInterface --|> `BaseRepository[Team]`

    UserRepositoryInterface --|> `BaseRepository[User]`

    WorkstationRepositoryInterface --|> `BaseRepository[Workstation]`

    MockAssignmentRepository --|> `domain.repositories.interfaces.assignment_repository.AssignmentRepositoryInterface`

    MockDepartmentRepository --|> `domain.repositories.interfaces.department_repository.DepartmentRepositoryInterface`

    MockEmployeeRepository --|> `domain.repositories.interfaces.employee_repository.EmployeeRepositoryInterface`

    MockEmployeeTrainingRepository --|> `domain.repositories.interfaces.employee_training_repository.EmployeeTrainingRepositoryInterface`

    MockEmployeeWorkstationRepository --|> `domain.repositories.interfaces.employee_workstation_repository.EmployeeWorkstationRepositoryInterface`

    MockEmployeeWorkHistoryRepository --|> `domain.repositories.interfaces.employee_work_history_repository.EmployeeWorkHistoryRepositoryInterface`

    MockGroupRepository --|> `domain.repositories.interfaces.group_repository.GroupRepositoryInterface`

    MockLineTypeRepository --|> `domain.repositories.interfaces.line_type_repository.LineTypeRepositoryInterface`

    MockScheduleRepository --|> `domain.repositories.interfaces.schedule_repository_interface.ScheduleRepositoryInterface`

    MockTeamMemberRepository --|> `domain.repositories.interfaces.team_member_repository.TeamMemberRepositoryInterface`

    MockTeamRepository --|> `domain.repositories.interfaces.team_repository.TeamRepositoryInterface`

    MockWorkstationRepository --|> `domain.repositories.interfaces.workstation_repository.WorkstationRepositoryInterface`

    TestEmployeeRepository --|> `unittest.TestCase`

    TestScheduleRepository --|> `unittest.TestCase`
```
