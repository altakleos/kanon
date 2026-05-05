"""Direct unit tests for _gates.py — evaluate_gates subprocess execution."""
from __future__ import annotations

import json
from pathlib import Path

from kanon_core._gates import evaluate_gates, write_trace


class TestEvaluateGates:
    """Test evaluate_gates subprocess execution logic."""

    def test_gate_with_passing_check(self, tmp_path: Path) -> None:
        gates = [{"label": "pass-gate", "aspect": "kanon-sdd", "protocol": "p.md",
                  "protocol_path": ".kanon/protocols/kanon-sdd/p.md", "priority": 1,
                  "check": "true", "question": "", "audit": "", "skip_when": ""}]
        results = evaluate_gates(gates, tmp_path)
        assert len(results) == 1
        assert results[0]["status"] == "pass"
        assert results[0]["exit_code"] == 0
        assert results[0]["duration_s"] >= 0

    def test_gate_with_failing_check(self, tmp_path: Path) -> None:
        gates = [{"label": "fail-gate", "aspect": "kanon-sdd", "protocol": "p.md",
                  "protocol_path": ".kanon/protocols/kanon-sdd/p.md", "priority": 1,
                  "check": "false", "question": "", "audit": "", "skip_when": ""}]
        results = evaluate_gates(gates, tmp_path)
        assert results[0]["status"] == "fail"
        assert results[0]["exit_code"] != 0

    def test_gate_with_timeout(self, tmp_path: Path) -> None:
        gates = [{"label": "slow-gate", "aspect": "kanon-sdd", "protocol": "p.md",
                  "protocol_path": ".kanon/protocols/kanon-sdd/p.md", "priority": 1,
                  "check": "sleep 60", "question": "", "audit": "", "skip_when": ""}]
        # Monkey-patch timeout to 1s for test speed
        import kanon_core._gates as gates_mod
        import subprocess
        original_run = subprocess.run

        def fast_timeout_run(*args, **kwargs):
            kwargs["timeout"] = 1
            return original_run(*args, **kwargs)

        gates_mod.subprocess.run = fast_timeout_run
        try:
            results = evaluate_gates(gates, tmp_path)
        finally:
            gates_mod.subprocess.run = original_run
        assert results[0]["status"] == "fail"
        assert results[0]["exit_code"] == -1

    def test_gate_without_check_is_judgment(self, tmp_path: Path) -> None:
        gates = [{"label": "judgment-gate", "aspect": "kanon-sdd", "protocol": "p.md",
                  "protocol_path": ".kanon/protocols/kanon-sdd/p.md", "priority": 1,
                  "check": None, "question": "Is this safe?", "audit": "Confirmed safe.",
                  "skip_when": "no changes"}]
        results = evaluate_gates(gates, tmp_path)
        assert results[0]["status"] == "judgment"
        assert results[0]["question"] == "Is this safe?"
        assert results[0]["audit"] == "Confirmed safe."
        assert results[0]["exit_code"] is None

    def test_fail_fast_stops_after_first_failure(self, tmp_path: Path) -> None:
        gates = [
            {"label": "g1", "aspect": "a", "protocol": "p.md",
             "protocol_path": "x", "priority": 1,
             "check": "false", "question": "", "audit": "", "skip_when": ""},
            {"label": "g2", "aspect": "a", "protocol": "q.md",
             "protocol_path": "y", "priority": 2,
             "check": "true", "question": "", "audit": "", "skip_when": ""},
        ]
        results = evaluate_gates(gates, tmp_path, fail_fast=True)
        assert len(results) == 1
        assert results[0]["label"] == "g1"

    def test_multiple_gates_all_run_without_fail_fast(self, tmp_path: Path) -> None:
        gates = [
            {"label": "g1", "aspect": "a", "protocol": "p.md",
             "protocol_path": "x", "priority": 1,
             "check": "false", "question": "", "audit": "", "skip_when": ""},
            {"label": "g2", "aspect": "a", "protocol": "q.md",
             "protocol_path": "y", "priority": 2,
             "check": "true", "question": "", "audit": "", "skip_when": ""},
        ]
        results = evaluate_gates(gates, tmp_path, fail_fast=False)
        assert len(results) == 2


class TestWriteTrace:
    """Test write_trace JSONL output."""

    def test_creates_trace_file(self, tmp_path: Path) -> None:
        results = [{"label": "g1", "status": "pass"}]
        write_trace(tmp_path, results)
        trace_file = tmp_path / ".kanon" / "traces" / "gates.jsonl"
        assert trace_file.exists()
        entry = json.loads(trace_file.read_text().strip())
        assert entry["passed"] is True
        assert entry["gates"] == [{"label": "g1", "status": "pass"}]

    def test_appends_to_existing_trace(self, tmp_path: Path) -> None:
        write_trace(tmp_path, [{"label": "g1", "status": "pass"}])
        write_trace(tmp_path, [{"label": "g2", "status": "fail"}])
        trace_file = tmp_path / ".kanon" / "traces" / "gates.jsonl"
        lines = trace_file.read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[1])["passed"] is False
