# Operations

Local PostgreSQL is defined in the root `docker-compose.yml`. Use an existing PostgreSQL service in production and set `DATABASE_URL` through your deployment provider's secret store. The checked-in example values are local-only defaults.

Deploy the FastAPI service from the repository root after installing the Python package. Run `alembic upgrade head` once as a release step, then start `uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000` behind your platform's TLS proxy. `/health` checks database connectivity; configure a platform readiness probe. Keep database access private and back it up.

Build the web app with `npm ci && npm run build` in `apps/web`, then run `npm start`. Set `NEXT_PUBLIC_API_URL` before the build to the HTTPS API origin reachable by users' browsers. Set `CORS_ORIGINS` on the API to the deployed frontend origin. The frontend does not proxy API requests and does not need database access.

Collectors use the same database through `python -m collectors.sync_all`. Sources and cadence are documented in [ingestion operations](../docs/ingestion.md). A foreground Python scheduler and a gated GitHub Actions schedule are included. The workflow requires `INGESTION_DATABASE_URL` as a repository secret and `INGESTION_ENABLED=true` as a variable, after database migration and seeding.

Production mutation endpoints remain blocked. Authentication and authorization are required before enabling production administration. Application tracking remains browser-local. Retain backups, monitor source failure/interrupted histories and schedule recency, and plan history retention as volume grows. Scheduled ingestion is configured but no cloud deployment or production database was provisioned in the local build.
