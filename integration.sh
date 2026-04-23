#!/bin/bash
set -e

echo "Starting integration test..."

# Bring up the stack
docker compose up -d --build

# Wait for all services healthy with timeout
echo "Waiting for services to be healthy..."
TIMEOUT=120
ELAPSED=0

until docker compose ps | grep -v "starting" | grep -qE "(healthy)"; do
  if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "Timeout: services did not become healthy within ${TIMEOUT}s"
    docker compose down -v
    exit 1
  fi
  echo "Still waiting... (${ELAPSED}s elapsed)"
  sleep 5
  ELAPSED=$((ELAPSED + 5))
done

echo "All services healthy. Running integration test..."

# Submit a job through the frontend
JOB_ID=$(curl -sf -X POST http://localhost:3000/submit | jq -r '.job_id')

if [ -z "$JOB_ID" ]; then
  echo "Failed to submit job"
  docker compose down -v
  exit 1
fi

echo "Job submitted: $JOB_ID"

# Poll for completion with timeout
POLL_TIMEOUT=60
POLL_ELAPSED=0

while true; do
  if [ $POLL_ELAPSED -ge $POLL_TIMEOUT ]; then
    echo "Timeout: job did not complete within ${POLL_TIMEOUT}s"
    docker compose down -v
    exit 1
  fi

  STATUS=$(curl -sf http://localhost:3000/status/$JOB_ID | jq -r '.status')
  echo "Job status: $STATUS (${POLL_ELAPSED}s elapsed)"

  if [ "$STATUS" = "completed" ]; then
    echo "Integration test PASSED"
    docker compose down -v
    exit 0
  fi

  sleep 3
  POLL_ELAPSED=$((POLL_ELAPSED + 3))
done