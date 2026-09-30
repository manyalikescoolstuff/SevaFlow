# SevaFlow Backend — Project Memory

> **Last updated:** 2026-09-28  
> **Purpose:** Single reference for the project context, architecture, current state, and blockers.

---

## 1. What is SevaFlow?

SevaFlow (formerly Q-FLOW) is an **IoT-enabled queue management system** for MPOnline-type citizen service centres. Three clients consume the backend:

| Client       | Auth method              | Purpose                                   |
|:-------------|:-------------------------|:------------------------------------------|
| **Pico W**   | `X-Hardware-Secret` header | Generates tokens, reservation IDs, QR URLs |
| **Customer website** | Claim-secret from QR + browser session | Claim token, register, track status |
| **Staff/Admin SPA** | JWT (username/password)  | Call Next, Start Service, Mark Missed, etc. |

---

## 2. Workspace Layout

```
c:\Users\manya\OneDrive\Desktop\winners_of_sih4.0\q-flow\
├── backend/
│   ├── alembic/                   # Alembic migrations
│   │   ├── env.py                 # Async migration runner
│   │   └── versions/              # Migration scripts
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints.py       # Router aggregator
│   │   │   ├── hardware.py        # Pico W endpoints
│   │   │   ├── customer.py        # QR claim + registration
│   │   │   └── staff.py           # Auth + counter operations
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic Settings (.env)
│   │   │   ├── database.py        # Async engine + session
│   │   │   ├── deps.py            # get_current_staff dependency
│   │   │   └── security.py        # JWT, bcrypt, SHA-256, HMAC
│   │   ├── db/
│   │   │   └── seed.py            # Auto-seed on first startup
│   │   ├── models/
│   │   │   ├── __init__.py         # Re-exports Base
│   │   │   └── schema.py          # All SQLAlchemy models
│   │   ├── schemas/
│   │   │   ├── __init__.py         # BROKEN — imports Token, TokenCreate which don't exist
│   │   │   ├── token.py           # Pydantic schemas for token ops
│   │   │   ├── staff.py           # Login/response schemas
│   │   │   ├── counter.py         # Counter schema
│   │   │   ├── service.py         # Service schema
│   │   │   └── queue.py           # Queue schema
│   │   ├── services/
│   │   │   └── queue_manager.py   # All transactional state-machine logic
│   │   └── main.py                # FastAPI app + lifespan
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_model_logic.py    # 12 passing pure-logic tests
│   ├── .env                       # DATABASE_URL, HARDWARE_SECRET, STAFF_JWT_SECRET
│   ├── .env.example
│   ├── alembic.ini
│   ├── docker-compose.yml
│   ├── pytest.ini
│   ├── requirements.txt
│   └── setup_db.py               # One-shot DB+user creation script
├── frontend/                   # Staff/Admin SPA (React + TypeScript + Vite)
├── customer/
│   ├── frontend/               # Customer Mobile-First Web App (Stage 1 Complete)
│   └── backend/README.md       # Customer integration contract & responsibilities
└── (root files)

```

---

## 3. Database

- **Engine:** PostgreSQL 16/17/18 (native install, port 5432)
- **Database:** `sevaflow`
- **User:** `sevaflow_user` (password stored in `.env`, not here)
- **Driver:** `asyncpg` via SQLAlchemy `create_async_engine`
- **ORM:** SQLAlchemy 2.x async, DeclarativeBase

### Connection URL format
```
DATABASE_URL=postgresql+asyncpg://sevaflow_user:<password>@localhost/sevaflow
```

### Models (in `app/models/schema.py`)

| Model              | Table                | Purpose                                 |
|:-------------------|:---------------------|:----------------------------------------|
| `Service`          | `services`           | Available services (Aadhaar, PAN, etc.) |
| `Queue`            | `queues`             | One per service; owns `current_sequence` counter |
| `Token`            | `tokens`             | Full token lifecycle, scan ordering     |
| `Staff`            | `staff`              | Login credentials, role (STAFF/ADMIN)   |
| `Counter`          | `counters`           | Physical counter; `current_token_id` is authoritative |
| `EventLog`         | `event_logs`         | Immutable audit trail                   |
| `IdempotencyRecord`| `idempotency_records`| Pico W request deduplication            |

### Circular FK issue
`counters.current_token_id → tokens.id` and `tokens.missed_counter_id → counters.id` create a cycle. The migration must use `use_alter=True` / deferred FKs so tables can be created in any order.

---

## 4. Token State Machine

```
RESERVED → CLAIMED → WAITING → CALLED → SERVING → COMPLETED
                                  ↓
                               MISSED (recall_attempts < 2)
                                  ↓ (after 2 failed recalls)
                            CLOSED_MISSED
Also: EXPIRED, CANCELLED
```

### Recall rules (approved)
1. Staff marks CALLED token as MISSED → `recall_attempts` stays 0, `missed_counter_id` set.
2. After next service completes at that counter → recall MISSED token (CALLED).
3. If present → Start Service. No recall attempt consumed.
4. If absent → `recall_attempts += 1`, status back to MISSED.
5. After next service completes → recall again.
6. If absent → `recall_attempts = 2` → CLOSED_MISSED.

### Open policy questions
- **Multiple missed tokens:** Currently FIFO by `missed_at`, one at a time. NOT approved.
- **Empty queue after recall:** Unresolved.

---

## 5. Locking Order

All mutations acquire row locks in strict order to prevent deadlocks:
```
Queue (with_for_update) → Counter (with_for_update) → Token (with_for_update)
```

---

## 6. API Endpoints

### Hardware (`/api/v1/hardware`)
| Method | Path       | Auth              | Action              |
|:-------|:-----------|:------------------|:---------------------|
| POST   | `/tokens`  | X-Hardware-Secret | Reserve token (idempotent) |
| GET    | `/services`| X-Hardware-Secret | List available services    |

### Customer (`/api/v1/customer`)
| Method | Path                    | Auth        | Action                    |
|:-------|:------------------------|:------------|:--------------------------|
| POST   | `/claim`                | claim_secret| Claim token (RESERVED→CLAIMED) |
| POST   | `/register`             | session     | Register (CLAIMED→WAITING)     |
| GET    | `/token/{id}/status`    | none        | Poll token status              |

### Staff (`/api/v1`)
| Method | Path                              | Auth | Action                    |
|:-------|:----------------------------------|:-----|:--------------------------|
| POST   | `/auth/login`                     | form | Get JWT                   |
| GET    | `/auth/me`                        | JWT  | Current staff info        |
| GET    | `/counters/live`                  | none | Display board data        |
| GET    | `/queues/live`                    | none | Queue stats               |
| POST   | `/counters/{id}/next`             | JWT  | Complete & Next           |
| POST   | `/counters/{id}/start`            | JWT  | Start Service (CALLED→SERVING) |
| POST   | `/counters/{id}/missed`           | JWT  | Mark Missed               |
| POST   | `/counters/{id}/absent-again`     | JWT  | Recall absent again       |

---

## 7. Seed Data

Created on first startup by `app/db/seed.py`:
- 5 services, 5 queues, 6 counters, 7 staff
- Staff creds: `admin/sevaflow_admin`, `staff01-06/sevaflow_staff`
- Counter 6 is PAUSED

---

## 8. Known Bugs / Current Blockers

### FIXED: Migration circular FK
The autogenerated migration created `counters` first (which referenced `tokens.id`) before `tokens` existed → `UndefinedTableError`. Fixed `alembic/versions/9c8679bbfebc_initial_postgres_schema.py` to create base tables first and add circular foreign keys afterwards via `op.create_foreign_key`.

### FIXED: services/__init__.py imports `QueueManager`
Fixed `app/services/__init__.py` to import the `queue_manager` module instead of non-existent `QueueManager` class.

### FIXED: passlib bcrypt error on Python 3.12
Replaced `passlib` `CryptContext` in `app/core/security.py` with direct `bcrypt` (`hashpw`/`checkpw`) to resolve `AttributeError` and `ValueError` during database seeding.




### FIXED: `.env` had `JWT_SECRET` instead of `STAFF_JWT_SECRET`
Pydantic rejected the extra field. Fixed.

### FIXED: `%` in password caused configparser error in alembic env.py
Fixed with `.replace("%", "%%")`.

---

## 9. Tests

- `tests/test_model_logic.py` — **12/12 passing** (pure logic, no DB).
  - Token state machine transitions
  - Recall sequence (2-attempt lifecycle)
  - Scan ordering (sort_key priority)

- No integration/endpoint tests yet (need running DB + fixed migrations first).

---

## 10. Environment

- **OS:** Windows
- **Python:** 3.12.10
- **Virtualenv:** `backend/venv/`
- **PostgreSQL:** Native install, port 5432
- **Docker:** NOT available
- **psql:** Blocked by Device Guard policy (use `setup_db.py` instead)

---

## 11. Next Steps (in order)

1. **Fix migration:** Rewrite to handle circular FKs (create tables, then add FK constraints).
2. **Fix `schemas/__init__.py`:** Remove broken imports.
3. **Apply migration:** `alembic upgrade head`
4. **Start server:** Verify seed runs, all endpoints respond.
5. **Implement integration tests** for the core flow.
6. **Finalize open policy questions** (multiple missed tokens, empty queue).

## Customer contract update — 29 September 2026

The customer frontend now connects to the core API. Claim allocates priority once;
registration preserves that priority, persists name/phone and activates WAITING.
Recovery requires browser session plus recovery hash. Deadline checks run after
Queue -> Token locks; registered tokens recover beyond the registration deadline.
Migration c81f2a9d401e adds nullable customer fields without reordering existing data.
See customer/backend/README.md and customer/frontend/README.md for current contracts,
real QR credential format, run instructions and isolated PostgreSQL/browser tests.
The older Stage 1 description and next-steps list above are historical.

## Live staff update — 29 September 2026

The staff frontend `/staff` now uses actual login and assigned counter state;
`/staff/demo` preserves the previous demo. The new `/api/v1/staff/workstation` and
`/staff/counters/{id}/{next|start|pause|resume}` endpoints check ownership, stale
expectations and idempotent command fingerprints. Migration d34b1c607a2f is additive.
Counter pause preserves current service and prevents new dispatch. Existing JWT
helpers now import settings correctly. Missed/recall UI integration remains pending.
See frontend/STAFF_INTEGRATION.md. Pico firmware work remains on hold.

## Missed-customer implementation — 29 September 2026
- Live staff supports initial Mark Missed & Next, first recall absence, and explicit closure on second recall absence.
- An actual completed service sets persisted recall_ready; call/skip/retry/refresh cannot consume or create recall opportunities. Pause preserves readiness for resume.
- Initial priority and original missed timestamp remain unchanged. Recall exhaustion is CLOSED_MISSED with audit reason, not service completion or QR expiry.
- All missed routes use saved request identity and expected token state; recall absence also requires expected_recall_attempts to reject stale first-recall commands at the second recall.
- Single-missed scope only: a second initial miss while another token is MISSED returns 409 without mutation, pending a multiple-missed policy decision. Empty queue retains pending token without auto-recall/closure.
- Migration e52a7109bc63 applied. All 35 backend tests and staff production build pass. Isolated browser verification confirmed customer MISSED tracking and staff pending-recall list. Remaining recall-button browser checks were interrupted by browser click failures; the full sequence is verified by API tests.

## Live admin monitoring
- Added ADMIN-only GET /api/v1/admin/monitor, and authenticated /admin Overview, Queues, Counters using the existing shell and visual styles.
- Polls every five seconds; refresh keeps admin login, sign-out clears it, and failed authentication removes displayed data. No admin counter-operation controls added.
- Daily registrations/completions use Asia/Kolkata timestamp boundaries. Counter recorded completions are explicitly cumulative; no fictional daily reset or utilization metric.
- Customer PII/credentials excluded; next three registered waiting tokens shown per queue. No active counter produces unavailable wait.
- Original screens retained under /admin/demo/*; Analytics/Predictions explicitly labeled sample data.
- 38 backend tests and frontend build passed. Isolated browser checks passed login, navigation, refresh recovery, demo notice, and sign-out. See frontend/ADMIN_INTEGRATION.md.

## Live admin Analytics — 30 September 2026
- Added authenticated /admin/analytics endpoint and real Analytics page with date selection, hourly registrations, measured averages/sample counts, and per-service reporting.
- Asia/Kolkata day boundaries; completion-date averages include older registrations. Wait includes recall delay; service duration includes pauses. Invalid or missing timestamps do not fabricate averages.
- No utilization percentage without operating/pause history. Predictions stays a demo; original Analytics preserved at /admin/demo/analytics.
- 41 backend tests pass, including date boundaries, closure exclusion, access, empty reports, invalid/missing timestamps, and genuine zero durations. Frontend build passes.

## Predictions integration — 30 September 2026
- /admin/predictions now uses authenticated aggregate registrations from the last 28 completed local days. Original sample screen retained at /admin/demo/predictions.
- Provisional recorded-day mean for tomorrow; requires seven recorded days and last activity within seven days. Service estimate requires three recorded days. Today and unobserved days excluded; upward-selection bias and absent seasonality clearly disclosed.
- No fabricated confidence interval, waiting-time or queue-pressure forecast. Predictions never mutate queue/counter state.
- 45 backend tests and frontend build pass. Browser verified insufficient-history state and readable cards. Ready forecasts are covered by deterministic and PostgreSQL API tests.

## Customer email — stage 2 — 30 September 2026
- Registration now requires normalized email plus existing name and phone; email is stored on Token through migration f14c9b7d2e10.
- Authenticated retries preserve the email; changed email conflicts. Tracking/admin outputs exclude it.
- Customer frontend build passes; 45 backend tests pass. No mail delivery yet: current backend is FastAPI, and Nodemailer needs a separate Node service or an SMTP adapter.
- Before sending confirmations, choose provider/sender policy and add committed outbox/idempotency so SMTP failures cannot roll back or duplicate queue activation.
