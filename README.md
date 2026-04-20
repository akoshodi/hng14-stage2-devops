# hng14-stage2-devops

A containerised job-processing system built for **HNG Internship 14 — DevOps Stage 2**.  
Three microservices (Node.js frontend · Python/FastAPI · Python worker) communicate over an isolated Docker network with Redis as the job queue, deployed behind a full CI/CD pipeline.

---

## Architecture

```
Browser
   │
   ▼
┌─────────────┐        ┌───────────────────┐
│  Frontend   │──HTTP──▶      API           │
│  Node/Expr  │        │  Python/FastAPI    │
│  port 3000  │        │  port 8000         │
└─────────────┘        └────────┬──────────┘
                                │  lpush / hset
                                ▼
                       ┌─────────────────┐
                       │     Redis        │
                       │  job_queue key   │
                       │ (internal only)  │
                       └────────┬────────┘
                                │  brpop
                                ▼
                       ┌─────────────────┐
                       │     Worker       │
                       │  Python process  │
                       │  marks completed │
                       └─────────────────┘
```

All inter-service traffic runs on a private Docker bridge network. Redis is never exposed on the host. The frontend is the only service with a public port.

---

## Prerequisites

| Tool | Minimum version |
|------|----------------|
| Docker | 24.0 |
| Docker Compose | 2.20 |
| Git | 2.x |
| curl + jq | any (for smoke tests) |

No cloud account is required. Everything runs on a single machine or GitHub's free-tier runners.

---

## Quick Start (clean machine)

```bash
# 1. Clone your fork
git clone https://github.com/akoshodi/hng14-stage2-devops.git
cd hng14-stage2-devops

# 2. Create local environment file
cp .env.example .env
# Edit .env if you need non-default values (defaults work out of the box)

# 3. Build and start all services
docker compose up -d --build

# 4. Confirm every service is healthy
docker compose ps
```

Expected output — all four services should show `(healthy)`:

```
NAME                        STATUS
stage2-redis-1              Up 30 seconds (healthy)
stage2-api-1                Up 28 seconds (healthy)
stage2-worker-1             Up 28 seconds (healthy)
stage2-frontend-1           Up 25 seconds (healthy)
```

Open `http://localhost:3000` in your browser.

---

## Environment Variables

Copy `.env.example` to `.env` and adjust if needed. Never commit `.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `redis` | Redis service hostname (Docker service name) |
| `REDIS_PORT` | `6379` | Redis port |
| `API_URL` | `http://api:8000` | URL the frontend uses to reach the API |
| `PORT` | `3000` | Port the frontend binds to on the host |

---

## Services & Endpoints

### Frontend — `http://localhost:3000`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Job dashboard UI |
| `GET` | `/health` | Frontend health check |
| `POST` | `/submit` | Submit a new job (proxies to API) |
| `GET` | `/status/:id` | Poll job status (proxies to API) |

### API — internal port 8000

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/` | `{"message": "API is running"}` |
| `GET` | `/health` | `{"status": "healthy"}` |
| `POST` | `/jobs` | `{"job_id": "<uuid>"}` — 201 |
| `GET` | `/jobs/:id` | `{"job_id": "...", "status": "queued|completed"}` |

All API responses use `Content-Type: application/json`.

### Worker — no public port

Continuously pops job IDs from the `job_queue` Redis key, simulates processing (2 s), then updates the job status to `completed`.

---

## Smoke Test

With the stack running:

```bash
# Submit a job
JOB_ID=$(curl -sf -X POST http://localhost:3000/submit | jq -r '.job_id')
echo "Submitted: $JOB_ID"

# Poll status (worker completes in ~2 seconds)
sleep 4
curl -s http://localhost:3000/status/$JOB_ID | jq
# Expected: {"job_id": "...", "status": "completed"}
```

---

## Running Tests Locally

```bash
cd api
pip install -r requirements.txt pytest pytest-cov
pytest tests/ --cov=. --cov-report=term
```

Expected: **6 tests pass**, covering root, health (up + redis-down), job creation, job retrieval, and 404 handling. Redis is fully mocked — no running instance required.

---

## CI/CD Pipeline

The GitHub Actions pipeline runs on every push and PR to `main` in strict stage order. A failure in any stage blocks all subsequent stages.

```
lint → test → build → security → integration → deploy
```

| Stage | What it does |
|-------|-------------|
| **lint** | flake8 (Python), eslint (JavaScript), hadolint (all Dockerfiles) |
| **test** | pytest with mocked Redis, coverage report uploaded as artifact |
| **build** | Builds all 3 images, tags with `git-SHA` + `latest`, pushes to in-job local registry |
| **security** | Trivy scans all 3 images; pipeline fails on any `CRITICAL` finding; SARIF uploaded as artifact |
| **integration** | Boots full stack inside the runner, submits a job via the frontend, polls until `completed`, tears down cleanly |
| **deploy** | Runs on `main` push only — rolling update over SSH; new container must pass health check within 60 s or old container is kept running |

### Required GitHub Secrets

Add these under **Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `SERVER_HOST` | Your VPS hostname or IP |
| `SSH_PRIVATE_KEY` | Contents of `~/.ssh/id_ed25519` for the `hngdevops` user |

---

## Stopping the Stack

```bash
docker compose down          # stop containers, keep volumes
docker compose down -v       # stop containers and remove volumes (clean slate)
```

---

## Project Structure

```
hng14-stage2-devops/
├── api/
│   ├── main.py               # FastAPI application
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
│       └── test_main.py      # 6 unit tests (Redis mocked)
├── worker/
│   ├── worker.py             # Job processor
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app.js                # Express server
│   ├── package.json
│   ├── .eslintrc.json
│   ├── Dockerfile
│   └── views/
│       └── index.html        # Job dashboard UI
├── .github/
│   └── workflows/
│       └── pipeline.yml      # Full CI/CD pipeline
├── docker-compose.yml
├── .env.example
├── FIXES.md                  # All bugs found and fixed
└── README.md
```

---

## Bugs Fixed

All 12 bugs found in the original source are documented with exact file, line number, problem description, and fix in [`FIXES.md`](./FIXES.md).

Key fixes at a glance:

- Redis `host="localhost"` → `REDIS_HOST` env var in both API and worker
- Missing `/health` and `/` endpoints on the API
- Job-not-found returning `200` instead of `404`
- Frontend API URL hardcoded to `localhost:8000`
- `signal` imported but never wired in the worker
- Queue key inconsistency standardised to `job_queue`

---

## License

MIT
