# SevaFlow customer frontend

Preserves welcome/service information and Accept/Reject, adds real name/mobile
registration and authenticated refresh recovery. Uses the approved light sky-blue
palette, aligned tracking metrics, and persistent English/Hindi toggle.

## Run

Start the core API in `../../backend` (apply its migrations first), then here:

```powershell
npm install
npm run dev
```

Vite serves port 5174 and proxies `/api` to `http://127.0.0.1:8000`.
For deployment, serve `/api/v1` on the same origin or set `VITE_API_BASE_URL` at build
time and configure allowed origins in the backend. Use HTTPS for mobile access:
credential hashing needs a secure browser context (localhost also works).

Real entry:

```text
/qr?cat=aadhar&qNo=A024&reservation=<hardware_reservation_id>#claim=<raw_claim_secret>
```

See `../backend/README.md` for the complete contract. The category/number-only URL
is insufficient to claim a real token. The frontend never invents a reservation.

Credentials and the accepted-screen choice are saved per reservation in localStorage.
Unsubmitted form drafts are saved in sessionStorage and removed on successful
registration. Do not clear browser storage while using an active token. The frontend
uses the server deadline and clock offset; backend admission remains authoritative.
Tracking polls every four seconds and labels stale data on connection failure.

The original Stage 1 mock is retained at `/qr?cat=aadhar&qNo=A024&preview=1` only in
development. Its old placeholder screens and developer reset controls are not part
of the live flow. No demo reservation is created when the production app opens.

## Validate

```powershell
npm run build
```

For manual end-to-end checks without touching real queues, run from `../../backend`:

```powershell
.\venv\Scripts\python.exe -B -m tests.serve_customer_browser
```

Then start a separate frontend here:

```powershell
$env:SEVAFLOW_API_TARGET='http://127.0.0.1:8001'
npm run dev -- --host 127.0.0.1 --port 5175 --strictPort
```

Use `/qr?cat=aadhar&qNo=A024&reservation=browser-check-24-<printed-suffix>#claim=browser-test-only`
on port 5175. The fixture prints the unique suffix. A025 / browser-check-25-<printed-suffix> is available for rejection testing. This
fixture uses a disposable schema and test-only secrets. Stop it with Ctrl+C to
remove its test schema. Use a fresh browser context for each fixture run.

If Windows interrupts the fixture before its shutdown handler runs, list leftover
test schemas with `python -B -m tests.cleanup_browser_fixture` from the backend.
Pass the exact printed schema name to that command to remove only that disposable
fixture after stopping its server. The cleanup utility refuses non-fixture names.
