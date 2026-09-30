# Vercel Services deployment

Pending confirmation of service names, public routes, and absence of bindings.
Set the Vercel project's Root Directory to the Git repository root (the local
`q-flow` directory), and its Framework Preset to **Services**.

## Routing

- `backend` (`backend/app/main.py`, ASGI app `app.main:app`): public `/api/*`.
  Existing FastAPI routes already include `/api/v1`; do not strip that prefix.
- `customer` (`customer/frontend`): public `/qr` and `/qr/*`, including customer
  assets. Existing kiosk QR query parameters and claim fragments are preserved.
  Vite uses `/qr/` as its base and emits `dist/qr/index.html` and
  `dist/qr/assets/*`; Vercel publishes `dist`. Fallbacks match only page routes,
  so JavaScript and CSS requests cannot accidentally receive index HTML.
- `frontend` (`frontend`): remaining paths, including `/`, `/staff`, `/admin`,
  and its assets. Both frontends have SPA fallbacks for page refreshes.
- No service is entirely internal. Backend `/docs`, `/openapi.json`, and `/health`
  are not exposed by this routing table.

## Calls and bindings

Both Vite apps make browser requests to the same-origin `/api/v1` endpoints.
There are no server-side service-to-service requests, so no bindings are declared.
Do not expose a runtime binding through a `VITE_*` variable: Vite replaces those
variables at build time and browser clients cannot use internal service URLs.
Leave `VITE_API_BASE_URL` unset for both apps. The existing `SEVAFLOW_API_TARGET`
localhost fallback is only for standalone Vite development, not production.
PostgreSQL is an external dependency, not a service in this repository.

## Required environment and database preparation

Configure `DATABASE_URL` with a remotely reachable PostgreSQL database using the
`postgresql+asyncpg://` scheme and your provider's TLS settings. Set strong unique
`HARDWARE_SECRET` and `STAFF_JWT_SECRET` values in Vercel. Never commit credentials.
Use separate preview and production databases. Python is pinned to 3.12 to match
the existing backend dependency versions.

Before serving traffic, run `alembic upgrade head` from `backend` against the
deployment database in a controlled migration step. Builds do not run migrations.
The current app seeds an empty database at startup with demo staff passwords;
provision the database once and replace those account passwords before exposing
it. Concurrent cold starts must not be used to provision an empty database.
Connection pool sizing must fit the database connection budget across instances.

## Local validation

From the repository root, run `vercel dev -L` (or `vercel dev` for a linked project).
Check `/qr?cat=aadhar&qNo=A024` using a real kiosk reservation and claim credential,
then registration and authenticated tracking. Check `/staff`, `/admin`, and a
refresh of `/admin/predictions`. Confirm both frontends' JavaScript/CSS requests
return assets, and `/api/v1` requests reach FastAPI rather than SPA HTML.
`preview=1` is a development-only mock; it is intentionally disabled in production.

Build each frontend with `npm ci` and `npm run build` in its own directory.
Both frontend builds passed. Vercel CLI 61.1.0 `vercel dev -L --listen 3100`
detected all three services. HTTP checks returned HTML for `/qr` and
`/admin/predictions`, JavaScript for both apps' entry modules and the customer's
Vite client, and the expected missing-auth-header JSON response from the backend.
The temporary validation server was stopped after the checks.
Database preparation and a real deployment smoke test remain required.
