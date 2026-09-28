# Customer backend integration

The existing `../../backend` FastAPI application remains the queue authority.
This directory is documentation only; do not start a second customer queue service.

## Implemented contract

- `POST /api/v1/customer/claim`: validate the hardware reservation and claim hash,
  lock Queue then Token, check the unchanged deadline after both locks, allocate
  `scan_sequence` and `sort_key` once, leave status `CLAIMED` (not dispatchable).
- `POST /api/v1/customer/recover`: token ID, claim session ID and recovery hash
  recover the current state without extending the deadline or allocating priority.
- `POST /api/v1/customer/register`: authenticated registration requires name,
  Indian mobile number and tracking hash. Stores details and changes `CLAIMED`
  to `WAITING`, preserving claim order. Identical retries work after dispatch or
  expiry; changed registration data conflicts with HTTP 409.
- `POST /api/v1/customer/reject`: the claim owner may cancel an unregistered token.
  Retries are safe; a registered token cannot be cancelled through this endpoint.
- `GET /api/v1/customer/token/{id}/status`: requires `X-Tracking-Secret` containing
  the browser's tracking credential hash. Returns status, counter, people ahead
  and an approximate wait; no customer name, phone or credentials are returned.

The browser generates a separate random session, recovery credential and tracking
credential for each reservation before first claim. Hashes are credential material:
keep request bodies/headers out of logs. The initial claim response may be lost;
repeating that claim with the saved credentials returns the same priority/deadline.
Claim recovery for a registered token remains valid after its registration deadline.

## QR entry

Keep category and number in the existing entry route, and add the hardware identity
and a secret in the URL fragment:

```text
/qr?cat=aadhar&qNo=A024&reservation=<hardware_reservation_id>#claim=<raw_claim_secret>
```

The kiosk must first receive the hardware reservation acknowledgement. The raw
claim secret must hash to the `claim_secret_hash` stored by the hardware endpoint.
The frontend hashes and saves the credential locally and removes the fragment from
the displayed URL. Refresh uses saved browser credentials. A bare category/number
URL does not authorize claiming a real reservation and shows a rescan message.
Never use the global hardware secret in a customer URL or frontend build.

## Migration and validation

From `q-flow/backend`:

```powershell
.\venv\Scripts\python.exe -B -m alembic upgrade head
.\venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Migration `c81f2a9d401e` only adds nullable name/phone columns. It does not alter
existing deadlines, tokens or queue order. Legacy CLAIMED tokens without a sequence
receive priority on their next authenticated claim, not on registration; historical
scan order is not reconstructed. Existing registered priorities remain unchanged.

Contract tests exercise the actual routes, queue service and PostgreSQL locks in
random disposable schemas (same database by default, or `TEST_DATABASE_URL`). They
cover ordering, dispatch eligibility, concurrent claims and registrations, competing
browsers, lock-delayed expiry, exact deadline, recovery, rejection and live status.

## Limits retained from the existing project

- Reservation TTL is still the backend's existing 15 minutes. A final 3–5 minute
  policy remains a separate decision; no issued deadline is reset by this change.
- Service category mappings remain those in the existing frontend registry. In the
  seeded backend, `svc-aadhaar` is currently labelled KYC; service/hardware mapping
  needs a separate coordinated decision before real kiosk rollout.
- Wait estimates are approximate: waiting customers plus current assignments,
  observed average duration (or service default), divided by active counters.
  Recalls and changing service times can change the estimate. No active counters
  produces an unavailable estimate rather than an invented time.
- The pre-existing general recall scheduler, staff command idempotency and hardware
  retry payload validation are outside this focused claim/registration change.
- No SMS/notification provider is connected.
