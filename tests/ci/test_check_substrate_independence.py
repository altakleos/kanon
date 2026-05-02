"""Tests for ci/check_substrate_independence.py — ADR-0044 invariant gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def csi(load_ci_script):
    return load_ci_script("check_substrate_independence.py")


def test_real_repo_passes(csi) -> None:
    """The substrate must run without kanon_reference today."""
    rc = csi.main([])
    assert rc == 0, "substrate-independence gate must pass on main"


def test_main_exits_zero_on_ok(csi, capsys: pytest.CaptureFixture[str]) -> None:
    rc = csi.main([])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["status"] == "ok"
    assert parsed["errors"] == []


def test_subprocess_emits_ok_sentinel() -> None:
    """The sub-process script must print 'substrate-independence: OK'."""
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "ci" / "check_substrate_independence.py"
    spec_text = script_path.read_text(encoding="utf-8")
    # Extract the _SUBPROCESS_SCRIPT constant to verify its content shape.
    assert "_SUBPROCESS_SCRIPT" in spec_text
    assert "kanon_reference" in spec_text
    assert "substrate-independence: OK" in spec_text


def test_failure_when_substrate_imports_kanon_reference(csi, monkeypatch: pytest.MonkeyPatch) -> None:
    """If we synthetically inject `import kanon_reference` into the script,
    the gate must detect it and fail."""
    bad_script = csi._SUBPROCESS_SCRIPT.replace(
        "print(\"substrate-independence: OK\")",
        "import kanon_reference  # synthesised — should be blocked\nprint(\"substrate-independence: OK\")",
    )
    monkeypatch.setattr(csi, "_SUBPROCESS_SCRIPT", bad_script)
    rc = csi.main([])
    assert rc == 1, "gate must fail when substrate code imports kanon_reference"
