"""Tests for `kanon aspect set-config` and `kanon aspect add --config`.

Covers all 10 invariants in `docs/specs/aspect-config.md` plus the manifest-load
validation of `config-schema:` blocks.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from kanon_core._cli_helpers import _parse_config_pair
from kanon_core.cli import main


def _init_with(runner: CliRunner, target: Path, *aspects: str) -> None:
    """Helper: scaffold a fresh project with the given aspect-depth pairs."""
    spec = ",".join(aspects)
    result = runner.invoke(main, ["init", str(target), "--aspects", spec])
    assert result.exit_code == 0, result.output


def _config(target: Path) -> dict:
    return yaml.safe_load((target / ".kanon" / "config.yaml").read_text())


# --- INV-aspect-config-set-config-command (idempotency, refresh enabled_at) ---


def test_set_config_idempotent_apart_from_timestamp(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "p"
    _init_with(runner, target, "sdd:1", "testing:3")

    r1 = runner.invoke(main, ["aspect", "set-config", str(target), "kanon-testing", "coverage_floor=80"])
    assert r1.exit_code == 0, r1.output
    cfg1 = _config(target)
    coverage1 = cfg1["aspects"]["kanon-testing"]["config"]["coverage_floor"]
    assert coverage1 == 80

    r2 = runner.invoke(main, ["aspect", "set-config", str(target), "kanon-testing", "coverage_floor=80"])
    assert r2.exit_code == 0, r2.output
    cfg2 = _config(target)
    coverage2 = cfg2["aspects"]["kanon-testing"]["config"]["coverage_floor"]
    assert coverage2 == 80
    # Spec INV-1: idempotent — value unchanged. enabled_at refresh on noop is OK.


# --- INV-aspect-config-add-config-flag ---


def test_aspect_add_config_flag_populates_config_at_enable_time(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "p"
    _init_with(runner, target, "sdd:1")

    result = runner.invoke(
        main,
        ["aspect", "add", str(target), "kanon-testing", "--depth", "3", "--config", "coverage_floor=85"],
    )
    assert result.exit_code == 0, result.output
    cfg = _config(target)
    assert cfg["aspects"]["kanon-testing"]["config"]["coverage_floor"] == 85


def test_aspect_add_config_flag_repeatable(tmp_path: Path) -> None:
    """Multiple --config occurrences accumulate; last write wins for shared keys."""
    runner = CliRunner()
    target = tmp_path / "p"
    _init_with(runner, target, "sdd:1")

    # `worktrees` has no config-schema today — schema-free aspects accept any key (INV-6).
    result = runner.invoke(
        main,
        [
            "aspect", "add", str(target), "kanon-worktrees", "--depth", "1",
            "--config", "alpha=1",
            "--config", "beta=foo",
        ],
    )
    assert result.exit_code == 0, result.output
    cfg_block = _config(target)["aspects"]["kanon-worktrees"]["config"]
    assert cfg_block == {"alpha": 1, "beta": "foo"}


# --- INV-aspect-config-yaml-scalar-parsing ---


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("flag=true", ("flag", True)),
        ("n=42", ("n", 42)),
        ("name=foo", ("name", "foo")),
        ('pin="==1.2"', ("pin", "==1.2")),
        ("pi=3.14", ("pi", 3.14)),
        ("blank=", ("blank", None)),  # YAML scalar: empty → None
    ],
)
def test_parse_config_pair_yaml_scalar(raw: str, expected: tuple) -> None:
    assert _parse_config_pair(raw, schema=None) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "xs=[1,2,3]",
        "m={a: 1}",
    ],
)
def test_parse_config_pair_rejects_lists_and_mappings(raw: str) -> None:
    import click

    with pytest.raises(click.ClickException) as exc:
        _parse_config_pair(raw, schema=None)
    assert "lists and mappings" in str(exc.value.message)


# --- INV-aspect-config-key-format ---


@pytest.mark.parametrize(
    "raw",
    [
        "Foo=1",       # uppercase
        "1foo=1",      # leading digit
        "foo bar=1",   # space
        "=1",          # empty
        "_foo=1",      # leading underscore
    ],
)
def test_parse_config_pair_rejects_bad_keys(raw: str) -> None:
    import click

    with pytest.raises(click.ClickException) as exc:
        _parse_config_pair(raw, schema=None)
    assert "Invalid config key" in str(exc.value.message)


# --- INV-aspect-config-schema-validation (unknown keys, type mismatch) ---


# Phase A.4: 3 schema-validation tests (test_set_config_rejects_unknown_key_against_schema,
# test_set_config_rejects_type_mismatch_against_schema, test_set_config_rejects_bool_for_integer_schema)
# retired — they exercised the generic config-schema validator against kanon-testing's
# (now-deleted) config-schema. The validation mechanism in `_aspect_config_schema` /
# set-config remains; future coverage can be added via a project-aspect or `acme-`
# publisher fixture that declares its own schema.


# --- INV-aspect-config-schema-optional ---


def test_set_config_accepts_any_key_when_no_schema(tmp_path: Path) -> None:
    """`worktrees` has no config-schema declared today."""
    runner = CliRunner()
    target = tmp_path / "p"
    _init_with(runner, target, "sdd:1", "worktrees:1")

    result = runner.invoke(
        main, ["aspect", "set-config", str(target), "kanon-worktrees", "anything=42"]
    )
    assert result.exit_code == 0, result.output
    cfg = _config(target)
    assert cfg["aspects"]["kanon-worktrees"]["config"]["anything"] == 42


# --- INV-aspect-config-config-schema-shape (manifest validation) ---


def test_malformed_config_schema_rejected_at_manifest_load(tmp_path: Path) -> None:
    """A schema entry missing `type:` raises a clear error from `_load_aspect_manifest`."""
    import click

    from kanon_core._manifest import _validate_config_schema

    bad = {"key1": {"description": "no type"}}
    with pytest.raises(click.ClickException) as exc:
        _validate_config_schema(tmp_path / "fake.yaml", bad)
    assert "missing required field 'type'" in str(exc.value.message)


def test_malformed_config_schema_invalid_type_rejected(tmp_path: Path) -> None:
    import click

    from kanon_core._manifest import _validate_config_schema

    bad = {"key1": {"type": "tuple"}}
    with pytest.raises(click.ClickException) as exc:
        _validate_config_schema(tmp_path / "fake.yaml", bad)
    assert "is invalid" in str(exc.value.message)


def test_malformed_config_schema_unknown_field_rejected(tmp_path: Path) -> None:
    import click

    from kanon_core._manifest import _validate_config_schema

    bad = {"key1": {"type": "string", "min": 0}}
    with pytest.raises(click.ClickException) as exc:
        _validate_config_schema(tmp_path / "fake.yaml", bad)
    assert "unknown field" in str(exc.value.message)


# --- INV-aspect-config-atomic-write ---


def test_set_config_clears_sentinel_on_success(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "p"
    _init_with(runner, target, "sdd:1", "testing:3")

    pending = target / ".kanon" / ".pending"
    assert not pending.exists()

    runner.invoke(main, ["aspect", "set-config", str(target), "kanon-testing", "coverage_floor=90"])
    assert not pending.exists()


def test_set_config_persists_sentinel_on_mid_write_failure(tmp_path: Path) -> None:
    """If the underlying _write_config raises, the sentinel must persist."""
    runner = CliRunner()
    target = tmp_path / "p"
    _init_with(runner, target, "sdd:1", "testing:3")

    pending = target / ".kanon" / ".pending"

    # Patch _write_config to raise after the sentinel write but before clear.
    with patch("kanon_core._cli_aspect._write_config", side_effect=OSError("simulated disk full")):
        runner.invoke(
            main, ["aspect", "set-config", str(target), "kanon-testing", "coverage_floor=90"]
        )
    assert pending.is_file()
    assert pending.read_text(encoding="utf-8").strip() == "set-config"


# --- INV-aspect-config-info-surfaces-schema ---


# Phase A.4: test_aspect_info_renders_schema_when_declared retired — kanon-testing's
# config-schema deleted. The `aspect info` rendering mechanism survives and renders
# `Config keys:` for any aspect that does declare a schema.


def test_aspect_info_omits_config_block_when_no_schema() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["aspect", "info", "kanon-worktrees"])
    assert result.exit_code == 0, result.output
    assert "Config keys:" not in result.output


# --- INV-aspect-config-error-aspect-not-enabled ---


def test_set_config_errors_when_aspect_not_enabled(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "p"
    _init_with(runner, target, "sdd:1")  # testing not enabled

    result = runner.invoke(
        main, ["aspect", "set-config", str(target), "kanon-testing", "coverage_floor=85"]
    )
    assert result.exit_code != 0
    assert "is not enabled" in result.output
    assert "kanon aspect add" in result.output


# --- T9: testing aspect's config-schema round-trips against on-disk YAML ---


# Phase A.4: test_testing_config_schema_round_trips retired — kanon-testing's
# config-schema deleted from both LOADER MANIFEST and YAML; round-trip is moot.


# --- _manifest.py coverage: _discover_project_aspects error paths ---


def test_discover_project_aspects_skips_hidden_dirs(tmp_path: Path) -> None:
    """Hidden directories (starting with '.') under .kanon/aspects/ are skipped."""
    from kanon_core._manifest import _discover_project_aspects

    aspects_dir = tmp_path / ".kanon" / "aspects"
    (aspects_dir / ".hidden-dir").mkdir(parents=True)
    (aspects_dir / ".hidden-dir" / "manifest.yaml").write_text(
        "stability: experimental\ndepth-range: [0, 1]\ndefault-depth: 1\n"
    )
    result = _discover_project_aspects(tmp_path)
    assert result == {}


def test_discover_project_aspects_missing_manifest_error(tmp_path: Path) -> None:
    """A project-aspect directory without manifest.yaml raises ClickException."""
    import click

    from kanon_core._manifest import _discover_project_aspects

    (tmp_path / ".kanon" / "aspects" / "project-nofile").mkdir(parents=True)
    with pytest.raises(click.ClickException, match="missing manifest.yaml"):
        _discover_project_aspects(tmp_path)


def test_discover_project_aspects_kanon_prefix_rejected(tmp_path: Path) -> None:
    """A kanon-* directory under .kanon/aspects/ is rejected (namespace ownership)."""
    import click

    from kanon_core._manifest import _discover_project_aspects

    d = tmp_path / ".kanon" / "aspects" / "kanon-bad"
    d.mkdir(parents=True)
    (d / "manifest.yaml").write_text("stability: experimental\n")
    with pytest.raises(click.ClickException, match="namespace ownership"):
        _discover_project_aspects(tmp_path)


def test_discover_project_aspects_invalid_depth_range(tmp_path: Path) -> None:
    """A project-aspect with a non-list depth-range raises ClickException."""
    import click

    from kanon_core._manifest import _discover_project_aspects

    d = tmp_path / ".kanon" / "aspects" / "project-bad"
    d.mkdir(parents=True)
    (d / "manifest.yaml").write_text(
        "stability: experimental\ndepth-range: 3\ndefault-depth: 1\n"
    )
    with pytest.raises(click.ClickException, match="depth-range must be"):
        _discover_project_aspects(tmp_path)


def test_discover_project_aspects_invalid_stability(tmp_path: Path) -> None:
    """A project-aspect with an invalid stability value raises ClickException."""
    import click

    from kanon_core._manifest import _discover_project_aspects

    d = tmp_path / ".kanon" / "aspects" / "project-bad"
    d.mkdir(parents=True)
    (d / "manifest.yaml").write_text(
        "stability: alpha\ndepth-range: [0, 1]\ndefault-depth: 1\n"
    )
    with pytest.raises(click.ClickException, match="invalid stability"):
        _discover_project_aspects(tmp_path)


def test_discover_project_aspects_missing_required_field(tmp_path: Path) -> None:
    """A project-aspect missing a required field raises ClickException."""
    import click

    from kanon_core._manifest import _discover_project_aspects

    d = tmp_path / ".kanon" / "aspects" / "project-bad"
    d.mkdir(parents=True)
    (d / "manifest.yaml").write_text("stability: experimental\ndefault-depth: 1\n")
    with pytest.raises(click.ClickException, match="missing required field"):
        _discover_project_aspects(tmp_path)


# --- _manifest.py coverage: _validate_config_schema error paths ---


def test_validate_config_schema_non_dict_rejected(tmp_path: Path) -> None:
    """A non-dict config-schema raises ClickException."""
    import click

    from kanon_core._manifest import _validate_config_schema

    with pytest.raises(click.ClickException, match="must be a mapping"):
        _validate_config_schema(tmp_path / "fake.yaml", ["not", "a", "dict"])


def test_validate_config_schema_non_string_key_rejected(tmp_path: Path) -> None:
    """A non-string key in config-schema raises ClickException."""
    import click

    from kanon_core._manifest import _validate_config_schema

    with pytest.raises(click.ClickException, match="must be a non-empty string"):
        _validate_config_schema(tmp_path / "fake.yaml", {42: {"type": "integer"}})


def test_validate_config_schema_non_dict_descriptor_rejected(tmp_path: Path) -> None:
    """A non-dict descriptor in config-schema raises ClickException."""
    import click

    from kanon_core._manifest import _validate_config_schema

    with pytest.raises(click.ClickException, match="must be a mapping"):
        _validate_config_schema(tmp_path / "fake.yaml", {"key1": "not-a-dict"})


# --- _manifest.py coverage: _validate_validators_field error paths ---


def test_validate_validators_non_list_rejected(tmp_path: Path) -> None:
    """A non-list validators field raises ClickException."""
    import click

    from kanon_core._manifest import _validate_validators_field

    with pytest.raises(click.ClickException, match="must be a list"):
        _validate_validators_field(tmp_path / "fake.yaml", "not-a-list")


def test_validate_validators_non_string_entry_rejected(tmp_path: Path) -> None:
    """A non-string entry in validators raises ClickException."""
    import click

    from kanon_core._manifest import _validate_validators_field

    with pytest.raises(click.ClickException, match="must be a string"):
        _validate_validators_field(tmp_path / "fake.yaml", [42])


def test_validate_validators_non_dotted_path_rejected(tmp_path: Path) -> None:
    """A non-dotted-path entry in validators raises ClickException."""
    import click

    from kanon_core._manifest import _validate_validators_field

    with pytest.raises(click.ClickException, match="not a valid dotted module path"):
        _validate_validators_field(tmp_path / "fake.yaml", ["not valid!"])


# --- _manifest.py coverage: _load_aspect_manifest error paths ---


def test_load_aspect_manifest_unknown_aspect_rejected() -> None:
    """An unknown aspect name raises ClickException."""
    import click

    from kanon_core._manifest import _load_aspect_manifest, _set_project_aspects_overlay

    _load_aspect_manifest.cache_clear()
    _set_project_aspects_overlay(None)
    try:
        with pytest.raises(click.ClickException, match="Unknown aspect"):
            _load_aspect_manifest("kanon-nonexistent-aspect-xyz")
    finally:
        _load_aspect_manifest.cache_clear()
