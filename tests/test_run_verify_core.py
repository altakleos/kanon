"""Direct unit tests for _run_verify_core (extracted verify logic)."""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from kanon_core.cli import _run_verify_core, main


def _init_project(tmp_path: Path) -> Path:
    target = tmp_path / "proj"
    CliRunner().invoke(main, ["init", str(target), "--profile", "solo", "--quiet"])
    return target


def test_run_verify_core_returns_ok_on_valid_project(tmp_path: Path) -> None:
    """A freshly initialized project passes verification."""
    target = _init_project(tmp_path)
    result = _run_verify_core(target)
    assert result["status"] == "ok"
    assert result["errors"] == []
    assert "aspects" in result
    assert isinstance(result["warnings"], list)


def test_run_verify_core_returns_fail_on_missing_config(tmp_path: Path) -> None:
    """Missing config.yaml produces a fail result (not an exception)."""
    target = _init_project(tmp_path)
    (target / ".kanon" / "config.yaml").unlink()
    result = _run_verify_core(target)
    assert result["status"] == "fail"
    assert len(result["errors"]) > 0


def test_run_verify_core_returns_fail_on_missing_required_file(tmp_path: Path) -> None:
    """Missing AGENTS.md produces errors."""
    target = _init_project(tmp_path)
    (target / "AGENTS.md").unlink()
    result = _run_verify_core(target)
    assert result["status"] == "fail"
    assert any("AGENTS.md" in e for e in result["errors"])


def test_gates_check_on_valid_project(tmp_path: Path) -> None:
    """gates check on a valid project exits 0 and produces JSON."""
    target = _init_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["gates", "check", str(target)])
    assert result.exit_code == 0, result.output
    # Output has stderr lines mixed in; find the JSON object
    report, _ = json.JSONDecoder().raw_decode(result.output[result.output.index("{"):])
    assert "passed" in report
    assert "summary" in report


def test_gates_check_with_filter(tmp_path: Path) -> None:
    """gates check --gate filters to matching labels only."""
    target = _init_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["gates", "check", str(target), "--gate", "Nonexistent"])
    assert result.exit_code == 0
    report, _ = json.JSONDecoder().raw_decode(result.output[result.output.index("{"):])
    assert report["summary"]["total"] == 0
