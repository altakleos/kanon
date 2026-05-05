"""Direct unit tests for _run_verify_core (extracted verify logic)."""
from __future__ import annotations

import json
import platform
from pathlib import Path

import pytest
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


def test_gates_check_exits_1_outside_worktree(tmp_path: Path) -> None:
    """gates check exits 1 when worktree gate fails (CWD not in .worktrees/)."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--aspects", "kanon-sdd:1,kanon-worktrees:1"])

    result = runner.invoke(main, ["gates", "check", str(target)])
    assert result.exit_code == 1, f"Expected exit 1, got {result.exit_code}: {result.output}"

    report, _ = json.JSONDecoder().raw_decode(result.output[result.output.index("{"):])
    assert report["passed"] is False
    assert report["summary"]["fail"] >= 1

    # Worktree Isolation gate specifically failed
    worktree_gate = next(g for g in report["gates"] if g["label"] == "Worktree Isolation")
    assert worktree_gate["status"] == "fail"
    assert worktree_gate["exit_code"] != 0
    assert worktree_gate["protocol_path"] == ".kanon/protocols/kanon-worktrees/branch-hygiene.md"


@pytest.mark.skipif(
    platform.system() == "Linux",
    reason="Worktree shell check uses [[ ]] which requires bash; /bin/sh on Linux is dash",
)
def test_gates_check_passes_inside_worktree(tmp_path: Path) -> None:
    """gates check passes when target path contains .worktrees/ segment."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--aspects", "kanon-sdd:1,kanon-worktrees:1"])

    # Create a .worktrees/ subdirectory and copy .kanon into it
    wt_dir = target / ".worktrees" / "my-task"
    wt_dir.mkdir(parents=True)
    import shutil
    shutil.copytree(target / ".kanon", wt_dir / ".kanon")
    shutil.copy2(target / "AGENTS.md", wt_dir / "AGENTS.md")

    result = runner.invoke(main, ["gates", "check", str(wt_dir)])
    report, _ = json.JSONDecoder().raw_decode(result.output[result.output.index("{"):])

    worktree_gate = next(g for g in report["gates"] if g["label"] == "Worktree Isolation")
    assert worktree_gate["status"] == "pass"


def test_gates_check_json_schema_contract(tmp_path: Path) -> None:
    """gates check output has the expected JSON schema agents parse."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--aspects", "kanon-sdd:1,kanon-worktrees:1"])

    result = runner.invoke(main, ["gates", "check", str(target)])
    report, _ = json.JSONDecoder().raw_decode(result.output[result.output.index("{"):])

    # Top-level keys
    assert "target" in report
    assert "passed" in report
    assert "summary" in report
    assert "gates" in report
    assert isinstance(report["passed"], bool)

    # Summary keys
    for key in ("total", "pass", "fail", "judgment"):
        assert key in report["summary"]
        assert isinstance(report["summary"][key], int)

    # Each gate has required fields
    for gate in report["gates"]:
        assert "label" in gate
        assert "status" in gate
        assert gate["status"] in ("pass", "fail", "judgment")
        assert "aspect" in gate
        assert "protocol_path" in gate
        assert "priority" in gate
        assert "exit_code" in gate
        assert "duration_s" in gate


def test_gates_check_judgment_gates_have_question_and_audit(tmp_path: Path) -> None:
    """Judgment gates include question and audit fields for agent self-evaluation."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--aspects", "kanon-sdd:1,kanon-worktrees:1"])

    result = runner.invoke(main, ["gates", "check", str(target)])
    report, _ = json.JSONDecoder().raw_decode(result.output[result.output.index("{"):])

    judgment_gates = [g for g in report["gates"] if g["status"] == "judgment"]
    assert len(judgment_gates) >= 1, "Expected at least one judgment gate"

    for gate in judgment_gates:
        assert "question" in gate and gate["question"], f"{gate['label']} missing question"
        assert "audit" in gate and gate["audit"], f"{gate['label']} missing audit"
        assert gate["exit_code"] is None


def test_gates_check_depth_filtering_excludes_deep_gates(tmp_path: Path) -> None:
    """Gates with depth-min > current depth are excluded from output."""
    runner = CliRunner()
    target = tmp_path / "proj"
    # sdd depth 1 — design-before-plan requires depth-min 3
    runner.invoke(main, ["init", str(target), "--aspects", "kanon-sdd:1,kanon-worktrees:1"])

    result = runner.invoke(main, ["gates", "check", str(target)])
    report, _ = json.JSONDecoder().raw_decode(result.output[result.output.index("{"):])

    labels = [g["label"] for g in report["gates"]]
    assert "Design Before Plan" not in labels, "depth-3 gate should not appear at depth 1"
    assert "Plan Before Build" in labels, "depth-1 gate should appear"


def test_gates_check_trace_written(tmp_path: Path) -> None:
    """gates check writes an audit trace to .kanon/traces/gates.jsonl."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--aspects", "kanon-sdd:1,kanon-worktrees:1"])

    runner.invoke(main, ["gates", "check", str(target)])

    trace_file = target / ".kanon" / "traces" / "gates.jsonl"
    assert trace_file.exists(), "Trace file not created"

    line = trace_file.read_text().strip().splitlines()[-1]
    entry = json.loads(line)
    assert "ts" in entry
    assert "gates" in entry
    assert "passed" in entry
    assert isinstance(entry["passed"], bool)
