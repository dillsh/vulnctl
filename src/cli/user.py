"""
vulnctl user CLI — standalone entry point for the public binary.

Only exposes `cve last` via HTTP REST — no API key required.

Usage:
    vulnctl cve last
    vulnctl cve last --days 3
    vulnctl cve last -d 2 -o report.json
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
    help="Query recent CVE vulnerabilities. No API key required.",
    no_args_is_help=True,
)

cve_app = typer.Typer(
    help="Query CVEs from cve-core.",
    no_args_is_help=True,
)
app.add_typer(cve_app, name="cve")


@cve_app.command("last")
def cve_last(
    days: int = typer.Option(
        1,
        "--days",
        "-d",
        min=1,
        max=3,
        help="Days to look back: 1, 2, or 3 (default: 1)",
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Save to file (.json or .csv) instead of printing"
    ),
) -> None:
    """Show CVEs from the last N days (1–3). No API key required."""
    import os
    from src.cli._constants import (
        CVE_CORE_HTTP_HOST as _DEFAULT_HOST,
        CVE_CORE_HTTP_PORT as _DEFAULT_PORT,
    )

    host = os.environ.get("CVE_CORE_HTTP_HOST", _DEFAULT_HOST)
    port = int(os.environ.get("CVE_CORE_HTTP_PORT", str(_DEFAULT_PORT)))
    asyncio.run(_cve_last(days, output, host, port))


async def _cve_last(days: int, output: Optional[str], host: str, port: int) -> None:
    from src.adapters.http_cve_store import HttpCVEStoreAdapter
    from src.core.use_cases import LastCVEs

    adapter = HttpCVEStoreAdapter(base_url=f"http://{host}:{port}")
    try:
        cves = await LastCVEs(store=adapter).execute(days=days)
    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to list CVEs: {e}")
        raise typer.Exit(1)

    if not cves:
        console.print("[yellow]No CVEs found.[/yellow]")
        return

    if output:
        import csv
        import json
        from pathlib import Path

        suffix = Path(output).suffix.lower()
        if suffix == ".json":
            data = [
                {
                    "cve_id": cve.cve_id,
                    "status": cve.status,
                    "title": cve.title,
                    "affected": [
                        {
                            "vendor": a.vendor,
                            "product": a.product,
                            "version": a.version,
                            "cpe": a.cpe,
                        }
                        for a in (cve.affected or [])
                    ],
                    "date_updated": cve.date_updated.isoformat()
                    if cve.date_updated
                    else None,
                }
                for cve in cves
            ]
            Path(output).write_text(json.dumps(data, indent=2))
        elif suffix == ".csv":
            with open(output, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["cve_id", "status", "title", "affected", "date_updated"]
                )
                for cve in cves:
                    affected_str = ", ".join(
                        f"{a.vendor}/{a.product}"
                        + (f":{a.version}" if a.version else "")
                        for a in (cve.affected or [])
                    )
                    writer.writerow(
                        [
                            cve.cve_id,
                            cve.status,
                            cve.title or "",
                            affected_str,
                            cve.date_updated.isoformat() if cve.date_updated else "",
                        ]
                    )
        else:
            raise typer.BadParameter(
                f"Unsupported file extension '{suffix}'. Use .json or .csv",
                param_hint="--output",
            )
        console.print(f"[green]✓[/green] {len(cves)} CVE(s) saved to {output}")
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
        table.add_row(cve.cve_id, cve.status, cve.title or "—", affected_str, date_str)
    console.print(table)


if __name__ == "__main__":
    logging.basicConfig(level="WARNING")
    app()
