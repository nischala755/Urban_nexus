# Deploy the demo on Render

[Deploy UrbanNexus](https://render.com/deploy?repo=https://github.com/nischala755/Urban_nexus)

1. Sign in to Render and open the deployment link above (or choose **New > Blueprint**
   and connect `nischala755/Urban_nexus`, branch `main`).
2. Review the two resources from `render.yaml`: `urban-nexus` Docker web service
   and `urban-nexus-db` PostgreSQL 16 database, both **Free**, in Singapore.
3. Deploy the Blueprint. Render builds React inside Docker, starts FastAPI,
   and supplies the internal database URL. No separate frontend service,
   build command, start command, or manually copied database secret is needed.
4. Wait for the web service to become **Live**. Open its assigned `onrender.com`
   URL, then `/health`; the JSON should show `status: ok`.
5. In the UI, run the waste stress scenario, evaluate plans, open a passport,
   approve it, and verify the outcome. Set traffic allowance to zero and
   reevaluate to exercise the no-safe-action result.

The existing Docker process listens on `0.0.0.0:8000`; the Blueprint sets Render's
`PORT` to the same value. The health endpoint reads the database, so readiness
requires both the application and persistence to work. Database tables and the
seeded synthetic ward are initialized automatically at startup.

This is a public synthetic demo with no login or operator identity verification.
Visitors share one ward and can reset it or approve simulated actions. Do not
upload private municipal information. MATLAB and SUMO are not installed in the
web image; the UI uses the documented Python simulation models.

## Free-plan limits and troubleshooting

- Free web services sleep after 15 minutes without incoming traffic; the first
  visit afterward can take around a minute to start.
- Free PostgreSQL expires after 30 days. Upgrade the database before expiry if
  the demo and its audit history must remain available. Free web filesystems are
  ephemeral; do not replace the database URL with SQLite for durable storage.
- A workspace can have only one free PostgreSQL database. If yours already has
  one, do not delete it to make room: use a suitable existing database or choose
  a paid database explicitly in Render.
- If deployment fails, inspect the web service **Logs** and database status.
  Confirm `DATABASE_URL` is the Blueprint-managed internal connection string.
  Never paste the connection string into an issue or chat.
- The exact URL is assigned by Render; `urban-nexus.onrender.com` is not guaranteed.

References: [Blueprint specification](https://render.com/docs/blueprint-spec),
[free-plan limits](https://render.com/docs/free).

Local Docker/PostgreSQL verification does not establish that a Render deployment
is live. Verify the assigned URL after creating these resources in your account.
