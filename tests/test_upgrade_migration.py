"""Tests for `kanon upgrade`'s built-in schema migration (per ADR-0054 §7
+ migrate-expanded plan, 2026-05-04).

Replaces tests/test_cli_migrate.py — the standalone `kanon migrate` verb
was retired (Option A: collapse to a single user-facing `upgrade` verb).
The schema-migration logic now lives in `_apply_v3_to_v4_migration()` in
_scaffold.py and is invoked by `upgrade` after `_migrate_legacy_config()`.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from kanon_core.cli import main


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
        "provenance": [
            {
                "recipe": "manual-migration",
                "publisher": "kanon-migrate",
                "recipe-version": "1.0",
                "applied_at": "2026-05-01T00:00:00+00:00",
            }
        ],
        "kit_version": "0.5.0a2",
        "aspects": {
            "kanon-sdd": {"depth": 1, "enabled_at": "2026-04-28T00:00:00+00:00", "config": {}},
        },
    }
    cfg_path = target / ".kanon" / "config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


# --- Schema migration via `upgrade` ---


def test_upgrade_v3_promotes_to_v4(tmp_path: Path) -> None:
    """A v3-shape config gains schema-version + kanon-dialect + provenance."""
    runner = CliRunner()
    _write_v3_config(tmp_path)
    result = runner.invoke(main, ["upgrade", str(tmp_path)])
    assert result.exit_code == 0, result.output
    cfg = yaml.safe_load((tmp_path / ".kanon" / "config.yaml").read_text(encoding="utf-8"))
    assert cfg["schema-version"] == 4
    assert cfg["kanon-dialect"] == "2026-05-01"
    assert isinstance(cfg["provenance"], list) and len(cfg["provenance"]) >= 1


def test_upgrade_strips_retired_testing_config_keys(tmp_path: Path) -> None:
    """The Phase A.4 retired keys under aspects.kanon-testing.config are stripped."""
    runner = CliRunner()
    _write_v3_config(tmp_path, with_testing_config=True)
    result = runner.invoke(main, ["upgrade", str(tmp_path)])
    assert result.exit_code == 0, result.output
    cfg = yaml.safe_load((tmp_path / ".kanon" / "config.yaml").read_text(encoding="utf-8"))
    testing_config = cfg["aspects"]["kanon-testing"]["config"]
    for retired in ("test_cmd", "lint_cmd", "typecheck_cmd", "format_cmd", "coverage_floor"):
        assert retired not in testing_config, f"retired key {retired!r} should be stripped"
    # Non-retired user keys must be preserved.
    assert testing_config.get("user_custom_key") == "preserved"


def test_upgrade_v4_config_is_idempotent(tmp_path: Path) -> None:
    """Running upgrade on an already-v4 config produces a stable post-state."""
    runner = CliRunner()
    _write_v4_config(tmp_path)
    result1 = runner.invoke(main, ["upgrade", str(tmp_path)])
    assert result1.exit_code == 0, result1.output
    cfg1 = (tmp_path / ".kanon" / "config.yaml").read_bytes()
    result2 = runner.invoke(main, ["upgrade", str(tmp_path)])
    assert result2.exit_code == 0, result2.output
    cfg2 = (tmp_path / ".kanon" / "config.yaml").read_bytes()
    assert cfg1 == cfg2, "second upgrade must not churn config"


def test_upgrade_idempotent_after_v3_promotion(tmp_path: Path) -> None:
    """v3 → v4 promotion runs once; second invocation is a no-op."""
    runner = CliRunner()
    _write_v3_config(tmp_path, with_testing_config=False)
    result1 = runner.invoke(main, ["upgrade", str(tmp_path)])
    assert result1.exit_code == 0, result1.output
    cfg1 = (tmp_path / ".kanon" / "config.yaml").read_bytes()
    result2 = runner.invoke(main, ["upgrade", str(tmp_path)])
    assert result2.exit_code == 0, result2.output
    cfg2 = (tmp_path / ".kanon" / "config.yaml").read_bytes()
    assert cfg1 == cfg2, "second upgrade must be a clean no-op"


# --- Forward-compat guards ---


def test_upgrade_rejects_future_schema_version(tmp_path: Path) -> None:
    """A v5+ config raises rather than mangling the file."""
    runner = CliRunner()
    cfg_path = tmp_path / ".kanon" / "config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        yaml.safe_dump({
            "schema-version": 5,
            "kit_version": "9.9.9",
            "aspects": {"kanon-sdd": {"depth": 1, "enabled_at": "2026-04-28T00:00:00+00:00", "config": {}}},
        }),
        encoding="utf-8",
    )
    result = runner.invoke(main, ["upgrade", str(tmp_path)])
    assert result.exit_code != 0
    assert "Unknown schema-version" in result.output


def test_upgrade_rejects_string_schema_version(tmp_path: Path) -> None:
    """A string schema-version raises a type error rather than silently parsing."""
    runner = CliRunner()
    cfg_path = tmp_path / ".kanon" / "config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        yaml.safe_dump({
            "schema-version": "5",
            "kit_version": "9.9.9",
            "aspects": {"kanon-sdd": {"depth": 1, "enabled_at": "2026-04-28T00:00:00+00:00", "config": {}}},
        }),
        encoding="utf-8",
    )
    result = runner.invoke(main, ["upgrade", str(tmp_path)])
    assert result.exit_code != 0
    assert "Unsupported schema-version type" in result.output


def test_upgrade_rejects_float_schema_version(tmp_path: Path) -> None:
    """A float schema-version raises a type error rather than int-coercing."""
    runner = CliRunner()
    cfg_path = tmp_path / ".kanon" / "config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        yaml.safe_dump({
            "schema-version": 5.0,
            "kit_version": "9.9.9",
            "aspects": {"kanon-sdd": {"depth": 1, "enabled_at": "2026-04-28T00:00:00+00:00", "config": {}}},
        }),
        encoding="utf-8",
    )
    result = runner.invoke(main, ["upgrade", str(tmp_path)])
    assert result.exit_code != 0
    assert "Unsupported schema-version type" in result.output


# --- Migrate verb is gone ---


def test_migrate_verb_no_longer_registered() -> None:
    """`kanon migrate` was removed in favour of `kanon upgrade` per ADR-0054 + the
    migrate-expanded plan (2026-05-04). This guard fires if anyone re-introduces
    the standalone verb."""
    assert "migrate" not in main.commands, (
        "kanon migrate was retired (Option A: single user-facing upgrade verb)"
    )


# --- Stale .kanon/protocols/<aspect>/ cleanup on upgrade ---


def test_upgrade_removes_stale_protocols_dir(tmp_path: Path) -> None:
    """If `.kanon/protocols/<aspect>/` exists for an aspect not in the current
    aspects: set, upgrade rmtree's the dir."""
    runner = CliRunner()
    _write_v3_config(tmp_path, with_testing_config=False)
    # Synthesise a stale protocols dir for an aspect NOT in the current config.
    stale = tmp_path / ".kanon" / "protocols" / "kanon-retired-aspect"
    stale.mkdir(parents=True)
    (stale / "some-protocol.md").write_text("# stale\n", encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert not stale.exists(), "stale protocols dir for retired aspect should be removed"


def test_upgrade_preserves_active_protocols_dir(tmp_path: Path) -> None:
    """A `.kanon/protocols/<aspect>/` dir for an active aspect must NOT be deleted."""
    runner = CliRunner()
    _write_v3_config(tmp_path, with_testing_config=False)
    active = tmp_path / ".kanon" / "protocols" / "kanon-sdd"
    active.mkdir(parents=True)
    (active / "kept-protocol.md").write_text("# kept\n", encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert active.is_dir(), "active aspect's protocols dir must be preserved"
