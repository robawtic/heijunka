from fastapi import APIRouter
from presentation.api.routes import employees, workstations, teams, schedules, assignments, status, auth, tasks

router = APIRouter()

router.include_router(employees.router, prefix="/employees", tags=["employees"])
router.include_router(workstations.router, prefix="/workstations", tags=["workstations"])
router.include_router(teams.router, prefix="/teams", tags=["teams"])
router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
router.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
router.include_router(status.router, prefix="/status", tags=["status"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
