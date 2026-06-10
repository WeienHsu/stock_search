# ── Stage 1: build the React frontend ──
FROM node:22-slim AS web-build

WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ .
RUN npm run build

# ── Stage 2: Python API + scheduler worker runtime ──
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=web-build /web/dist ./web/dist

# Shared runtime volume: app and worker see the same SQLite DBs and caches.
RUN mkdir -p data

EXPOSE 8700

HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:8700/api/health || exit 1

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8700"]
