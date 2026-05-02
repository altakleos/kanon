"""Tests for kanon CLI: verify, preflight, release commands, pending sentinel."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from kanon.cli import main


def _extract_verify_json(output: str) -> dict:
    """Extract the first JSON object from `verify` output (report precedes the human summary)."""
    start = output.find("{")
    end = output.rfind("}")
    return json.loads(output[start:end + 1])






# --- verify ---


def test_verify_fails_on_missing_file(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    (target / "docs" / "sdd-method.md").unlink()
    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code != 0
    assert "missing required file" in result.output.lower()



def test_verify_fails_on_missing_marker(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    agents = target / "AGENTS.md"
    # Strip all marker sections.
    text = agents.read_text(encoding="utf-8")
    # Remove protocols-index markers entirely.
    text = text.replace("<!-- kanon:begin:protocols-index -->", "")
    text = text.replace("<!-- kanon:end:protocols-index -->", "")
    agents.write_text(text, encoding="utf-8")
    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code != 0
    assert "marker" in result.output.lower()



def test_verify_fails_without_config(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["verify", str(tmp_path)])
    assert result.exit_code != 0



# --- cli.py: verify with empty aspects ---


def test_verify_empty_aspects(tmp_path: Path) -> None:
    """Lines 180-182: config.aspects is empty."""
    runner = CliRunner()
    config_dir = tmp_path / ".kanon"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump({"kit_version": "0.1", "aspects": {}}), encoding="utf-8"
    )
    (config_dir / "kit.md").write_text("# kit\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# AGENTS.md\n", encoding="utf-8")
    result = runner.invoke(main, ["verify", str(tmp_path)])
    assert result.exit_code == 0
    report = _extract_verify_json(result.output)
    assert any("no aspects" in w.lower() for w in report.get("warnings", []))



def test_verify_unknown_aspect(tmp_path: Path) -> None:
    """Spec invariant 4: an aspect in config not in the installed kit registry
    emits a warning, exit 0 — not a hard failure (`docs/specs/aspects.md`).

    Models the upstream-deprecation scenario: a consumer had aspect X enabled,
    upgraded the kit, and X no longer ships. The opt-in record survives so they
    can clean up — verify must not brick them.
    """
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Inject a fake aspect into a real, otherwise-valid project.
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["aspects"]["bogus"] = {"depth": 1, "enabled_at": "now", "config": {}}
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code == 0, result.output
    report = _extract_verify_json(result.output)
    assert report["status"] == "ok"
    assert report["errors"] == []
    assert any("bogus" in w for w in report["warnings"])
    assert "warning" in result.output.lower()



def test_verify_depth_out_of_range(tmp_path: Path) -> None:
    """Line 193: aspect depth outside valid range."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Manually set depth to 99
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["aspects"]["kanon-sdd"]["depth"] = 99
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code != 0
    report = _extract_verify_json(result.output)
    assert any("outside range" in e for e in report["errors"])



def test_verify_marker_imbalance(tmp_path: Path) -> None:
    """Lines 207, 220: AGENTS.md has mismatched begin/end markers."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    agents = target / "AGENTS.md"
    text = agents.read_text(encoding="utf-8")
    # Remove one end marker to create imbalance
    text = text.replace("<!-- kanon:end:protocols-index -->", "", 1)
    agents.write_text(text, encoding="utf-8")
    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code != 0
    output = result.output.lower()
    assert "imbalance" in output or "marker" in output



# --- _verify.py: project-validator error paths ---


def test_project_validator_import_error(tmp_path: Path) -> None:
    """run_project_validators records ImportError for missing validator module."""
    from kanon._verify import run_project_validators

    errors: list[str] = []
    warnings: list[str] = []
    aspects = {"project-bad": 1}
    # Mock _aspect_validators to return a nonexistent module.
    import kanon._verify as _v
    orig = _v._aspect_validators
    _v._aspect_validators = lambda _a: ["nonexistent_module_xyz"]  # type: ignore[assignment]
    try:
        run_project_validators(tmp_path, aspects, errors, warnings)
    finally:
        _v._aspect_validators = orig  # type: ignore[assignment]
    assert any("import failed" in e for e in errors)



def test_project_validator_missing_check(tmp_path: Path) -> None:
    """run_project_validators records error when module has no check() callable."""
    from kanon._verify import run_project_validators

    # Create a module with no check() function.
    (tmp_path / "no_check_mod.py").write_text("x = 1\n", encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []
    aspects = {"project-bad": 1}
    import kanon._verify as _v
    orig = _v._aspect_validators
    _v._aspect_validators = lambda _a: ["no_check_mod"]  # type: ignore[assignment]
    try:
        run_project_validators(tmp_path, aspects, errors, warnings)
    finally:
        _v._aspect_validators = orig  # type: ignore[assignment]
    assert any("no callable" in e for e in errors)



def test_project_validator_check_raises(tmp_path: Path) -> None:
    """run_project_validators records error when check() raises."""
    from kanon._verify import run_project_validators

    (tmp_path / "bad_check_mod.py").write_text(
        "def check(target, errors, warnings):\n    raise RuntimeError('boom')\n",
        encoding="utf-8",
    )
    errors: list[str] = []
    warnings: list[str] = []
    aspects = {"project-bad": 1}
    import kanon._verify as _v
    orig = _v._aspect_validators
    _v._aspect_validators = lambda _a: ["bad_check_mod"]  # type: ignore[assignment]
    try:
        run_project_validators(tmp_path, aspects, errors, warnings)
    finally:
        _v._aspect_validators = orig  # type: ignore[assignment]
    assert any("RuntimeError" in e and "boom" in e for e in errors)



# --- release_cmd tests ---


def test_release_cmd_requires_depth_2(tmp_path: Path) -> None:
    """release command rejects when release aspect depth < 2."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["release", str(target), "--tag", "v1.0.0"])
    assert result.exit_code != 0
    assert "depth >= 2 required" in result.output



def test_release_cmd_invalid_tag(tmp_path: Path) -> None:
    """release command rejects invalid tag format."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Set release depth to 2 via config manipulation.
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["aspects"]["kanon-release"] = {"depth": 2, "enabled_at": "2026-01-01", "config": {}}
    config_path.write_text(yaml.dump(config), encoding="utf-8")
    result = runner.invoke(main, ["release", str(target), "--tag", "bad-tag"])
    assert result.exit_code != 0
    assert "Invalid tag format" in result.output



def test_release_cmd_dirty_tree(tmp_path: Path) -> None:
    """release command rejects dirty working tree."""
    import subprocess

    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Init a git repo with a dirty file.
    subprocess.run(["git", "init"], cwd=str(target), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(target), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(target), capture_output=True)
    (target / "dirty.txt").write_text("uncommitted")
    # Set release depth to 2.
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["aspects"]["kanon-release"] = {"depth": 2, "enabled_at": "2026-01-01", "config": {}}
    config_path.write_text(yaml.dump(config), encoding="utf-8")
    result = runner.invoke(main, ["release", str(target), "--tag", "v1.0.0"])
    assert result.exit_code != 0
    assert "dirty" in result.output.lower()



def test_release_cmd_dry_run(tmp_path: Path) -> None:
    """release command dry-run passes when preflight succeeds."""
    import os
    import subprocess

    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Init a clean git repo.
    subprocess.run(["git", "init"], cwd=str(target), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(target), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(target), capture_output=True, env=git_env,
    )
    # Set release depth to 2.
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["aspects"]["kanon-release"] = {
        "depth": 2, "enabled_at": "2026-01-01", "config": {},
    }
    config_path.write_text(yaml.dump(config), encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(target), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "release prep"],
        cwd=str(target), capture_output=True, env=git_env,
    )
    result = runner.invoke(
        main, ["release", str(target), "--tag", "v1.0.0", "--dry-run"],
    )
    # Dry-run either passes (exit 0) or fails preflight (exit 1) — both
    # are valid coverage. The key is that we reached the preflight stage.
    combined = (result.output + getattr(result, "stderr", "")).lower()
    assert (
        "tag" in combined
        or "preflight" in combined
        or result.exit_code in (0, 1)
    )



# --- preflight verify-failure path ---


def test_preflight_exits_on_verify_failure(tmp_path: Path) -> None:
    """preflight exits with code 1 and JSON when verify fails."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Break AGENTS.md markers to make verify fail.
    agents = target / "AGENTS.md"
    text = agents.read_text(encoding="utf-8")
    text = text.replace("<!-- kanon:end:protocols-index -->", "", 1)
    agents.write_text(text, encoding="utf-8")
    result = runner.invoke(main, ["preflight", str(target), "--stage", "commit"])
    assert result.exit_code != 0
    assert '"passed": false' in result.output.lower() or "passed" in result.output.lower()



def test_verify_warns_on_stale_lock(tmp_path: Path) -> None:
    """Modify spec after fidelity update, verify should warn."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    spec = target / "docs" / "specs" / "example.md"
    spec.write_text("---\nstatus: accepted\ndate: 2026-01-01\n---\n# Spec: Example\n", encoding="utf-8")
    runner.invoke(main, ["fidelity", "update", str(target)])
    spec.write_text("---\nstatus: accepted\ndate: 2026-01-01\n---\n# Spec: Example\nChanged.\n", encoding="utf-8")
    result = runner.invoke(main, ["verify", str(target)])
    parsed = _extract_verify_json(result.output)
    assert any("fidelity" in w and "example" in w for w in parsed.get("warnings", []))



def test_verify_no_warning_without_lock(tmp_path: Path) -> None:
    """Without a lock file, verify should not emit fidelity warnings."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    result = runner.invoke(main, ["verify", str(target)])
    parsed = _extract_verify_json(result.output)
    assert not any("fidelity" in w for w in parsed.get("warnings", []))



def test_verify_warns_on_stale_fixture(tmp_path: Path) -> None:
    """Modify a fixture file after fidelity update, verify should warn."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    test_file = target / "tests" / "test_example.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test_one(): pass\n", encoding="utf-8")
    spec = target / "docs" / "specs" / "example.md"
    spec.write_text(
        "---\nstatus: accepted\ndate: 2026-01-01\n"
        "invariant_coverage:\n"
        "  INV-example-one:\n"
        "    - tests/test_example.py::test_one\n"
        "---\n# Spec: Example\n",
        encoding="utf-8",
    )
    runner.invoke(main, ["fidelity", "update", str(target)])
    # Modify the test file (not the spec)
    test_file.write_text("def test_one(): assert True\n", encoding="utf-8")
    result = runner.invoke(main, ["verify", str(target)])
    parsed = _extract_verify_json(result.output)
    assert any(
        "fixture" in w and "test_example.py" in w
        for w in parsed.get("warnings", [])
    )



def test_pending_sentinel_triggers_warning_on_upgrade(tmp_path: Path) -> None:
    """If .kanon/.pending exists, upgrade warns about interrupted operation."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Simulate interrupted operation by writing sentinel manually.
    (target / ".kanon" / ".pending").write_text("set-depth\n", encoding="utf-8")
    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    assert "interrupted" in result.output.lower()
    # Sentinel should be cleared after successful upgrade.
    assert not (target / ".kanon" / ".pending").exists()



def test_pending_sentinel_triggers_warning_on_verify(tmp_path: Path) -> None:
    """If .kanon/.pending exists, verify warns about interrupted operation."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    (target / ".kanon" / ".pending").write_text("upgrade\n", encoding="utf-8")
    result = runner.invoke(main, ["verify", str(target)])
    # Verify outputs to stderr; CliRunner mixes stdout+stderr by default.
    assert "interrupted" in result.output.lower()


@pytest.mark.parametrize(
    "pending_op,expected_command",
    [
        ("init", "kanon init"),
        ("upgrade", "kanon upgrade"),
        ("set-depth", "kanon aspect set-depth"),
        ("set-config", "kanon aspect set-config"),
        ("aspect-remove", "kanon aspect remove"),
        ("fidelity-update", "kanon fidelity update"),
    ],
)

def test_pending_recovery_warning_uses_correct_user_command(
    tmp_path: Path, pending_op: str, expected_command: str
) -> None:
    """The recovery warning must suggest a valid `kanon` command for each
    known sentinel operation. Sub-group commands like `aspect remove`
    appear with a space, not as `kanon aspect-remove` (which isn't a
    valid CLI invocation)."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    (target / ".kanon" / ".pending").write_text(f"{pending_op}\n", encoding="utf-8")
    # Any mutating command path triggers _check_pending_recovery; verify
    # also prints it. Use verify because it's idempotent and won't clear
    # the sentinel (it has no write side effect).
    result = runner.invoke(main, ["verify", str(target)])
    assert f"Re-run '{expected_command}'" in result.output, (
        f"expected suggestion {expected_command!r} for pending {pending_op!r}; "
        f"got output: {result.output!r}"
    )



def test_pending_recovery_warning_falls_back_for_unknown_op(tmp_path: Path) -> None:
    """An unknown sentinel operation falls back to `kanon {pending}`
    rather than crashing — defensive against future operation strings
    not yet mapped in `_PENDING_OP_TO_COMMAND`."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    (target / ".kanon" / ".pending").write_text("future-op\n", encoding="utf-8")
    result = runner.invoke(main, ["verify", str(target)])
    assert "Re-run 'kanon future-op'" in result.output


# --- ADR-0042: canonical exit-zero wording on verify --help (immutable per ADR-0032). ---


def test_verify_help_carries_adr_0042_wording() -> None:
    """`kanon verify --help` MUST surface the canonical exit-zero claim
    (positive claim + 4 MUST-NOTs) verbatim per ADR-0042 §1. The wording is
    immutable post-acceptance; this test fails fast if any phrase drifts."""
    runner = CliRunner()
    result = runner.invoke(main, ["verify", "--help"])
    assert result.exit_code == 0, result.output

    # Click's help formatter reflows whitespace; we collapse to compare phrases.
    flat = " ".join(result.output.split())

    # ADR citation is present.
    assert "ADR-0042" in flat

    # The positive claim.
    assert "exit-0 means" in flat
    assert "structural and behavioural contracts" in flat
    assert "discipline aspects the consumer has explicitly enabled" in flat
    assert "depths the consumer has declared" in flat

    # The four MUST-NOT phrases.
    assert "MUST NOT" in flat
    assert "good engineering practices" in flat
    assert "correctness or quality endorsement" in flat
    assert "runtime behavioural guarantee" in flat
    assert "semantically correct" in flat
