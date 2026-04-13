"""
vulnctl CLI — entry point for all commands.

Usage:

user mode (no API key required):
    uv run python -m src.cli.main cve last
    uv run python -m src.cli.main cve last --days 3
    uv run python -m src.cli.main cve last -d 2 -o report.json

admin mode (requires API key):
    cve
    uv run python -m src.cli.main cve list --since 2026-01-01
    uv run python -m src.cli.main cve list --since 2026-01-01 --until 2026-03-02
    uv run python -m src.cli.main cve collect --since 2026-01-01
    uv run python -m src.cli.main cve collect --since 2026-01-01 --until 2026-01-02
    uv run python -m src.cli.main cve schedule $SCHEDULE_NAME # default --cron "0 6 * * *"
    uv run python -m src.cli.main cve schedule $SCHEDULE_NAME --cron "0 10 * * *"

    cpe
    uv run python -m src.cli.main cpe sync
    uv run python -m src.cli.main cpe schedule $SCHEDULE_NAME # default --cron "0 3 * * *"
    uv run python -m src.cli.main cpe schedule $SCHEDULE_NAME --cron "0 5 * * *"

    schedule
    uv run python -m src.cli.main schedule list
    uv run python -m src.cli.main schedule delete $SCHEDULE_NAME
"""

import asyncio
import csv
import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.config import settings

console = Console()
error_console = Console(stderr=True)

app = typer.Typer(
    name="vulnctl",
    help="Vulnerability control CLI — trigger CVE collection and manage schedules.",
    no_args_is_help=True,
)

cve_app = typer.Typer(
    help="CVE operations: query, collect, schedule.",
    no_args_is_help=True,
)
app.add_typer(cve_app, name="cve")

cpe_app = typer.Typer(
    help="CPE dictionary operations: sync, schedule.",
    no_args_is_help=True,
    hidden=True,
)
app.add_typer(cpe_app, name="cpe")

schedule_app = typer.Typer(
    help="Manage all Temporal Schedules (list, delete).",
    no_args_is_help=True,
    hidden=True,
)
app.add_typer(schedule_app, name="schedule")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_temporal_client():
    """Connect to Temporal with the proto-aware payload converter."""
    from temporalio.client import Client
    from temporalio.converter import (
        BinaryNullPayloadConverter,
        DefaultPayloadConverter,
        JSONPlainPayloadConverter,
        JSONProtoPayloadConverter,
    )

    DefaultPayloadConverter.default_encoding_payload_converters = (
        BinaryNullPayloadConverter(),
        JSONProtoPayloadConverter(),
        JSONPlainPayloadConverter(),
    )
    return await Client.connect(f"{settings.temporal_host}:{settings.temporal_port}")


# ---------------------------------------------------------------------------
# cve collect  (admin: one-off CVE collection)
# ---------------------------------------------------------------------------


@cve_app.command("collect", hidden=True)
def cve_collect(
    since: str = typer.Option(..., help="Start date (ISO 8601), e.g. 2024-01-01"),
    until: Optional[str] = typer.Option(
        None, help="End date (ISO 8601), e.g. 2024-01-31"
    ),
) -> None:
    """Trigger a one-off CVE collection run via cve-collector."""
    asyncio.run(_cve_collect(since, until))


async def _cve_collect(since: str, until: Optional[str]) -> None:
    from src.adapters.grpc_collector import GrpcCollectorAdapter
    from src.core.use_cases import TriggerCollection

    adapter = GrpcCollectorAdapter(
        address=settings.collector_grpc_address, api_key=settings.api_key
    )
    use_case = TriggerCollection(collector=adapter)

    try:
        result = await use_case.execute(since=since, until=until)
        console.print(
            f"[green]✓[/green] Workflow started: [bold]{result.workflow_id}[/bold]"
        )
    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to trigger collection: {e}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# cve schedule  (admin: create recurring CVE collection schedule)
# ---------------------------------------------------------------------------


@cve_app.command("schedule", hidden=True)
def cve_schedule(
    schedule_name: str = typer.Argument(
        help="Unique schedule name in Temporal, e.g. daily-cve-collection"
    ),
    cron: str = typer.Option(
        "0 6 * * *",
        help="Cron expression (UTC), e.g. '0 6 * * *' for 06:00 daily",
    ),
) -> None:
    """Create a recurring CVE collection schedule in Temporal."""
    asyncio.run(_cve_schedule(schedule_name, cron))


async def _cve_schedule(schedule_id: str, cron: str) -> None:
    from src.adapters.temporal_scheduler import TemporalSchedulerAdapter
    from src.core.use_cases import ManageSchedule

    client = await _create_temporal_client()
    use_case = ManageSchedule(scheduler=TemporalSchedulerAdapter(client=client))

    try:
        await use_case.create(schedule_id=schedule_id, cron=cron)
        console.print(
            f"[green]✓[/green] Schedule [bold]{schedule_id}[/bold] created  (cron: {cron})"
        )
    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to create schedule: {e}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# cpe sync  (admin: one-off CPE dictionary sync)
# ---------------------------------------------------------------------------


@cpe_app.command("sync")
def cpe_sync() -> None:
    """Manually trigger a one-off NVD CPE dictionary sync."""
    asyncio.run(_cpe_sync())


async def _cpe_sync() -> None:
    from datetime import datetime

    client = await _create_temporal_client()
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    workflow_id = f"sync-cpe-manual-{run_id}"

    try:
        handle = await client.start_workflow(
            "SyncCPEDictionaryWorkflow",
            id=workflow_id,
            task_queue=settings.collector_task_queue,
        )
        console.print(
            f"[green]✓[/green] CPE sync workflow started: [bold]{handle.id}[/bold]"
        )
    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to start CPE sync: {e}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# cpe schedule  (admin: create recurring CPE sync schedule)
# ---------------------------------------------------------------------------


@cpe_app.command("schedule")
def cpe_schedule(
    schedule_name: str = typer.Argument(
        help="Unique schedule name in Temporal, e.g. daily-cpe-sync"
    ),
    cron: str = typer.Option(
        "0 3 * * *",
        help="Cron expression (UTC), e.g. '0 3 * * *' for 03:00 daily",
    ),
) -> None:
    """Create a recurring NVD CPE dictionary sync schedule in Temporal."""
    asyncio.run(_cpe_schedule(schedule_name, cron))


async def _cpe_schedule(schedule_id: str, cron: str) -> None:
    from src.adapters.temporal_scheduler import TemporalSchedulerAdapter

    client = await _create_temporal_client()
    adapter = TemporalSchedulerAdapter(client=client)

    try:
        await adapter.create_cpe_sync(schedule_id=schedule_id, cron=cron)
        console.print(
            f"[green]✓[/green] CPE sync schedule [bold]{schedule_id}[/bold] created  (cron: {cron})"
        )
    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to create CPE sync schedule: {e}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# schedule list
# ---------------------------------------------------------------------------


@schedule_app.command("list")
def schedule_list() -> None:
    """List all active Temporal Schedules."""
    asyncio.run(_schedule_list())


async def _schedule_list() -> None:
    from src.adapters.temporal_scheduler import TemporalSchedulerAdapter
    from src.core.use_cases import ManageSchedule

    client = await _create_temporal_client()
    use_case = ManageSchedule(scheduler=TemporalSchedulerAdapter(client=client))

    try:
        schedules = await use_case.list()
    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to list schedules: {e}")
        raise typer.Exit(1)

    if not schedules:
        console.print("[yellow]No schedules found.[/yellow]")
        return

    table = Table("Name", "Cron", "Next Run (UTC)")
    for s in schedules:
        table.add_row(s.schedule_id, s.cron, s.next_run or "—")
    console.print(table)


# ---------------------------------------------------------------------------
# schedule delete
# ---------------------------------------------------------------------------


@schedule_app.command("delete")
def schedule_delete(
    schedule_name: str = typer.Argument(help="Schedule name to delete"),
) -> None:
    """Delete a Temporal Schedule by name."""
    asyncio.run(_schedule_delete(schedule_name))


async def _schedule_delete(schedule_id: str) -> None:
    from src.adapters.temporal_scheduler import TemporalSchedulerAdapter
    from src.core.use_cases import ManageSchedule

    client = await _create_temporal_client()
    use_case = ManageSchedule(scheduler=TemporalSchedulerAdapter(client=client))

    try:
        await use_case.delete(schedule_id=schedule_id)
        console.print(f"[green]✓[/green] Schedule [bold]{schedule_id}[/bold] deleted.")
    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to delete schedule: {e}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _cves_to_dicts(cves) -> list[dict]:
    result = []
    for cve in cves:
        result.append(
            {
                "cve_id": cve.cve_id,
                "status": cve.status,
                "title": cve.title or "",
                "date_updated": (
                    cve.date_updated.isoformat() if cve.date_updated else None
                ),
                "affected": [
                    {
                        "vendor": a.vendor,
                        "product": a.product,
                        "version": a.version,
                        "cpe": a.cpe,
                    }
                    for a in (cve.affected or [])
                ],
            }
        )
    return result


def _save_cves(cves, output: Path) -> None:
    suffix = output.suffix.lower()
    if suffix == ".json":
        data = _cves_to_dicts(cves)
        output.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    elif suffix == ".csv":
        rows = _cves_to_dicts(cves)
        fieldnames = ["cve_id", "status", "title", "date_updated", "affected"]
        with output.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                row["affected"] = "; ".join(
                    f"{a['vendor']}/{a['product']}"
                    + (f":{a['version']}" if a["version"] else "")
                    for a in row["affected"]
                )
                writer.writerow(row)
    else:
        raise typer.BadParameter(
            f"Unsupported file extension '{suffix}'. Use .json or .csv",
            param_hint="--output",
        )


# ---------------------------------------------------------------------------
# cve list  (admin: query by date range)
# ---------------------------------------------------------------------------


@cve_app.command("list", hidden=True)
def cve_list(
    since: str = typer.Option(
        ..., "--since", help='Start date (ISO 8601), e.g. "2024-01-01"'
    ),
    until: Optional[str] = typer.Option(
        None, "--until", help='End date (ISO 8601), e.g. "2024-06-01"'
    ),
) -> None:
    """List CVEs from cve-core updated within the given date range."""
    asyncio.run(_cve_list(since, until))


async def _cve_list(since: str, until: Optional[str]) -> None:
    from src.adapters.grpc_cve_store import GrpcCVEStoreAdapter
    from src.core.use_cases import ListCVEs

    adapter = GrpcCVEStoreAdapter(
        address=settings.cve_core_grpc_address, api_key=settings.api_key
    )
    try:
        cves = await ListCVEs(store=adapter).execute(since=since, until=until)
    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to list CVEs: {e}")
        raise typer.Exit(1)

    if not cves:
        console.print("[yellow]No CVEs found.[/yellow]")
        return

    table = Table("CVE ID", "Status", "Title", "Affected", "Date Updated")
    for cve in cves:
        date_str = (
            cve.date_updated.strftime("%Y-%m-%d %H:%M UTC") if cve.date_updated else "—"
        )
        affected_str = (
            ", ".join(f"{a.vendor}/{a.product}" for a in cve.affected)
            if cve.affected
            else "—"
        )
        table.add_row(
            cve.cve_id,
            cve.status,
            cve.title or "—",
            affected_str,
            date_str,
        )
    console.print(table)


# ---------------------------------------------------------------------------
# cve last  (user: last N days, no API key required)
# ---------------------------------------------------------------------------


@cve_app.command("last")
def cve_last(
    days: int = typer.Option(
        1,
        "--days",
        "-d",
        min=1,
        max=3,
        help="Number of days to look back (1–3). Default: 1.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Save results to a file instead of printing. Format is inferred from extension: .json or .csv",
    ),
) -> None:
    """Show CVEs from the last N days (1–3). No API key required."""
    asyncio.run(_cve_last(days, output))


async def _cve_last(days: int, output: Optional[Path]) -> None:
    from src.adapters.http_cve_store import HttpCVEStoreAdapter
    from src.core.use_cases import LastCVEs

    adapter = HttpCVEStoreAdapter(base_url=settings.cve_core_http_base_url)
    try:
        cves = await LastCVEs(store=adapter).execute(days=days)
    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to list CVEs: {e}")
        raise typer.Exit(1)

    if not cves:
        console.print("[yellow]No CVEs found.[/yellow]")
        return

    if output:
        try:
            _save_cves(cves, output)
            console.print(
                f"[green]✓[/green] {len(cves)} CVE(s) saved to [bold]{output}[/bold]"
            )
        except typer.BadParameter:
            raise
        except Exception as e:
            error_console.print(f"[red]✗[/red] Failed to write file: {e}")
            raise typer.Exit(1)
        return

    table = Table("CVE ID", "Status", "Title", "Affected", "Date Updated")
    for cve in cves:
        date_str = (
            cve.date_updated.strftime("%Y-%m-%d %H:%M UTC") if cve.date_updated else "—"
        )
        affected_str = (
            ", ".join(f"{a.vendor}/{a.product}" for a in cve.affected)
            if cve.affected
            else "—"
        )
        table.add_row(
            cve.cve_id,
            cve.status,
            cve.title or "—",
            affected_str,
            date_str,
        )
    console.print(table)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app()
