# Live admin monitoring

`/admin`, `/admin/queues`, and `/admin/counters` use the authenticated, read-only
`GET /api/v1/admin/monitor` endpoint. Start the core API and staff frontend as described
in the root README, then sign in with an active ADMIN account. Staff accounts are
rejected by the API. Admin sessions are saved separately from staff sessions in
sessionStorage; logout removes the admin session. No passwords are stored.

The existing admin shell, sidebar, palette, metric cards and counter cards are reused.
The original screens remain at `/admin/demo/overview`, `/admin/demo/queues`, and
`/admin/demo/counters`. The old Analytics screen is at `/admin/demo/analytics`.
Predictions now uses a provisional recorded-day baseline; its former demo remains at `/admin/demo/predictions`. Live Analytics and Predictions are documented below.

The monitor polls every five seconds and retains the last snapshot with a reconnecting
notice on errors. Authentication failure clears displayed data and returns to login.
The endpoint returns counts, token numbers and assigned staff names, never customer
names, phone numbers, password hashes or token credentials. No admin mutation route
is introduced.

Daily registrations and completions use token timestamps and Asia/Kolkata calendar
boundaries. They are not derived from the counter's cumulative served_today field.
Counter cards explicitly label that field as recorded completions. CALLED and SERVING
are counted separately; RESERVED and CLAIMED do not enter waiting counts. Upcoming
lists contain at most three registered WAITING tokens per queue in scan order.

Waiting estimates approximate the end of each waiting line using active-counter
average service durations (or the service default). They are not measured historical
waits. No active counter returns an unavailable estimate. Multiple queries comprise
a monitoring response, so concurrent queue changes can briefly produce differences
between related counts; the next poll refreshes them. Monitoring takes no queue locks.

Validation: `python -B -m pytest -q -p no:cacheprovider` from backend (41 tests passed)
and `npm run build` from frontend. The isolated browser fixture also seeds
`browser-admin` / `admin-browser-test` for local UI checks on port 8001 only.

## Live Analytics

`/admin/analytics` now uses ADMIN-only `GET /api/v1/admin/analytics?date=YYYY-MM-DD`.
Omit the date for today in Asia/Kolkata. Future/invalid dates are rejected. The page
refreshes every 15 seconds, supports historical dates, displays stale/error states,
and preserves the original sample page at `/admin/demo/analytics`.

Registrations are grouped by registration timestamp. Completions and measured
averages are grouped by completion timestamp (including registrations on older days).
Wait = registration to actual service start, including recall delay. Service duration
= start to completion, including pauses. Only COMPLETED tokens enter completion
counts. Invalid/missing duration samples are excluded; sample counts are displayed.
Zero duration is valid; no samples returns null and displays Unavailable. Hourly
buckets span the entire local calendar day, with an exclusive next-midnight boundary.
The page shows registrations by hour and a detailed accessible hourly table. Empty
reports never fabricate a peak hour. Utilization remains unavailable because complete
counter opening/pause history is not stored. Predictions uses the provisional baseline documented below.

## Predictions baseline

`/admin/predictions` uses ADMIN-only `GET /api/v1/admin/predictions`, refreshing every
minute. Original sample UI remains at `/admin/demo/predictions`. This is a provisional
planning baseline, not trained ML or a validated forecasting model.

The target is tomorrow in Asia/Kolkata. Input is aggregated registrations from the
previous 28 completed calendar days, excluding today. At least seven days with recorded
registrations are required, and the latest activity must be no more than seven days old.
The estimate is mean registrations per recorded day, with the same denominator for
hourly counts. A service requires records on at least three of those days to display
its own estimate. Thresholds are implementation defaults in services/predictions.py,
not approved queue/admission policy; forecasts never change queue behavior.

Days without registrations are excluded rather than assumed open with zero demand.
This conditions the baseline on recorded activity and can bias it upward. Closure,
collection coverage, weekday/holiday/seasonal effects are not modeled. Historical
min/max is not a confidence interval. New services may lack estimates, and rounded
hourly/service totals may not equal the centre estimate. Future waiting time and
queue pressure remain unavailable without planned capacity and validated arrival
modeling. Missing history never falls back to mock data.

Verification: 45 backend tests and frontend build passed. Tests cover authorization,
real PostgreSQL aggregation, local midnight, excluding current-day/out-of-window data,
recorded-day means, sparse history, and stale history.

## Mock Predictions preview

Open `/admin/predictions?preview=1` or choose **View mock data** on Predictions.
The preview displays 144 synthetic expected registrations, a 24-hour demand chart,
and four sample services. A persistent mock label and **Use real data** link distinguish
it from the backend forecast. No customer records are inserted and the forecast API
is not polled while the mock view is selected. Admin authentication is still required.
