# SevaFlow

SevaFlow is a queue-management project for service centres. Customers scan a QR code, review service information, register their name and phone number, and track their token. Staff operate their assigned counter through a live workstation.

The FastAPI backend owns queue order, registration deadlines, assignments, and recalls. The customer and staff frontends display that state and submit authenticated actions.

## Current status

| Module | Status |
| --- | --- |
| Customer welcome and registration | Connected to the backend; English/Hindi toggle and light sky-blue UI |
| Customer tracking | Live polling for token status, counter assignment, people ahead, and approximate waiting time |
| Staff workstation | Real login, assigned-counter access, Call Next, Start Service, Complete & Next, Pause/Resume |
| Missed customers | Initial miss, two recall opportunities, and explicit closure after the second unsuccessful recall |
| Admin monitoring | Real admin login and live Overview, Queues, and Counters; Analytics uses recorded timestamps; Predictions uses a provisional historical-demand baseline |
| Hardware | Reservation API exists; Pico W firmware and end-to-end kiosk integration are unfinished |
| Notifications | Live page updates; no SMS provider connected |

**Recall limitation:** only one pending missed customer per counter is currently supported. A second initial miss is rejected without changing either token until the multiple-missed policy is settled. With no intervening service completion, the missed token stays pending; it is not automatically recalled or closed.

## Customer and queue flow

```mermaid
flowchart LR
    R[Hardware reservation] --> C[Successful QR claim]
    C --> W[Welcome and service information]
    W -->|Accept| N[Name and phone registration]
    W -->|Reject| X[Reservation cancelled]
    N --> Q[Waiting and live tracking]
    Q --> A[Called to counter]
    A --> S[Staff starts service]
    S --> D[Service completed]
    A --> M[Marked missed]
    M --> I[Intervening service completes]
    I --> A
```

- A successful claim allocates scan priority once. Registration makes the token eligible for dispatch.
- Refreshes, rescans, and identical registration retries preserve priority and the original deadline.
- Registration deadlines are checked after transaction locks. Registered tokens survive that deadline.
- The original missed call does not consume a recall. Each unsuccessful recall consumes one opportunity; two close the token as `CLOSED_MISSED`, not `COMPLETED`.
- Staff commands preserve request identity across retries and check expected counter/token state before acting.
- Pausing retains the current customer and prevents new assignments. Completing a service while paused does not dispatch another token.

See [Operating rules](OPERATING_RULES.md) for the approved sequence and unresolved policy decisions.

## Architecture and repository layout

```text
Customer frontend ──┐
Staff frontend ─────┼── FastAPI core backend ── PostgreSQL
Hardware API client ┘        queue authority
```

```text
backend/                       FastAPI API, queue logic, authentication
  app/api/                     Customer, staff, workstation, hardware routes
  app/services/                Queue mutations and command retry protection
  app/models/                  SQLAlchemy models
  alembic/                     Database migrations
  tests/                       API, concurrency, and queue-contract tests
frontend/                      Staff workstation and admin/demo screens
customer/
  frontend/                    Customer welcome, registration, and tracking
  backend/                     Integration documentation for the core API
OPERATING_RULES.md              Queue and operating decisions
MEMORY.md                       Development history and implementation notes
```

`customer/backend/` is documentation, not a separate backend service.

**Stack:** Python 3.12, FastAPI, SQLAlchemy async, asyncpg, PostgreSQL, Alembic, React, TypeScript, and Vite. The staff/admin application also uses React Router and Zustand. Staff authentication uses JWT; hardware currently uses the `X-Hardware-Secret` shared-secret header, not signed HMAC requests.

## Local setup

The commands below use Windows PowerShell and start from the repository root containing `backend/`, `frontend/`, and `customer/`.

### Prerequisites

- Python 3.12.
- Node.js 22.12 or newer and npm. The staff Vite package requires Node `^20.19.0 || >=22.12.0`.
- PostgreSQL, or Docker Compose for the included PostgreSQL 15 development container.

### 1. Backend and database

```powershell
cd backend
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

For a new local development database, use the supplied Compose file:

```powershell
docker compose up -d db
```

It creates the `sevaflow` database on port 5432 using the development credentials in `backend/docker-compose.yml`. If PostgreSQL already uses that port, use your existing instance and create a database instead of starting this container.

For a fresh checkout, copy the environment template once:

```powershell
Copy-Item .env.example .env
```

Preserve an existing `.env`. Edit it so `DATABASE_URL` points to your database, and set separate values for `HARDWARE_SECRET` and `STAFF_JWT_SECRET`. The template does not include the JWT setting, so add it. Do not commit actual secrets.

| Setting | Purpose |
| --- | --- |
| `DATABASE_URL` | Async connection URL: `postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE` |
| `HARDWARE_SECRET` | Shared credential for hardware API access |
| `STAFF_JWT_SECRET` | Signing secret for staff sessions |
| `STAFF_JWT_EXPIRE_MINUTES` | Session duration; defaults to 480 minutes |

Apply migrations before starting the API:

```powershell
.\venv\Scripts\python.exe -B -m alembic upgrade head
.\venv\Scripts\python.exe -B -m uvicorn app.main:app --reload
```

- API documentation: [localhost:8000/docs](http://localhost:8000/docs)
- Health endpoint: [localhost:8000/health](http://localhost:8000/health)

Startup seeds services, queues, staff, and counters when no service record exists. It does not overwrite an already configured database. Fresh development seeds include `staff01` through `staff06` with password `sevaflow_staff`, and `admin` with password `sevaflow_admin`. These are development defaults: replace them before deployment. An administrator cannot operate the live staff workstation, and Predictions uses a provisional historical-demand baseline.

### 2. Staff frontend

In a second terminal, from the repository root:

```powershell
cd frontend
npm ci
npm run dev -- --strictPort
```

- Live staff login: [localhost:5173/staff](http://localhost:5173/staff)
- Preserved staff demo: [localhost:5173/staff/demo](http://localhost:5173/staff/demo)
- Live admin login: [localhost:5173/admin](http://localhost:5173/admin)

Use an active staff account assigned to exactly one counter. The development server proxies `/api` to the backend on port 8000.

### 3. Customer frontend

In a third terminal, from the repository root:

```powershell
cd customer/frontend
npm ci
npm run dev -- --strictPort
```

The customer application runs at [localhost:5174](http://localhost:5174). A real QR entry must reference an acknowledged reservation:

```text
http://localhost:5174/qr?cat=aadhar&qNo=A024&reservation=<hardware_reservation_id>#claim=<raw_claim_secret>
```

The short route `/qr?cat=aadhar&qNo=A024` alone cannot authorize a real claim. The browser saves its recovery credentials before claiming, removes the secret fragment from the displayed URL, and uses authenticated recovery after refresh. Do not clear browser storage while using an active token.

For a visual-only development preview, use `/qr?cat=aadhar&qNo=A024&preview=1`. This preserves the old mock flow and does not create a real reservation. For a real flow without hardware, follow the isolated browser fixture instructions in [Staff integration](frontend/STAFF_INTEGRATION.md).

Both frontends accept `SEVAFLOW_API_TARGET` to change the development proxy target. Production builds can use `VITE_API_BASE_URL`, or a same-origin `/api/v1` reverse proxy. Mobile access requires HTTPS for browser credential hashing; localhost also works.

## Tests and builds

From `backend/`:

```powershell
.\venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

The PostgreSQL integration tests create and remove disposable schemas. They use `TEST_DATABASE_URL` when set, otherwise the configured `DATABASE_URL`; the database role needs permission to create schemas. Coverage includes claim priority, lock-delayed expiry, registration recovery, counter ownership, duplicate/stale commands, pause behavior, and the single-missed two-recall sequence.

Run `npm run build` separately in `frontend/` and `customer/frontend/`.

Latest recorded verification: **45 backend tests passed**, and the staff production build passed. The customer production build passed during the earlier customer integration. Browser checks confirmed the normal service flow and missed-status display; the remaining recall-button visual checks were interrupted by browser interaction failures, while the full recall sequence passed API tests.

## Remaining work

- Decide and implement multiple-missed scheduling and end-of-day handling.
- Program the Pico W firmware, finish hardware retry validation, and verify QR issuance end to end.
- Align hardware service buttons, backend service IDs, and customer category labels before rollout.
- Validate the Predictions baseline against real operations and record opening/pause coverage before adding capacity or waiting-time forecasts.
- Finalize registration TTL: the implementation retains 15 minutes; the proposed shorter policy is not yet applied.
- Prepare deployment configuration, restricted CORS origins, HTTPS, and non-development accounts/secrets.

## Documentation

- [Queue and operating rules](OPERATING_RULES.md)
- [Customer frontend setup](customer/frontend/README.md)
- [Claim, registration, and recovery contract](customer/backend/README.md)
- [Staff workstation, commands, and browser testing](frontend/STAFF_INTEGRATION.md)
- [Admin monitoring and metric definitions](frontend/ADMIN_INTEGRATION.md)
- [Development history](MEMORY.md)
