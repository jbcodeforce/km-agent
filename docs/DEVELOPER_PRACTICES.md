# Developer practices

## Local PostgreSQL (Docker Compose only)

The database service in `compose.yaml` is named `agent-db` (image `agnohq/pgvector:18`). To start **only** that container from the repository root:

```bash
docker compose up -d agent-db
```

Compose reads `.env` when present. Postgres is published on the host as **`POSTGRES_PUBLISH_PORT` → `5432` inside the container** (default host port `5432`). See `compose.yaml` under `agent-db.ports`. This is separate from **`DB_PORT`**, which `kma.db.build_db_url()` uses when your app or pytest connects to the database. Keep **`DB_PORT` equal to `POSTGRES_PUBLISH_PORT`** when you run tests on the host against the Compose database.

If port `5432` is already in use on your machine, set for example `POSTGRES_PUBLISH_PORT=5433` in `.env` and set **`DB_HOST=localhost`** and **`DB_PORT=5433`** for local runs and unit tests.

To stop just that service:

```bash
docker compose stop agent-db
```

### Where data lives

Postgres uses the Compose **named volume** declared as `km-agent-postgres` in `compose.yaml` (mounted at `/var/lib/postgresql` in the container). Docker registers it under a **project-scoped name**, usually `<compose_project_name>_km-agent-postgres`. The default project name is the directory name (for example `km-agent`), so the volume often appears as **`km-agent_km-agent-postgres`**. Confirm with:

```bash
docker volume ls
docker volume inspect "$(docker volume ls -q --filter name=km-agent-postgres)"
```

**On disk:** With **Docker Engine on Linux**, `Mountpoint` from `docker volume inspect` is a real host path (typically under `/var/lib/docker/volumes/.../_data`). With **Docker Desktop** (macOS or Windows), that path lives **inside Docker’s Linux VM**, not next to your project folder; you normally access the data only through Postgres or by running a one-off container that mounts the same volume (for example `docker run --rm -v km-agent_km-agent-postgres:/v alpine ls /v` — adjust the volume name to match `docker volume ls`).

### Keeping data between sessions

Named volumes **persist until you remove them explicitly**. They are **not** tied to a running container.

| Action | Postgres data |
|--------|----------------|
| `docker compose stop agent-db` or `docker compose stop` | **Kept** |
| `docker compose start agent-db` | Reattaches the **same** volume |
| `docker compose down` | Containers removed; volume **still kept** |
| `docker compose up -d agent-db` after `down` | **Same** volume is reused |
| `docker compose down -v` | Volume **deleted** (fresh empty DB on next `up`) |
| `docker volume rm <volume_name>` | Volume **deleted** |

To wipe the database and start clean:

```bash
docker compose down -v
docker compose up -d agent-db
```
## Unit tests

Install dependencies (once per clone or after dependency changes):

```bash
uv sync
```

Run all tests under `tests/`:

```bash
uv run pytest
```

Run only unit tests under `tests/ut/`:

```bash
uv run pytest tests/ut -v
```

Tests that talk to PostgreSQL (for example `tests/ut/test_db_public_schema.py`) use the same URL as `kma.db`. Run them on the **host** with **`DB_HOST=localhost`** (or `127.0.0.1`) — not `agent-db`, which only resolves inside the Compose network. Set **`DB_PORT`** to the same value as **`POSTGRES_PUBLISH_PORT`** from `compose.yaml` (default `5432`). Confirm the mapping with `docker compose ps` or `docker port agent-db`. If the server is not reachable, those tests **skip** instead of failing.
