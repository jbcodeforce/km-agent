# syntax=docker/dockerfile:1

# --- Vue + Vite static assets (same paths as dev: browser calls /agent-os/* on this origin)
FROM node:22-bookworm-slim AS frontend
WORKDIR /ui
COPY src/frontend/package.json src/frontend/package-lock.json ./
RUN npm ci
COPY src/frontend/ ./
RUN npm run build

# --- AgentOS (FastAPI) + built UI
FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        libmagic1 \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONPATH=/app/src \
    KMA_SERVE_UI=1 \
    PATH=/app/.venv/bin:$PATH

COPY pyproject.toml uv.lock README.md /app/
RUN uv sync --frozen --no-install-project

COPY src /app/src
COPY --from=frontend /ui/dist /app/src/frontend/dist
RUN uv sync --frozen

EXPOSE 8000
# Use the venv interpreter explicitly (avoids broken shebangs on some setups).
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
