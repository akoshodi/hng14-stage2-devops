from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import redis
import uuid
import os

app = FastAPI()

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379))
)


@app.get("/")
def root():
    return JSONResponse(content={"message": "API is running"})


@app.get("/health")
def health():
    try:
        r.ping()
        return JSONResponse(content={"status": "healthy"})
    except Exception:
        raise HTTPException(status_code=503, detail="Redis unavailable")


@app.post("/jobs", status_code=201)
def create_job():
    job_id = str(uuid.uuid4())
    r.lpush("job_queue", job_id)
    r.hset(f"job:{job_id}", "status", "queued")
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    status = r.hget(f"job:{job_id}", "status")
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": status.decode()}
