"""Tests for kanon preflight — staged local validation."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from kanon_core._preflight import _resolve_preflight_checks
from kanon_core.cli import main


def _init_project(tmp_path: Path, tier: int = 1) -> Path:
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", str(tier)])
    return target


def test_resolve_empty_config(tmp_path: Path) -> None:
    """No preflight-stages in config, no aspect preflight entries → empty list."""
    checks = _resolve_preflight_checks({}, {}, "commit")
    assert checks == []


def test_resolve_consumer_stages(tmp_path: Path) -> None:
    """Consumer preflight-stages are used when no aspects contribute."""
    config = {
        "preflight-stages": {
            "commit": [{"run": "echo lint", "label": "lint"}],
            "push": [{"run": "echo test", "label": "tests"}],
        }
    }
    commit_checks = _resolve_preflight_checks({}, config, "commit")
    assert len(commit_checks) == 1
    assert commit_checks[0]["label"] == "lint"

    push_checks = _resolve_preflight_checks({}, config, "push")
    assert len(push_checks) == 2  # commit + push (strict superset)
    assert push_checks[0]["label"] == "lint"
    assert push_checks[1]["label"] == "tests"


# Phase A.8: test_resolve_aspect_defaults retired — kanon-deps was the last
# aspect contributing a preflight block (per ADR-0048; A.8 retired all
# scaffolded-CI preflight blocks). The aspect-contributed-preflight mechanism
# in `_resolve_preflight_checks` still works; `acme-` publishers shipping
# their own preflight blocks would re-exercise it.


def test_consumer_overrides_aspect_default(tmp_path: Path) -> None:
    """Consumer entry with same label replaces aspect default."""
    target = _init_project(tmp_path)
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    config.setdefault("aspects", {}).setdefault("kanon-testing", {}).setdefault("config", {})
    config["aspects"]["kanon-testing"]["config"]["lint_cmd"] = "echo aspect-lint"
    config["aspects"]["kanon-testing"]["depth"] = 1
    config["preflight-stages"] = {
        "commit": [{"run": "echo consumer-lint", "label": "lint"}],
    }
    aspects = {a: d["depth"] for a, d in config["aspects"].items()}
    aspects["kanon-testing"] = 1

    checks = _resolve_preflight_checks(aspects, config, "commit")
    lint_checks = [c for c in checks if c["label"] == "lint"]
    assert len(lint_checks) == 1
    assert lint_checks[0]["run"] == "echo consumer-lint"


def test_empty_cmd_skipped(tmp_path: Path) -> None:
    """Empty config values result in skipped checks."""
    target = _init_project(tmp_path)
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    config.setdefault("aspects", {}).setdefault("kanon-testing", {}).setdefault("config", {})
    config["aspects"]["kanon-testing"]["config"]["lint_cmd"] = ""
    config["aspects"]["kanon-testing"]["config"]["test_cmd"] = ""
    config["aspects"]["kanon-testing"]["depth"] = 1
    aspects = {a: d["depth"] for a, d in config["aspects"].items()}
    aspects["kanon-testing"] = 1

    checks = _resolve_preflight_checks(aspects, config, "push")
    # All empty → no checks from testing
    testing_labels = [c["label"] for c in checks if c["label"] in ("lint", "tests", "typecheck", "format")]
    assert testing_labels == []


def test_preflight_cli_commit_stage(tmp_path: Path) -> None:
    """kanon preflight runs and produces JSON output."""
    target = _init_project(tmp_path)
    # Add a simple consumer check
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["preflight-stages"] = {
        "commit": [{"run": "echo ok", "label": "smoke"}],
    }
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))

    runner = CliRunner()
    result = runner.invoke(main, ["preflight", str(target)])
    assert result.exit_code == 0, result.output
    import json
    # CliRunner mixes stdout+stderr. Use raw_decode to parse just the first JSON object.
    report, _ = json.JSONDecoder().raw_decode(result.output)
    assert report["passed"] is True
    assert report["stage"] == "commit"
    labels = [c["label"] for c in report["checks"]]
    assert "verify" in labels
    assert "smoke" in labels


def test_preflight_cli_failing_check(tmp_path: Path) -> None:
    """A failing check causes non-zero exit."""
    target = _init_project(tmp_path)
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["preflight-stages"] = {
        "commit": [{"run": "exit 1", "label": "always-fail"}],
    }
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))

    runner = CliRunner()
    result = runner.invoke(main, ["preflight", str(target)])
    assert result.exit_code != 0


def test_preflight_release_requires_tag(tmp_path: Path) -> None:
    """--stage release without --tag is an error."""
    target = _init_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["preflight", str(target), "--stage", "release"])
    assert result.exit_code != 0
    assert "tag" in result.output.lower()


def test_preflight_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A check that times out is marked as failed (covers TimeoutExpired handler)."""
    import subprocess as _sp

    from kanon_core import _preflight

    target = _init_project(tmp_path)

    def _fake_run(*args, **kwargs):
        raise _sp.TimeoutExpired(cmd="sleep 999", timeout=120)

    monkeypatch.setattr(_preflight.subprocess, "run", _fake_run)

    checks = [{"run": "sleep 999", "label": "slow"}]
    all_passed, results = _preflight._run_preflight(target, checks, None, False)
    assert not all_passed
    assert results[0]["passed"] is False


def test_preflight_fail_fast(tmp_path: Path) -> None:
    """fail_fast=True stops after first failure (covers break on fail_fast)."""
    from kanon_core._preflight import _run_preflight

    target = _init_project(tmp_path)
    checks = [
        {"run": "exit 1", "label": "fail-first"},
        {"run": "echo ok", "label": "never-reached"},
    ]
    all_passed, results = _run_preflight(target, checks, None, True)
    assert not all_passed
    assert len(results) == 1
    assert results[0]["label"] == "fail-first"


def test_resolve_aspect_contributed_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aspect-contributed preflight checks are resolved (covers lines 37-43)."""
    from kanon_core import _preflight

    fake_manifest = {
        "depth-1": {
            "preflight": {
                "commit": [{"run": "echo aspect-check", "label": "aspect-lint"}],
            }
        }
    }
    monkeypatch.setattr(_preflight, "_load_aspect_manifest", lambda _a: fake_manifest)
    monkeypatch.setattr(_preflight, "_aspect_depth_range", lambda _a: (1, 2))

    aspects = {"acme-foo": 1}
    checks = _resolve_preflight_checks(aspects, {}, "commit")
    assert any(c["label"] == "aspect-lint" for c in checks)


def test_preflight_oserror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A check that raises OSError is marked as failed (covers OSError handler)."""
    import subprocess as _sp

    from kanon_core._preflight import _run_preflight

    target = _init_project(tmp_path)

    def _fake_run(*args, **kwargs):
        raise OSError("No such file or directory")

    monkeypatch.setattr(_sp, "run", _fake_run)

    checks = [{"run": "/nonexistent/binary", "label": "bad-cmd"}]
    all_passed, results = _run_preflight(target, checks, None, False)
    assert not all_passed
    assert results[0]["passed"] is False


def test_resolve_aspect_invalid_stage_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aspect preflight with invalid stage name is skipped (covers line 38)."""
    from kanon_core import _preflight

    fake_manifest = {
        "depth-1": {
            "preflight": {
                "invalid-stage": [{"run": "echo bad", "label": "bad"}],
            }
        }
    }
    monkeypatch.setattr(_preflight, "_load_aspect_manifest", lambda _a: fake_manifest)
    monkeypatch.setattr(_preflight, "_aspect_depth_range", lambda _a: (1, 2))

    checks = _resolve_preflight_checks({"acme-x": 1}, {}, "commit")
    assert checks == []


def test_resolve_aspect_unresolved_placeholder_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aspect preflight with unresolved placeholder is skipped (covers line 42)."""
    from kanon_core import _preflight

    fake_manifest = {
        "depth-1": {
            "preflight": {
                "commit": [{"run": "${undefined_var} check", "label": "unresolved"}],
            }
        }
    }
    monkeypatch.setattr(_preflight, "_load_aspect_manifest", lambda _a: fake_manifest)
    monkeypatch.setattr(_preflight, "_aspect_depth_range", lambda _a: (1, 2))

    checks = _resolve_preflight_checks({"acme-y": 1}, {}, "commit")
    assert checks == []


def test_verify_malformed_kit_version(tmp_path: Path) -> None:
    """Malformed kit_version in config produces a warning (covers cli.py:498-499)."""
    target = _init_project(tmp_path)
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["kit_version"] = "not-a-valid-version!!!"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))

    runner = CliRunner()
    result = runner.invoke(main, ["verify", str(target)])
    assert "Could not parse kit_version" in result.output
