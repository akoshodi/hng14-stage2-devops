import redis
import time
import os
import signal
import sys

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379))
)

running = True


def handle_signal(signum, frame):
    global running
    print("Shutting down worker...")
    running = False
    sys.exit(0)


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def process_job(job_id):
    print(f"Processing job {job_id}", flush=True)
    time.sleep(2)
    r.hset(f"job:{job_id}", "status", "completed")
    print(f"Done: {job_id}", flush=True)


while running:
    job = r.brpop("job_queue", timeout=5)
    if job:
        _, job_id = job
        process_job(job_id.decode())
