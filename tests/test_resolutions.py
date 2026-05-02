"""Phase A.6a: resolutions engine tests.

Per ADR-0039 / docs/specs/resolutions.md / docs/design/resolutions-engine.md.
The kanon repo has no real ``.kanon/resolutions.yaml`` yet (no contract-bearing
aspects ship ``realization-shape:`` frontmatter), so all tests use synthetic
fixtures built in tmp_path. Phase A.6b/A.6c/A.7 expand the workload.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from kanon._resolutions import (
    ExecutionRecord,
    ReplayError,
    ReplayReport,
    canonicalize_entry,
    replay,
    stale_check,
)


# --- Helpers ---


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _make_entry(
    contract_path: Path,
    evidence: list[tuple[str, bytes, str]],
    *,
    semantic_version: str = "1.0",
    realized_by: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a per-contract entry whose pins all match the given files."""
    if realized_by is None:
        realized_by = [
            {"label": "lint", "invocation": "ruff check .", "invocation-form": "shell"}
        ]
    entry = {
        "semantic-version": semantic_version,
        "contract-content-sha": _sha(contract_path.read_bytes()),
        "realized-by": realized_by,
        "evidence": [
            {"path": rel, "sha": _sha(content), "cite": cite}
            for rel, content, cite in evidence
        ],
    }
    entry["meta-checksum"] = _sha(canonicalize_entry(entry))
    return entry


def _build_synthetic_target(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    """Build a target dir + registry with one synthetic aspect + contract.

    Returns (target_path, registry_dict). The registry uses the same shape
    `_load_aspect_registry()` produces — `{aspects: {<slug>: {_source, ...}}}`.
    """
    target = tmp_path / "consumer"
    target.mkdir()
    aspect_root = tmp_path / "publisher" / "synthetic-aspect"
    contracts_dir = aspect_root / "contracts"
    contracts_dir.mkdir(parents=True)
    contract = contracts_dir / "preflight.md"
    contract.write_text("# Preflight contract\n\nLint the source tree.\n", encoding="utf-8")

    # Evidence file in target.
    pyproject = target / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\nline-length = 120\n", encoding="utf-8")

    registry = {
        "aspects": {
            "synthetic-aspect": {
                "_source": str(aspect_root),
                "stability": "experimental",
                "depth-range": [0, 1],
                "default-depth": 1,
            },
        }
    }
    return target, registry


def _write_resolutions(target: Path, contracts: dict[str, dict[str, Any]]) -> None:
    rfile = target / ".kanon" / "resolutions.yaml"
    rfile.parent.mkdir(parents=True, exist_ok=True)
    rfile.write_text(
        yaml.safe_dump(
            {
                "schema-version": 1,
                "resolved-at": "2026-05-02T12:00:00Z",
                "resolver-environment": {
                    "model": "claude-opus-4-7-2026-04-22",
                    "harness": "claude-code",
                },
                "contracts": contracts,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


# --- Canonicalization ---


def test_canonicalize_strips_meta_checksum() -> None:
    entry = {"meta-checksum": "should-be-stripped", "b": 1, "a": [3, 2]}
    out = canonicalize_entry(entry)
    decoded = json.loads(out)
    assert "meta-checksum" not in decoded
    assert decoded == {"a": [3, 2], "b": 1}


def test_canonicalize_sorts_keys_recursively() -> None:
    entry = {"z": 1, "a": {"y": 2, "b": [3, {"d": 4, "c": 5}]}}
    out = canonicalize_entry(entry)
    # Compact form, sorted keys at every depth.
    assert b'"a":{"b":[3,{"c":5,"d":4}]' in out
    assert out.index(b'"a"') < out.index(b'"z"')


def test_canonicalize_deterministic() -> None:
    entry = {"meta-checksum": "x", "b": 1, "a": 2}
    assert canonicalize_entry(entry) == canonicalize_entry(entry)


# --- Empty / missing resolutions ---


def test_replay_missing_file_returns_empty_report(tmp_path: Path) -> None:
    target = tmp_path / "consumer"
    target.mkdir()
    report = replay(target, registry={"aspects": {}})
    assert report.ok
    assert report.errors == []
    assert report.executions == []


def test_stale_check_missing_file_returns_empty_report(tmp_path: Path) -> None:
    target = tmp_path / "consumer"
    target.mkdir()
    report = stale_check(target, registry={"aspects": {}})
    assert report.ok


# --- Schema validation ---


def test_replay_unknown_schema_version_errors(tmp_path: Path) -> None:
    target, registry = _build_synthetic_target(tmp_path)
    rfile = target / ".kanon" / "resolutions.yaml"
    rfile.parent.mkdir(parents=True, exist_ok=True)
    rfile.write_text("schema-version: 99\ncontracts: {}\n", encoding="utf-8")
    report = replay(target, registry=registry)
    assert any(e.code == "unknown-schema-version" for e in report.errors)


def test_replay_invalid_yaml_errors(tmp_path: Path) -> None:
    target, registry = _build_synthetic_target(tmp_path)
    rfile = target / ".kanon" / "resolutions.yaml"
    rfile.parent.mkdir(parents=True, exist_ok=True)
    rfile.write_text(": : not valid yaml\n", encoding="utf-8")
    report = replay(target, registry=registry)
    assert any(e.code == "invalid-resolution-yaml" for e in report.errors)


# --- INV-resolutions-machine-only-owned ---


def test_replay_hand_edit_detected(tmp_path: Path) -> None:
    target, registry = _build_synthetic_target(tmp_path)
    contract = Path(registry["aspects"]["synthetic-aspect"]["_source"]) / "contracts" / "preflight.md"
    pyproject = target / "pyproject.toml"
    entry = _make_entry(contract, [("pyproject.toml", pyproject.read_bytes(), "lint config")])
    # Tamper: change a field after meta-checksum was computed.
    entry["realized-by"][0]["invocation"] = "ruff check src/"  # tampered
    _write_resolutions(target, {"synthetic-aspect/preflight": entry})
    report = replay(target, registry=registry)
    assert any(
        e.code == "hand-edit-detected" and e.contract == "synthetic-aspect/preflight"
        for e in report.errors
    )


def test_replay_missing_meta_checksum_errors(tmp_path: Path) -> None:
    target, registry = _build_synthetic_target(tmp_path)
    contract = Path(registry["aspects"]["synthetic-aspect"]["_source"]) / "contracts" / "preflight.md"
    pyproject = target / "pyproject.toml"
    entry = _make_entry(contract, [("pyproject.toml", pyproject.read_bytes(), "x")])
    del entry["meta-checksum"]
    _write_resolutions(target, {"synthetic-aspect/preflight": entry})
    report = replay(target, registry=registry)
    assert any(e.code == "hand-edit-detected" for e in report.errors)


# --- INV-resolutions-quadruple-pin ---


def test_replay_clean_passes_all_pins(tmp_path: Path) -> None:
    target, registry = _build_synthetic_target(tmp_path)
    contract = Path(registry["aspects"]["synthetic-aspect"]["_source"]) / "contracts" / "preflight.md"
    pyproject = target / "pyproject.toml"
    entry = _make_entry(contract, [("pyproject.toml", pyproject.read_bytes(), "lint config")])
    _write_resolutions(target, {"synthetic-aspect/preflight": entry})
    report = replay(target, registry=registry)
    assert report.ok, f"expected clean report, got errors: {report.errors}"
    assert len(report.executions) == 1
    assert report.executions[0].executed is False  # A.6a stub
    assert "Phase A.6a stub" in (report.executions[0].reason or "")


def test_replay_contract_content_drift_errors(tmp_path: Path) -> None:
    target, registry = _build_synthetic_target(tmp_path)
    contract = Path(registry["aspects"]["synthetic-aspect"]["_source"]) / "contracts" / "preflight.md"
    pyproject = target / "pyproject.toml"
    entry = _make_entry(contract, [("pyproject.toml", pyproject.read_bytes(), "x")])
    # After resolution: the contract file is edited.
    contract.write_text("# Preflight contract\n\nLint the source tree (UPDATED).\n", encoding="utf-8")
    _write_resolutions(target, {"synthetic-aspect/preflight": entry})
    report = replay(target, registry=registry)
    assert any(
        e.code == "stale-resolution" and "drift" in (e.reason or "")
        for e in report.errors
    )


def test_replay_evidence_drift_errors(tmp_path: Path) -> None:
    target, registry = _build_synthetic_target(tmp_path)
    contract = Path(registry["aspects"]["synthetic-aspect"]["_source"]) / "contracts" / "preflight.md"
    pyproject = target / "pyproject.toml"
    entry = _make_entry(contract, [("pyproject.toml", pyproject.read_bytes(), "x")])
    # After resolution: the evidence file is edited.
    pyproject.write_text("[tool.ruff]\nline-length = 100\n", encoding="utf-8")
    _write_resolutions(target, {"synthetic-aspect/preflight": entry})
    report = replay(target, registry=registry)
    assert any(
        e.code == "sha-mismatch" and e.path == "pyproject.toml"
        for e in report.errors
    )


def test_replay_missing_contract_errors(tmp_path: Path) -> None:
    target, registry = _build_synthetic_target(tmp_path)
    contract = Path(registry["aspects"]["synthetic-aspect"]["_source"]) / "contracts" / "preflight.md"
    pyproject = target / "pyproject.toml"
    entry = _make_entry(contract, [("pyproject.toml", pyproject.read_bytes(), "x")])
    contract.unlink()  # remove contract source
    _write_resolutions(target, {"synthetic-aspect/preflight": entry})
    report = replay(target, registry=registry)
    assert any(e.code == "missing-contract" for e in report.errors)


# --- INV-resolutions-evidence-grounded ---


def test_replay_empty_evidence_errors(tmp_path: Path) -> None:
    target, registry = _build_synthetic_target(tmp_path)
    contract = Path(registry["aspects"]["synthetic-aspect"]["_source"]) / "contracts" / "preflight.md"
    entry = _make_entry(contract, [])  # no evidence
    _write_resolutions(target, {"synthetic-aspect/preflight": entry})
    report = replay(target, registry=registry)
    assert any(
        e.code == "ungrounded-resolution" and e.contract == "synthetic-aspect/preflight"
        for e in report.errors
    )


def test_replay_missing_evidence_file_errors(tmp_path: Path) -> None:
    target, registry = _build_synthetic_target(tmp_path)
    contract = Path(registry["aspects"]["synthetic-aspect"]["_source"]) / "contracts" / "preflight.md"
    pyproject = target / "pyproject.toml"
    entry = _make_entry(contract, [("pyproject.toml", pyproject.read_bytes(), "x")])
    pyproject.unlink()  # remove evidence
    _write_resolutions(target, {"synthetic-aspect/preflight": entry})
    report = replay(target, registry=registry)
    assert any(
        e.code == "missing-evidence" and e.path == "pyproject.toml"
        for e in report.errors
    )


# --- INV-resolutions-replay-deterministic ---


def test_replay_deterministic(tmp_path: Path) -> None:
    """Two replays of the same input produce identical reports."""
    target, registry = _build_synthetic_target(tmp_path)
    contract = Path(registry["aspects"]["synthetic-aspect"]["_source"]) / "contracts" / "preflight.md"
    pyproject = target / "pyproject.toml"
    entry = _make_entry(contract, [("pyproject.toml", pyproject.read_bytes(), "x")])
    _write_resolutions(target, {"synthetic-aspect/preflight": entry})
    r1 = replay(target, registry=registry)
    r2 = replay(target, registry=registry)
    assert r1.errors == r2.errors
    assert len(r1.executions) == len(r2.executions)
    for e1, e2 in zip(r1.executions, r2.executions):
        assert e1.invocation == e2.invocation
        assert e1.label == e2.label


# --- INV-resolutions-stale-fails: replay continues across contracts ---


def test_replay_continues_after_pin_failure(tmp_path: Path) -> None:
    """One stale contract doesn't prevent other contracts from being checked."""
    target, registry = _build_synthetic_target(tmp_path)
    aspect_root = Path(registry["aspects"]["synthetic-aspect"]["_source"])
    contract_a = aspect_root / "contracts" / "preflight.md"
    contract_b = aspect_root / "contracts" / "release.md"
    contract_b.write_text("# Release contract\n", encoding="utf-8")
    pyproject = target / "pyproject.toml"
    # Contract A: drift-the evidence.
    entry_a = _make_entry(contract_a, [("pyproject.toml", pyproject.read_bytes(), "x")])
    pyproject.write_text("drifted\n", encoding="utf-8")
    # Contract B: clean.
    other_evidence = target / "README.md"
    other_evidence.write_text("# README\n", encoding="utf-8")
    entry_b = _make_entry(contract_b, [("README.md", other_evidence.read_bytes(), "y")])
    _write_resolutions(
        target,
        {
            "synthetic-aspect/preflight": entry_a,
            "synthetic-aspect/release": entry_b,
        },
    )
    report = replay(target, registry=registry)
    assert any(e.contract == "synthetic-aspect/preflight" for e in report.errors)
    # Contract B should have produced an execution despite contract A's failure.
    assert any(
        x.contract == "synthetic-aspect/release" for x in report.executions
    ), f"contract B execution missing; report: {report}"


# --- stale_check vs replay ---


def test_stale_check_does_not_execute(tmp_path: Path) -> None:
    target, registry = _build_synthetic_target(tmp_path)
    contract = Path(registry["aspects"]["synthetic-aspect"]["_source"]) / "contracts" / "preflight.md"
    pyproject = target / "pyproject.toml"
    entry = _make_entry(contract, [("pyproject.toml", pyproject.read_bytes(), "x")])
    _write_resolutions(target, {"synthetic-aspect/preflight": entry})
    report = stale_check(target, registry=registry)
    assert report.ok
    assert report.executions == []  # stale_check skips execution path entirely


# --- Invocation-form validation ---


def test_replay_invalid_invocation_form_errors(tmp_path: Path) -> None:
    target, registry = _build_synthetic_target(tmp_path)
    contract = Path(registry["aspects"]["synthetic-aspect"]["_source"]) / "contracts" / "preflight.md"
    pyproject = target / "pyproject.toml"
    entry = _make_entry(
        contract,
        [("pyproject.toml", pyproject.read_bytes(), "x")],
        realized_by=[
            {"label": "lint", "invocation": "x", "invocation-form": "python-callable"}
        ],
    )
    _write_resolutions(target, {"synthetic-aspect/preflight": entry})
    report = replay(target, registry=registry)
    assert any(e.code == "invalid-invocation-form" for e in report.errors)


# --- Top-level shape errors ---


def test_replay_contracts_not_a_mapping_errors(tmp_path: Path) -> None:
    target, registry = _build_synthetic_target(tmp_path)
    rfile = target / ".kanon" / "resolutions.yaml"
    rfile.parent.mkdir(parents=True, exist_ok=True)
    rfile.write_text("schema-version: 1\ncontracts: 'not a dict'\n", encoding="utf-8")
    report = replay(target, registry=registry)
    assert any(e.code == "invalid-resolution-yaml" for e in report.errors)


def test_replay_contract_entry_not_a_mapping_errors(tmp_path: Path) -> None:
    target, registry = _build_synthetic_target(tmp_path)
    rfile = target / ".kanon" / "resolutions.yaml"
    rfile.parent.mkdir(parents=True, exist_ok=True)
    rfile.write_text(
        "schema-version: 1\ncontracts:\n  some-aspect/x: 'not a mapping'\n",
        encoding="utf-8",
    )
    report = replay(target, registry=registry)
    assert any(
        e.code == "invalid-resolution-yaml" and e.contract == "some-aspect/x"
        for e in report.errors
    )


# --- Dataclass smoke tests ---


def test_replay_report_ok_property() -> None:
    assert ReplayReport().ok is True
    rr = ReplayReport(errors=[ReplayError(code="x")])
    assert rr.ok is False


def test_execution_record_default_executed_false() -> None:
    rec = ExecutionRecord(contract="x/y", label="z", invocation="i", invocation_form="shell")
    assert rec.executed is False
