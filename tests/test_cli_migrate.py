"""Phase A.9: tests for `kanon migrate v0.3 → v0.4` (deprecated-on-arrival)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner
from kernel.cli import main


def _write_v3_config(target: Path, with_testing_config: bool = True) -> None:
    config: dict = {
        "kit_version": "0.3.1a2",
        "aspects": {
            "kanon-sdd": {"depth": 1, "enabled_at": "2026-04-28T00:00:00+00:00", "config": {}},
        },
    }
    if with_testing_config:
        config["aspects"]["kanon-testing"] = {
            "depth": 3,
            "enabled_at": "2026-04-28T00:00:00+00:00",
            "config": {
                "test_cmd": ".venv/bin/pytest -q",
                "lint_cmd": "ruff check .",
                "typecheck_cmd": "mypy src/",
                "format_cmd": "",
                "coverage_floor": 90,
                "user_custom_key": "preserved",
            },
        }
    cfg_path = target / ".kanon" / "config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


def _write_v4_config(target: Path) -> None:
    config = {
        "schema-version": 4,
        "kanon-dialect": "2026-05-01",
        "provenance": [],
        "kit_version": "0.3.1a2",
        "aspects": {},
    }
    cfg_path = target / ".kanon" / "config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


def test_migrate_already_v4_is_noop(tmp_path: Path) -> None:
    _write_v4_config(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["migrate", "--target", str(tmp_path)])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "noop"


def test_migrate_v3_adds_v4_fields(tmp_path: Path) -> None:
    _write_v3_config(tmp_path, with_testing_config=False)
    runner = CliRunner()
    result = runner.invoke(main, ["migrate", "--target", str(tmp_path)])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "written"
    cfg = yaml.safe_load((tmp_path / ".kanon" / "config.yaml").read_text())
    assert cfg["schema-version"] == 4
    assert cfg["kanon-dialect"] == "2026-05-01"
    assert isinstance(cfg["provenance"], list)
    assert cfg["provenance"][0]["recipe"] == "manual-migration"


def test_migrate_strips_retired_testing_config_keys(tmp_path: Path) -> None:
    _write_v3_config(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["migrate", "--target", str(tmp_path)])
    assert result.exit_code == 0, result.output
    cfg = yaml.safe_load((tmp_path / ".kanon" / "config.yaml").read_text())
    testing_cfg = cfg["aspects"]["kanon-testing"]["config"]
    for key in ("test_cmd", "lint_cmd", "typecheck_cmd", "format_cmd", "coverage_floor"):
        assert key not in testing_cfg, f"retired key {key} should be stripped"
    # Non-retired user keys preserved.
    assert testing_cfg.get("user_custom_key") == "preserved"


def test_migrate_dry_run_does_not_write(tmp_path: Path) -> None:
    _write_v3_config(tmp_path, with_testing_config=False)
    cfg_before = (tmp_path / ".kanon" / "config.yaml").read_bytes()
    runner = CliRunner()
    result = runner.invoke(main, ["migrate", "--target", str(tmp_path), "--dry-run"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "would-write"
    cfg_after = (tmp_path / ".kanon" / "config.yaml").read_bytes()
    assert cfg_before == cfg_after, "dry-run wrote to disk"


def test_migrate_emits_deprecation_banner(tmp_path: Path) -> None:
    _write_v3_config(tmp_path, with_testing_config=False)
    runner = CliRunner()
    result = runner.invoke(main, ["migrate", "--target", str(tmp_path)])
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert "deprecated-on-arrival" in parsed["deprecation"]


def test_migrate_missing_config_errors(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["migrate", "--target", str(tmp_path)])
    assert result.exit_code != 0
    assert "no .kanon/config.yaml" in result.output


def test_migrate_idempotent(tmp_path: Path) -> None:
    _write_v3_config(tmp_path, with_testing_config=False)
    runner = CliRunner()
    r1 = runner.invoke(main, ["migrate", "--target", str(tmp_path)])
    assert r1.exit_code == 0
    r2 = runner.invoke(main, ["migrate", "--target", str(tmp_path)])
    assert r2.exit_code == 0
    parsed = json.loads(r2.output)
    assert parsed["status"] == "noop"


def test_migrate_rejects_future_schema_version(tmp_path: Path) -> None:
    """A v5+ config is from a future kanon. migrate must refuse loudly rather
    than silently mangling the file (e.g., adding v4 fields beneath a v5
    schema header — a hybrid that no reader understands)."""
    config_dir = tmp_path / ".kanon"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "schema-version": 5,
                "kanon-dialect": "2027-01-01",
                "kit_version": "0.5.0",
                "aspects": {},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["migrate", "--target", str(tmp_path)])
    assert result.exit_code != 0, result.output
    assert "Unknown schema-version: 5" in result.output
    # File MUST NOT have been mutated.
    parsed = yaml.safe_load((config_dir / "config.yaml").read_text(encoding="utf-8"))
    assert parsed["schema-version"] == 5
    assert parsed["kanon-dialect"] == "2027-01-01"
    # Critically: no v4-shape `provenance:` injection happened.
    assert "provenance" not in parsed


# --- Plan v040a3-p2-fixes AC2: schema-version YAML quirks (string, float)
# must hit the same forward-version guard as integer-5. The prior guard used
# isinstance(int) which silently bypassed both bypass paths.


def test_migrate_rejects_string_schema_version(tmp_path: Path) -> None:
    """`schema-version: "5"` (quoted string in YAML) must be refused, not
    silently augmented with v4 fields beneath the v5 header."""
    config_dir = tmp_path / ".kanon"
    config_dir.mkdir()
    # Write the YAML literally so PyYAML keeps "5" as a string.
    (config_dir / "config.yaml").write_text(
        'schema-version: "5"\nkit_version: "0.5.0"\naspects: {}\n',
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["migrate", "--target", str(tmp_path)])
    assert result.exit_code != 0, result.output
    # Diagnostic surfaces the type mismatch.
    assert "schema-version" in result.output
    assert ("Unsupported" in result.output or "Unknown" in result.output)
    # File MUST NOT be mutated.
    parsed = yaml.safe_load((config_dir / "config.yaml").read_text(encoding="utf-8"))
    assert parsed["schema-version"] == "5"
    assert "kanon-dialect" not in parsed
    assert "provenance" not in parsed


def test_migrate_rejects_float_schema_version(tmp_path: Path) -> None:
    """`schema-version: 5.0` (YAML float) must be refused, not augmented."""
    config_dir = tmp_path / ".kanon"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        "schema-version: 5.0\nkit_version: \"0.5.0\"\naspects: {}\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["migrate", "--target", str(tmp_path)])
    assert result.exit_code != 0, result.output
    assert "schema-version" in result.output
    parsed = yaml.safe_load((config_dir / "config.yaml").read_text(encoding="utf-8"))
    assert parsed["schema-version"] == 5.0
    assert "kanon-dialect" not in parsed
    assert "provenance" not in parsed
