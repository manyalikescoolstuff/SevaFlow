# SevaFlow Project Quick Context & Rules

## Project Summary
SevaFlow is an IoT-enabled queue management system for citizen service centres (e.g. MPOnline).
- **Backend:** FastAPI + SQLAlchemy 2 (Async) + PostgreSQL (`sevaflow` database)
- **Virtualenv:** `backend/venv`
- **Port:** PostgreSQL 5432 (Local native instance)

## Key Paths & Commands
- **Working Dir:** `c:\Users\manya\OneDrive\Desktop\winners_of_sih4.0\q-flow\backend`
- **Run Migrations:** `venv\Scripts\alembic.exe upgrade head`
- **Start FastAPI Dev Server:** `venv\Scripts\uvicorn.exe app.main:app --reload`
- **Run Unit Tests:** `venv\Scripts\pytest.exe`

## Database Connection
- `DATABASE_URL=postgresql+asyncpg://sevaflow_user:Bhavesh@localhost/sevaflow`

## State & Conventions
- **Memory File:** `MEMORY.md` at workspace root contains full technical specifications and resolved blockers.
- **Operating Rules:** `OPERATING_RULES.md` and `.agents/rules/queue_and_operating_rules.md` specify official physical admission, scan ordering, activation, and two-recall rules.
- **Circular FK:** Handled in Alembic migrations by adding FK constraints after creating `counters` and `tokens` tables.

