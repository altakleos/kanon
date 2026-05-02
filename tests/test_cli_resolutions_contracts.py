"""Phase A.7: tests for new CLI verbs `kanon resolutions check / explain`,
`kanon contracts validate`, and `kanon resolve` stub.

Per ADR-0039 / ADR-0041 designs.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from kanon.cli import main

# --- kanon resolutions check ---


def test_resolutions_check_missing_file_exits_zero(tmp_path: Path) -> None:
    target = tmp_path / "consumer"
    target.mkdir()
    runner = CliRunner()
    result = runner.invoke(main, ["resolutions", "check", "--target", str(target)])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "ok"
    assert parsed["errors"] == []


def test_resolutions_check_unknown_schema_exits_one(tmp_path: Path) -> None:
    target = tmp_path / "consumer"
    rdir = target / ".kanon"
    rdir.mkdir(parents=True)
    (rdir / "resolutions.yaml").write_text("schema-version: 99\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(main, ["resolutions", "check", "--target", str(target)])
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert parsed["status"] == "fail"
    assert any(e["code"] == "unknown-schema-version" for e in parsed["errors"])


# --- kanon resolutions explain (stub) ---


def test_resolutions_explain_emits_deferred_status(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main, ["resolutions", "explain", "kanon-x/preflight", "--target", str(tmp_path)]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "deferred"
    assert parsed["contract"] == "kanon-x/preflight"


# --- kanon contracts validate ---


def test_contracts_validate_missing_manifest_errors(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    runner = CliRunner()
    result = runner.invoke(main, ["contracts", "validate", str(bundle)])
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert parsed["status"] == "fail"
    assert any(e["code"] == "missing-manifest" for e in parsed["errors"])
    # Per plan v040a3-p2-fixes AC3: missing-manifest branch carries
    # `dialect: null` and `contracts: []` for schema parity with the
    # success path so consumers don't have to special-case the failure shape.
    assert parsed["dialect"] is None
    assert parsed["contracts"] == []


def test_contracts_validate_missing_dialect_pin_errors(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "manifest.yaml").write_text(
        yaml.safe_dump({"contracts": []}), encoding="utf-8"
    )
    runner = CliRunner()
    result = runner.invoke(main, ["contracts", "validate", str(bundle)])
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    # Per docs/specs/dialect-grammar.md INV 1: missing pin → `code: missing-dialect-pin`.
    assert any(e["code"] == "missing-dialect-pin" for e in parsed["errors"])


def test_contracts_validate_clean_empty_bundle_ok(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "kanon-dialect": "2026-05-01",
                "contracts": [],
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["contracts", "validate", str(bundle)])
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert parsed["status"] == "ok"


def test_contracts_validate_missing_realization_shape_errors(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "kanon-dialect": "2026-05-01",
                "contracts": [
                    {
                        "contract-id": "kanon-x/preflight",
                        "surface": "preflight.commit",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["contracts", "validate", str(bundle)])
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert any(e["code"] == "missing-realization-shape" for e in parsed["errors"])


def test_contracts_validate_invalid_realization_shape_errors(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "kanon-dialect": "2026-05-01",
                "contracts": [
                    {
                        "contract-id": "kanon-x/preflight",
                        "surface": "preflight.commit",
                        "realization-shape": {
                            "verbs": ["bogus-verb"],
                            "evidence-kinds": [],
                            "stages": [],
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["contracts", "validate", str(bundle)])
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert any(e["code"] == "invalid-realization-shape" for e in parsed["errors"])


def test_contracts_validate_composition_cycle_errors(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "kanon-dialect": "2026-05-01",
                "contracts": [
                    {
                        "contract-id": "kanon-x/a",
                        "surface": "preflight.commit",
                        "before": ["kanon-x/b"],
                        "realization-shape": {
                            "verbs": [],
                            "evidence-kinds": [],
                            "stages": [],
                        },
                    },
                    {
                        "contract-id": "kanon-x/b",
                        "surface": "preflight.commit",
                        "before": ["kanon-x/a"],
                        "realization-shape": {
                            "verbs": [],
                            "evidence-kinds": [],
                            "stages": [],
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["contracts", "validate", str(bundle)])
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert any(e["code"] == "composition-cycle" for e in parsed["errors"])


# --- kanon resolve (stub) ---


def test_resolve_emits_deferred_status(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["resolve", "--target", str(tmp_path)])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "deferred"


def test_resolve_with_contracts_flag_records_request(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main, ["resolve", "--target", str(tmp_path), "--contracts", "x/a, x/b"]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["contracts_requested"] == ["x/a", "x/b"]


# --- Smoke: verbs surface in --help ---


def test_resolutions_group_in_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert "resolutions" in result.output
    assert "contracts" in result.output
    assert "resolve" in result.output


def test_resolutions_subcommands_in_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["resolutions", "--help"])
    assert "check" in result.output
    assert "explain" in result.output
