# vulnctl

CLI tool for monitoring CVE vulnerabilities.

In progress, please wait...

```bash
# See CVEs from the last 24 hours
./vulnctl cve last

# See CVEs from the last 3 days
./vulnctl cve last --days 3
```

No account, no API key, no Docker required.

---

## Install

Standalone binaries are published to [GitHub Releases](https://github.com/dillsh/vulnctl/releases) on every tag.

| Platform | File |
|---|---|
| macOS Apple Silicon | `vulnctl-darwin-arm64` |
| Linux x86_64 | `vulnctl-linux-amd64` |

```bash
# macOS
curl -L https://github.com/dillsh/vulnctl/releases/latest/download/vulnctl-darwin-arm64 -o vulnctl
chmod +x vulnctl

# Linux
curl -L https://github.com/dillsh/vulnctl/releases/latest/download/vulnctl-linux-amd64 -o vulnctl
chmod +x vulnctl
```

---

## Commands

### `cve last` — recent vulnerabilities

```bash
vulnctl cve last                          # last 24 hours (default)
vulnctl cve last --days 3                 # last 3 days
vulnctl cve last -d 2 -o report.json      # save to JSON
vulnctl cve last -d 1 -o report.csv       # save to CSV
```

| Option | Default | Description |
|---|---|---|
| `--days` / `-d` | `1` | Days to look back: `1`, `2`, or `3` |
| `--output` / `-o` | — | Save to file instead of printing. Format inferred from extension: `.json` or `.csv` |

Without `--output`: prints a table with CVE ID, Status, Title, Affected products, Date Updated.

With `--output`:
- **`.json`** — array of CVE objects with all fields, including nested `affected` list
- **`.csv`** — one row per CVE; `affected` column is a flattened `vendor/product` string

Each entry in `affected` contains:

| Field | Description |
|---|---|
| `vendor` | Vendor name |
| `product` | Product name |
| `version` | Affected version string |
| `cpe` | List of CPE 2.3 identifiers |

---

## Configuration

The binary connects to a hosted cve-core instance by default — no configuration needed.

To point at a custom instance, set environment variables (or a `.env` file):

| Variable | Default | Description |
|---|---|---|
| `CVE_CORE_HTTP_HOST` | _(baked in at build time)_ | cve-core REST host |
| `CVE_CORE_HTTP_PORT` | `8080` | cve-core REST port |

---

---

## Dev

### Admin commands

Admin commands require an API key and access to internal ports.

#### `cve list` — query by date range

```bash
vulnctl cve list --since 2024-01-01
vulnctl cve list --since 2024-01-01 --until 2024-06-30
```

| Option | Required | Description |
|---|---|---|
| `--since` | Yes | Start date (ISO 8601) |
| `--until` | No | End date (ISO 8601) |

#### `cve collect` — trigger a one-off CVE collection

```bash
vulnctl cve collect --since 2024-01-01
vulnctl cve collect --since 2024-01-01 --until 2024-06-30
```

#### `cve schedule` — create a recurring CVE collection schedule

```bash
vulnctl cve schedule $SCHEDULE_NAME                    # default --cron "0 6 * * *"
vulnctl cve schedule $SCHEDULE_NAME --cron "0 10 * * *"
```

| Argument / Option | Required | Description |
|---|---|---|
| `SCHEDULE_NAME` | Yes | Unique schedule name in Temporal |
| `--cron` | No | Cron expression (UTC). Default: `0 6 * * *` |

Each scheduled run resolves the collection window automatically via the checkpoint stored in cve-core.

#### `cpe sync` — trigger a one-off NVD CPE dictionary sync

```bash
vulnctl cpe sync
```

#### `cpe schedule` — create a recurring CPE dictionary sync schedule

```bash
vulnctl cpe schedule $SCHEDULE_NAME                    # default --cron "0 3 * * *"
vulnctl cpe schedule $SCHEDULE_NAME --cron "0 5 * * *"
```

| Argument / Option | Required | Description |
|---|---|---|
| `SCHEDULE_NAME` | Yes | Unique schedule name in Temporal |
| `--cron` | No | Cron expression (UTC). Default: `0 3 * * *` |

#### `schedule list` / `schedule delete` — manage all schedules

```bash
vulnctl schedule list
vulnctl schedule delete $SCHEDULE_NAME
```

### Running locally

#### 1. Install uv

```bash
# macOS / Linux
curl -Ls https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### 2. Install dependencies

```bash
uv sync --all-extras
```

#### 3. Configure

All settings are loaded from environment variables (or a `.env` file).

| Variable | Default | Description |
|---|---|---|
| `CVE_CORE_HTTP_HOST` | `localhost` | cve-core REST host |
| `CVE_CORE_HTTP_PORT` | `8080` | cve-core REST port |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`) |
| `ENVIRONMENT` | `development` | `development` / `staging` / `production` / `test` |

#### 4. Run

```bash
uv run python -m src.cli.main --help
uv run python -m src.cli.main cve last
```

### Running via Docker

vulnctl is part of the Docker Compose stack in [cve-project](https://github.com/dillsh/cve-project) under the `cli` profile:

```bash
# from cve-project/
docker compose run --rm vulnctl cve last
docker compose run --rm vulnctl cve collect --since 2024-01-01
docker compose run --rm vulnctl --help
```

### Tests

```bash
uv run pytest tests/
```

### CI/CD

Workflow: `.github/workflows/ci.yml`

| Trigger | Jobs |
|---|---|
| Pull request → `main` | lint, type check, docker build, unit tests |
| Tag `v*` (e.g. `v1.2.3`) | lint, type check, docker build, unit tests → deploy |

Push to `main` without a tag does not trigger any workflow.

Reusable workflow templates: [ci-cd-templates](https://github.com/dillsh/ci-cd-templates)

### Check deployed version

```bash
docker image inspect cve-project-vulnctl --format '{{.Config.Labels.version}}'
# v1.2.3
```

Local dev builds (without a tag) return `dev`.

### Tech Stack

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
