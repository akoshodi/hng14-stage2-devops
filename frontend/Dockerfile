# syntax=docker/dockerfile:1
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN set -eux; \
  ok=0; \
  for i in 1 2 3 4 5; do \
    if npm ci; then ok=1; break; fi; \
    echo "npm ci failed, retrying in 5s..."; \
    sleep 5; \
  done; \
  [ "$ok" -eq 1 ]
COPY . .

FROM node:20-alpine AS runner
WORKDIR /app
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./
COPY app.js .
COPY views ./views
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "app.js"]
