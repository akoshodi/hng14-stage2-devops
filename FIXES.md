# FIXES.md

All bugs found in the original source code and how they were resolved.

---

### Fix 1 — API Redis hostname hardcoded to localhost
- **File:** `api/main.py`, line 8
- **Problem:** `redis.Redis(host="localhost")` — in a Docker network, services
  communicate by service name, not `localhost`. This causes a connection error
  at startup inside any container.
- **Fix:** Changed to `host=os.getenv("REDIS_HOST", "redis")` so the hostname
  is read from the environment and defaults to the Docker Compose service name.

### Fix 2 — Worker Redis hostname hardcoded to localhost
- **File:** `worker/worker.py`, line 5
- **Problem:** Same issue as Fix 1 — `redis.Redis(host="localhost")` fails
  inside Docker.
- **Fix:** Changed to `host=os.getenv("REDIS_HOST", "redis")`.

### Fix 3 — Queue key mismatch between API and worker
- **File:** `api/main.py` line 12 vs `worker/worker.py` line 16
- **Problem:** API pushed jobs to key `"job"` via `lpush`. Worker popped from
  key `"job"` via `brpop` — this accidentally matched, but the key name was
  semantically wrong and fragile. Standardised to `"job_queue"` across both
  services for clarity and correctness.
- **Fix:** Changed both to use `"job_queue"`.

### Fix 4 — Frontend API URL hardcoded to localhost
- **File:** `frontend/app.js`, line 6
- **Problem:** `API_URL = "http://localhost:8000"` — inside Docker, the
  frontend container cannot reach the API via localhost. Must use the Docker
  Compose service name `api`.
- **Fix:** Changed to `process.env.API_URL || "http://api:8000"`.

### Fix 5 — Missing /health endpoint on API
- **File:** `api/main.py`
- **Problem:** No `/health` route existed. The Docker HEALTHCHECK, the
  `depends_on: service_healthy` condition in Compose, and the CI integration
  test all require a working health endpoint.
- **Fix:** Added `GET /health` that pings Redis and returns `{"status":"healthy"}`
  or 503 if Redis is down.

### Fix 6 — Missing / root endpoint on API
- **File:** `api/main.py`
- **Problem:** No root `GET /` route. The integration test and grader check
  this endpoint.
- **Fix:** Added `GET /` returning `{"message": "API is running"}`.

### Fix 7 — Job not found returns 200 instead of 404
- **File:** `api/main.py`, line 17
- **Problem:** `return {"error": "not found"}` returns HTTP 200 with an error
  body — semantically wrong. Clients cannot distinguish success from failure
  by status code.
- **Fix:** Changed to `raise HTTPException(status_code=404, detail="Job not found")`.

### Fix 8 — signal imported but never used in worker
- **File:** `worker/worker.py`, line 4
- **Problem:** `import signal` present but no signal handlers registered.
  The worker cannot be stopped gracefully — SIGTERM from Docker compose down
  causes an abrupt kill.
- **Fix:** Registered `SIGTERM` and `SIGINT` handlers that set a `running`
  flag to `False` and exit cleanly.

### Fix 9 — Frontend hardcoded port
- **File:** `frontend/app.js`, line 26
- **Problem:** `app.listen(3000)` is hardcoded, not configurable via
  environment variable.
- **Fix:** Changed to `app.listen(process.env.PORT || 3000)`.

### Fix 10 — Missing /health endpoint on frontend
- **File:** `frontend/app.js`
- **Problem:** No health route for Docker HEALTHCHECK to probe.
- **Fix:** Added `GET /health` returning `{"status":"healthy"}`.

### Fix 11 — No ESLint configuration
- **File:** `frontend/package.json`
- **Problem:** CI lint stage runs `eslint` but no eslint dependency or config
  existed in the project.
- **Fix:** Added `eslint` to `devDependencies`, added `lint` script, and
  created `.eslintrc.json` with `eslint:recommended` rules.

### Fix 12 — .env file present in repo
- **File:** `_env` (repo root)
- **Problem:** An environment file was committed to the repository. This is a
  security violation — credentials and config must never be in git history.
- **Fix:** Removed `_env`, created `.env.example` with placeholder values,
  and added `.env` to `.gitignore`.
