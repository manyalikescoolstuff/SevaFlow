# Live staff workstation

`/staff` now uses real FastAPI authentication and queue state. The original mock
workstation remains at `/staff/demo`; Admin pages are still the existing mock UI.

## Run

From `../backend`, apply migrations and run the API:

```powershell
.\venv\Scripts\python.exe -B -m alembic upgrade head
.\venv\Scripts\python.exe -B -m uvicorn app.main:app --reload
```

From this directory, run `npm run dev` and open `http://localhost:5173/staff`.
Sign in with an existing active STAFF account assigned to exactly one counter.
The frontend proxies `/api` to port 8000; `SEVAFLOW_API_TARGET` can select a test API.
A production build can set `VITE_API_BASE_URL`, or use a same-origin `/api/v1` proxy.

## Supported operations

- Call Next only while the counter is free and active.
- Start Service only for a CALLED token with the customer present.
- Mark Missed & Next for the initial CALLED customer; recall absence has a separate
  action and the second unsuccessful recall explicitly closes the token.
- Complete & Next only for a SERVING token.
- Pause retains the current customer. Completing while paused releases that customer
  but assigns nobody new. Resume makes the counter available again.
- Upcoming tokens are registered WAITING customers in backend scan order.
- Three-second polling updates the workstation; disconnected screens disable actions.
- Refresh keeps the login in sessionStorage. Passwords are never saved.

Each live command carries a saved request ID and expected token ID/status. The
backend locks Queue -> Counter -> Token and checks ownership/state. A stale command
returns 409. Repeating the same request returns its original result, even after the
counter moves on; changing its payload returns 409. The pending command is saved
before sending and retained on ambiguous network/server failures. Retry saved action
reuses that exact command, including after refresh or reauthentication.

`GET /api/v1/staff/workstation` and
`POST /api/v1/staff/counters/{counter_id}/{next|start|pause|resume|missed|absent-again}` are authenticated.
Admin accounts cannot operate counters. The older counter endpoints now also check
assigned STAFF ownership; the live UI uses the retry-safe `/staff/counters` routes.

Migration `d34b1c607a2f` adds a nullable request fingerprint to the existing
idempotency table; it leaves queue order, deadlines and existing records unchanged.
The missing settings import in the existing JWT helpers has been restored.

## Verification

From `../backend`:

```powershell
.\venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

The new PostgreSQL integration tests use actual staff logins and isolated schemas.
They exercise customer registration -> Call Next -> Start Service -> completion,
tracking status, duplicate/concurrent requests, changed payloads, stale actions,
unauthorized counters, admin restrictions, disabled accounts and pause behavior.
`npm run build` verifies the frontend.

For browser testing, run `tests.serve_customer_browser` from the backend. It prints
a reservation suffix and creates an isolated STAFF account:
`browser-staff` / `staff-browser-test`. These credentials exist only in that fixture.
Run the staff frontend on 5176 and customer frontend on 5175, each with
`SEVAFLOW_API_TARGET=http://127.0.0.1:8001`. Open `/staff` on 5176 and, on 5175:

```text
/qr?cat=aadhar&qNo=A024&reservation=browser-check-24-<printed-suffix>#claim=browser-test-only
```

## Remaining work

The approved single-missed-customer sequence is connected. Only an actual service
completion makes that token eligible for recall; Call Next, absence, polling and
refresh do not. Migration `e52a7109bc63` persists eligibility across pauses/restarts.
Existing missed tokens conservatively wait for a new service completion after migration.
No empty-queue timeout or automatic closure is invented: the missed token stays pending.
After two unsuccessful recalls it becomes CLOSED_MISSED, without a completed-service
timestamp/count. Returning customers use Start Service with their original token.

Recall absence commands also carry `expected_recall_attempts`, so a stale first-recall
screen cannot close a second recall. The legacy `/counters/{id}/missed` and
`/counters/{id}/absent-again` aliases require the same command body and return the same
command response; callers without request identity now receive 422.

Multiple-missed scheduling remains undecided. A second initial miss at a counter
with a pending missed token is rejected with 409 without changing either customer.
This deliberate scope limit must be resolved before broad counter deployment.
Admin integration, notifications beyond live tracking, and Pico firmware remain separate.
