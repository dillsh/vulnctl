# vulnctl
CLI tool for triggering CVE collection and querying stored vulnerabilities.
The part of the bunch of CVE services, see [cve-services](https://github.com/dillsh/cve-project).


## Getting Started

### Docker (recommended)

vulnctl is built as part of the Docker Compose stack in [cve-project](https://github.com/dillsh/cve-project) under the `cli` profile. Run commands via `docker-compose run`:

```bash
# from cve-project/
docker-compose run --rm vulnctl collect --since 2024-01-01
docker-compose run --rm vulnctl cve list --since 2024-01-01
docker-compose run --rm vulnctl --help
```

The `--rm` flag removes the container after each run, since vulnctl is a one-shot CLI tool.

### Local Development

#### 0. Configuration

All settings are loaded from environment variables (or a `.env` file).

| Variable | Default | Description |
|---|---|---|
| `TEMPORAL_HOST` | `localhost` | Temporal server host |
| `TEMPORAL_PORT` | `7233` | Temporal server port |
| `COLLECTOR_GRPC_HOST` | `localhost` | cve-collector gRPC host |
| `COLLECTOR_GRPC_PORT` | `50052` | cve-collector gRPC port |
| `CVE_CORE_GRPC_HOST` | `localhost` | cve-core gRPC host |
| `CVE_CORE_GRPC_PORT` | `50051` | cve-core gRPC port |
| `COLLECTOR_TASK_QUEUE` | `cve-collector` | Temporal task queue of the cve-collector worker |
| `VULNCTL_API_KEY` | `""` | API key sent to gRPC services — use admin key for full access, reader key for read-only |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENVIRONMENT` | `development` | `development` / `staging` / `production` / `test` |

#### 1. Install uv (Python package manager)
```
# macOS / Linux
curl -Ls https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### 2. Install dependencies
```bash
uv sync --all-extras
```

#### 3. Run a command
```bash
uv run python -m src.cli.main --help
```

---

## Running Tests

```bash
uv run pytest tests/
```

---

## Access Levels

vulnctl commands require an API key (`VULNCTL_API_KEY`) matching the role:

| Role | Key | Commands available |
|------|-----|--------------------|
| **admin** | `API_KEY_ADMIN` from cve-project | All commands |

**Admin** — runs on the server (SSH) or locally with internal access:
```bash
export VULNCTL_API_KEY=<admin-key>
export CVE_CORE_GRPC_HOST=localhost
vulnctl collect --since 2024-01-01
vulnctl schedule create --cron "0 6 * * *"
vulnctl cve list --since 2024-01-01
```

**Reader** — runs from any machine with access to the public cve-core port (50051):
```bash
export CVE_CORE_GRPC_HOST=<server-ip>
vulnctl cve list --since 2024-01-01   # ✓ works
vulnctl collect ...                    # ✗ connection refused (port not public)
```

Without a key or with a wrong key: `UNAUTHENTICATED`.

---

## Commands

### `collect` — Trigger a one-off CVE collection _(admin only)_

```bash
vulnctl collect --since 2024-01-01
vulnctl collect --since 2024-01-01 --until 2024-06-30
```

| Option | Required | Description |
|---|---|---|
| `--since` | Yes | Start date (ISO 8601), e.g. `2024-01-01` |
| `--until` | No | End date (ISO 8601); defaults to open-ended |

---

### `schedule` — Manage recurring collection schedules _(admin only)_

#### `schedule create`
```bash
vulnctl schedule create --schedule-id daily-cve-collection --cron "0 6 * * *" --lookback-days 1
```

| Option | Default | Description |
|---|---|---|
| `--schedule-id` | `daily-cve-collection` | Unique schedule ID in Temporal |
| `--cron` | `0 6 * * *` | Cron expression (UTC) |
| `--lookback-days` | `1` | Days to look back when building the collection window |

#### `schedule list`
```bash
vulnctl schedule list
```
Lists all active schedules with their ID, cron expression, and next run time.

#### `schedule delete`
```bash
vulnctl schedule delete daily-cve-collection
```

| Argument | Description |
|---|---|
| `SCHEDULE_ID` | ID of the schedule to delete |

---

### `cve` — Query CVEs from cve-core _(admin + reader)_

#### `cve list`
```bash
vulnctl cve list --since 2024-01-01
vulnctl cve list --since 2024-01-01 --until 2024-06-30
```

| Option | Required | Description |
|---|---|---|
| `--since` | Yes | Start date (ISO 8601) — lower bound on `date_updated` |
| `--until` | No | End date (ISO 8601) — upper bound on `date_updated` |

Outputs a table: CVE ID, Status, Title, Affected (list of (vendor, product)), Date Updated.

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.12 |
| CLI framework | `typer` |
| Console output | `rich` |
| gRPC client | `grpcio` >= 1.78.0 |
| Workflow orchestration | `temporalio` ~= 1.18.0 |
| Config | `pydantic-settings` |
| Serialization | `protobuf` ~6.33 |
| Linting | `ruff` |
| Type checking | `mypy` |
| Testing | `pytest`, `pytest-asyncio` |

---
