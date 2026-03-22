"""
vulnctl user CLI — standalone entry point for the public binary.

Only includes `cve list` via HTTP — no gRPC or Temporal dependencies.

Usage:
    vulnctl cve list --since 2024-01-01
"""

import asyncio
import logging
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()
error_console = Console(stderr=True)

app = typer.Typer(
    name="vulnctl",
    help="Query CVEs from cve-core.",
    no_args_is_help=True,
)

cve_app = typer.Typer(
    help="Query CVEs from cve-core.",
    no_args_is_help=True,
)
app.add_typer(cve_app, name="cve")


@cve_app.command("list")
def cve_list(
    since: str = typer.Option(..., "--since", help='Start date (ISO 8601), e.g. "2024-01-01"'),
    until: Optional[str] = typer.Option(None, "--until", help='End date (ISO 8601), e.g. "2024-06-01"'),
) -> None:
    """List CVEs from cve-core updated within the given date range."""
    import os
    from src.cli._constants import CVE_CORE_HTTP_HOST as _DEFAULT_HOST, CVE_CORE_HTTP_PORT as _DEFAULT_PORT
    host = os.environ.get("CVE_CORE_HTTP_HOST", _DEFAULT_HOST)
    port = int(os.environ.get("CVE_CORE_HTTP_PORT", str(_DEFAULT_PORT)))
    asyncio.run(_cve_list(since, until, host, port))


async def _cve_list(since: str, until: Optional[str], host: str, port: int) -> None:
    from src.adapters.http_cve_store import HttpCVEStoreAdapter
    from src.core.use_cases import ListCVEs

    adapter = HttpCVEStoreAdapter(base_url=f"http://{host}:{port}")
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
        date_str = cve.date_updated.strftime("%Y-%m-%d %H:%M UTC") if cve.date_updated else "—"
        affected_str = (
            ", ".join(f"{a.vendor}/{a.product}" for a in cve.affected)
            if cve.affected else "—"
        )
        table.add_row(cve.cve_id, cve.status, cve.title or "—", affected_str, date_str)
    console.print(table)


if __name__ == "__main__":
    logging.basicConfig(level="WARNING")
    app()
