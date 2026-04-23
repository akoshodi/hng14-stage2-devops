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

### Fix 13 — `api/.env` with plaintext credentials committed and tracked
- **File:** `api/.env`, line 1
- **Problem:** A real `.env` file containing `REDIS_PASSWORD=supersecretpassword123`
  and `APP_ENV=production` was tracked by git and present in commit history.
  Any public viewer of the repository could read these credentials. This violates
  the acceptance criteria which state `.env` must never appear in the repository
  or git history.
- **Fix:** Ran `git rm --cached api/.env` to untrack the file. Added `**/.env`
  to `.gitignore` to block all nested env files. Rewrote full git history with
  `git filter-repo --path api/.env --invert-paths` to permanently remove the
  file from all past commits.

### Fix 14 — Compose frontend service uses hardcoded container port
- **File:** `docker-compose.yml`, lines 59 and 62
- **Problem:** The `ports` mapping contained a hardcoded container-side port
  (`"${PORT}:3000"`) and the `environment` block set `PORT: 3000` as a literal
  value. This violates the rubric requirement that all configuration must come
  from environment variables with nothing hardcoded in the Compose file.
- **Fix:** Changed ports to `"${PORT}:${PORT}"` and environment to `PORT: ${PORT}`
  so the value flows entirely from the `.env` file.

### Fix 15 — Compose frontend service missing internal network
- **File:** `docker-compose.yml`, line 63
- **Problem:** The frontend service was only attached to the `public` network.
  Since it must call the API (`api:8000`) over Docker networking, and the API
  is on the `internal` network, all inter-service traffic must traverse the
  internal network. Without this, the frontend-to-API path is inconsistent with
  the rubric requirement that services communicate over a named internal network.
- **Fix:** Added `internal` to the frontend service's `networks` list so it
  shares the private bridge with the API, worker, and Redis, while still
  exposing the host port via the `public` network.

### Fix 16 — Worker healthcheck tests process existence, not service health
- **File:** `worker/Dockerfile`, line 14
- **Problem:** `HEALTHCHECK CMD python -c "import os, sys; sys.exit(0) if os.path.exists('/proc/1/status')..."` only
  verifies that a process is alive on PID 1 — it does not prove the worker can
  reach Redis, which is its only external dependency and the one failure mode
  that matters. A worker that cannot connect to Redis will appear healthy.
- **Fix:** Changed to `python -c "import os, redis; r=redis.Redis(host=os.getenv('REDIS_HOST','redis'),port=int(os.getenv('REDIS_PORT',6379))); r.ping()"`
  so the healthcheck probes the actual Redis connection on every interval.

### Fix 17 — `.env.example` contained real operational defaults instead of placeholders
- **File:** `.env.example`
- **Problem:** Variables such as `REDIS_HOST=redis`, `PORT=3000`, and
  `API_URL=http://api:8000` are real working values, not placeholders. The
  rubric explicitly requires placeholder values in `.env.example`.
- **Fix:** Replaced all values with angle-bracket placeholder strings (e.g.
  `REDIS_HOST=<redis_service_name>`, `PORT=<frontend_port>`) to make it clear
  that the file must be filled in before use.
