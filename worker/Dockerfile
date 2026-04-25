# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN set -eux; \
  ok=0; \
  for i in 1 2 3 4 5; do \
    if pip install --no-cache-dir --prefix=/install -r requirements.txt; then ok=1; break; fi; \
    echo "pip install failed, retrying in 5s..."; \
    sleep 5; \
  done; \
  [ "$ok" -eq 1 ]

FROM python:3.11-slim AS runner
WORKDIR /app
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
COPY --from=builder /install /usr/local
COPY worker.py .
USER appuser
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import os, redis; r=redis.Redis(host=os.getenv('REDIS_HOST','redis'),port=int(os.getenv('REDIS_PORT',6379))); r.ping()"
CMD ["python", "worker.py"]
