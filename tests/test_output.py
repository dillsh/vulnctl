"""
Unit tests for CVE output helpers: _cves_to_dicts, _save_cves.

Tests cover JSON/CSV serialisation and the unknown-extension error path.
No network or gRPC calls — pure file I/O via tmp_path.
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import typer

from src.cli.main import _cves_to_dicts, _save_cves
from src.core.ports import AffectedInfo, CVEInfo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_cve(
    cve_id: str = "CVE-2026-0001",
    affected: list[AffectedInfo] | None = None,
    date_updated: datetime | None = None,
) -> CVEInfo:
    return CVEInfo(
        cve_id=cve_id,
        status="PUBLISHED",
        title="Test vulnerability",
        affected=affected or [AffectedInfo(vendor="acme", product="widget")],
        date_updated=date_updated or datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# _cves_to_dicts
# ---------------------------------------------------------------------------


class TestCvesToDicts:
    def test_basic_fields_present(self):
        cve = _make_cve()
        result = _cves_to_dicts([cve])

        assert len(result) == 1
        row = result[0]
        assert row["cve_id"] == "CVE-2026-0001"
        assert row["status"] == "PUBLISHED"
        assert row["title"] == "Test vulnerability"

    def test_date_updated_serialised_as_iso_string(self):
        cve = _make_cve(date_updated=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc))
        row = _cves_to_dicts([cve])[0]

        assert row["date_updated"] == "2026-03-01T12:00:00+00:00"

    def test_date_updated_none_stays_none(self):
        cve = CVEInfo(
            cve_id="CVE-2026-0002",
            status="RESERVED",
            title="",
            date_updated=None,
        )
        row = _cves_to_dicts([cve])[0]

        assert row["date_updated"] is None

    def test_affected_list_serialised(self):
        cve = _make_cve(
            affected=[
                AffectedInfo(
                    vendor="acme",
                    product="widget",
                    version="1.0.0",
                    cpe=["cpe:2.3:a:acme:widget:1.0.0:*"],
                )
            ]
        )
        affected = _cves_to_dicts([cve])[0]["affected"]

        assert len(affected) == 1
        assert affected[0] == {
            "vendor": "acme",
            "product": "widget",
            "version": "1.0.0",
            "cpe": ["cpe:2.3:a:acme:widget:1.0.0:*"],
        }

    def test_affected_none_fields_preserved(self):
        cve = _make_cve(affected=[AffectedInfo(vendor="acme", product="widget")])
        affected = _cves_to_dicts([cve])[0]["affected"]

        assert affected[0]["version"] is None
        assert affected[0]["cpe"] is None

    def test_no_affected_produces_empty_list(self):
        cve = CVEInfo(
            cve_id="CVE-2026-0003",
            status="PUBLISHED",
            title="No affected",
            date_updated=None,
            affected=None,
        )
        row = _cves_to_dicts([cve])[0]

        assert row["affected"] == []

    def test_multiple_cves_all_serialised(self):
        cves = [_make_cve(f"CVE-2026-{i:04d}") for i in range(5)]
        result = _cves_to_dicts(cves)

        assert len(result) == 5
        assert [r["cve_id"] for r in result] == [f"CVE-2026-{i:04d}" for i in range(5)]

    def test_empty_title_becomes_empty_string(self):
        cve = CVEInfo(
            cve_id="CVE-2026-0004",
            status="PUBLISHED",
            title=None,  # type: ignore[arg-type]
            date_updated=None,
        )
        row = _cves_to_dicts([cve])[0]

        assert row["title"] == ""


# ---------------------------------------------------------------------------
# _save_cves — JSON
# ---------------------------------------------------------------------------


class TestSaveCvesJson:
    def test_creates_valid_json_file(self, tmp_path: Path):
        cve = _make_cve()
        out = tmp_path / "report.json"

        _save_cves([cve], out)

        data = json.loads(out.read_text())
        assert isinstance(data, list)
        assert data[0]["cve_id"] == "CVE-2026-0001"

    def test_json_contains_nested_affected(self, tmp_path: Path):
        cve = _make_cve(
            affected=[
                AffectedInfo(vendor="acme", product="widget", version="2.0"),
            ]
        )
        out = tmp_path / "report.json"

        _save_cves([cve], out)

        data = json.loads(out.read_text())
        assert data[0]["affected"][0]["vendor"] == "acme"
        assert data[0]["affected"][0]["version"] == "2.0"

    def test_json_multiple_cves(self, tmp_path: Path):
        cves = [_make_cve(f"CVE-2026-{i:04d}") for i in range(3)]
        out = tmp_path / "report.json"

        _save_cves(cves, out)

        data = json.loads(out.read_text())
        assert len(data) == 3

    def test_json_empty_list(self, tmp_path: Path):
        out = tmp_path / "report.json"

        _save_cves([], out)

        data = json.loads(out.read_text())
        assert data == []


# ---------------------------------------------------------------------------
# _save_cves — CSV
# ---------------------------------------------------------------------------


class TestSaveCvesCsv:
    def _read_csv(self, path: Path) -> list[dict]:
        with path.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_creates_csv_with_header(self, tmp_path: Path):
        out = tmp_path / "report.csv"

        _save_cves([_make_cve()], out)

        rows = self._read_csv(out)
        assert len(rows) == 1
        assert set(rows[0].keys()) == {
            "cve_id",
            "status",
            "title",
            "date_updated",
            "affected",
        }

    def test_csv_basic_fields(self, tmp_path: Path):
        out = tmp_path / "report.csv"

        _save_cves([_make_cve()], out)

        row = self._read_csv(out)[0]
        assert row["cve_id"] == "CVE-2026-0001"
        assert row["status"] == "PUBLISHED"

    def test_csv_affected_flattened(self, tmp_path: Path):
        cve = _make_cve(
            affected=[
                AffectedInfo(vendor="acme", product="widget", version="1.0"),
                AffectedInfo(vendor="corp", product="tool"),
            ]
        )
        out = tmp_path / "report.csv"

        _save_cves([cve], out)

        row = self._read_csv(out)[0]
        assert "acme/widget:1.0" in row["affected"]
        assert "corp/tool" in row["affected"]

    def test_csv_affected_without_version(self, tmp_path: Path):
        cve = _make_cve(affected=[AffectedInfo(vendor="acme", product="widget")])
        out = tmp_path / "report.csv"

        _save_cves([cve], out)

        row = self._read_csv(out)[0]
        assert row["affected"] == "acme/widget"

    def test_csv_multiple_rows(self, tmp_path: Path):
        cves = [_make_cve(f"CVE-2026-{i:04d}") for i in range(4)]
        out = tmp_path / "report.csv"

        _save_cves(cves, out)

        rows = self._read_csv(out)
        assert len(rows) == 4

    def test_csv_empty_list_has_only_header(self, tmp_path: Path):
        out = tmp_path / "report.csv"

        _save_cves([], out)

        rows = self._read_csv(out)
        assert rows == []


# ---------------------------------------------------------------------------
# _save_cves — unknown extension
# ---------------------------------------------------------------------------


class TestSaveCvesUnknownExtension:
    def test_txt_raises_bad_parameter(self, tmp_path: Path):
        out = tmp_path / "report.txt"

        with pytest.raises(typer.BadParameter):
            _save_cves([_make_cve()], out)

    def test_no_extension_raises_bad_parameter(self, tmp_path: Path):
        out = tmp_path / "report"

        with pytest.raises(typer.BadParameter):
            _save_cves([_make_cve()], out)
