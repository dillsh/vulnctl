"""
vulnctl CLI — user-facing entry point.

Usage:
    vulnctl cve last
    vulnctl cve last --days 3
    vulnctl cve last -d 2 -o report.json

Admin commands (collect, schedule, cpe sync, etc.) live in the
cve-collector CLI — run them via:
    task cli -- <command>   (inside the running container)
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
    help="Query recent CVE vulnerabilities. No API key required.",
    no_args_is_help=True,
)

cve_app = typer.Typer(
    help="CVE operations.",
    no_args_is_help=True,
)
app.add_typer(cve_app, name="cve")


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _cves_to_dicts(cves) -> list[dict]:
    return [
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
        for cve in cves
    ]


def _save_cves(cves, output: Path) -> None:
    suffix = output.suffix.lower()
    if suffix == ".json":
        output.write_text(
            json.dumps(_cves_to_dicts(cves), indent=2, ensure_ascii=False),
            encoding="utf-8",
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
        help="Save results to a file. Format inferred from extension: .json or .csv",
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
