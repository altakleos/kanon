"""Tests for ci/check_security_patterns.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "ci" / "check_security_patterns.py"
assert _SCRIPT_PATH.is_file(), f"script not found: {_SCRIPT_PATH}"


def _load():
    spec = importlib.util.spec_from_file_location("check_security_patterns", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


mod = _load()


def test_real_repo_no_errors() -> None:
    """The kanon repo's own src/kanon/ must be free of tls-disabled findings.

    sql-interpolation is excluded because the best-effort regex flags f-strings
    containing the word "update" (e.g. ``f"fidelity: … update."``).
    """
    src_dir = _REPO_ROOT / "src" / "kanon"
    if not src_dir.is_dir():
        pytest.skip("src/kanon/ not found")
    files = mod._collect_files(src_dir)
    findings: list[dict] = []
    for f in files:
        findings.extend(mod._scan_file(f))
    bad = [f for f in findings if f["rule"] == "tls-disabled"]
    assert bad == [], f"unexpected findings in src/kanon/:\n{bad}"


def test_sql_interpolation_detected(tmp_path: Path) -> None:
    p = tmp_path / "bad_sql.py"
    p.write_text('query = f"SELECT * FROM {table}"\n', encoding="utf-8")
    findings = mod._scan_file(p)
    assert any(f["rule"] == "sql-interpolation" for f in findings)


def test_tls_disabled_detected(tmp_path: Path) -> None:
    p = tmp_path / "bad_tls.py"
    p.write_text("requests.get(url, verify=False)\n", encoding="utf-8")
    findings = mod._scan_file(p)
    assert any(f["rule"] == "tls-disabled" for f in findings)


def test_permissive_mode_detected(tmp_path: Path) -> None:
    p = tmp_path / "bad_chmod.py"
    p.write_text("os.chmod(path, 0o777)\n", encoding="utf-8")
    findings = mod._scan_file(p)
    assert any(f["rule"] == "permissive-mode" for f in findings)


def test_wildcard_cors_detected(tmp_path: Path) -> None:
    p = tmp_path / "bad_cors.py"
    p.write_text('headers = {"Access-Control-Allow-Origin: *"}\n', encoding="utf-8")
    findings = mod._scan_file(p)
    assert any(f["rule"] == "wildcard-cors" for f in findings)


def test_high_entropy_secret_detected(tmp_path: Path) -> None:
    p = tmp_path / "bad_secret.py"
    p.write_text('key = "aB3dE5fG7hJ9kL1mN3pQ5rS7tU9vW1xY"\n', encoding="utf-8")
    findings = mod._scan_file(p)
    assert any(f["rule"] == "high-entropy-secret" for f in findings)


def test_clean_file_no_findings(tmp_path: Path) -> None:
    p = tmp_path / "clean.py"
    p.write_text("x = 1\n", encoding="utf-8")
    findings = mod._scan_file(p)
    assert findings == []


def test_skip_dirs_respected(tmp_path: Path) -> None:
    nm = tmp_path / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "index.js").write_text("module.exports = {}\n", encoding="utf-8")
    files = mod._collect_files(tmp_path)
    assert all("node_modules" not in str(f) for f in files)


def test_main_exits_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "clean.py").write_text("x = 1\n", encoding="utf-8")
    import sys
    old_argv = sys.argv
    sys.argv = ["check_security_patterns", "--root", str(tmp_path)]
    try:
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
        assert exc_info.value.code == 0
    finally:
        sys.argv = old_argv
    out = capsys.readouterr().out
    report = json.loads(out)
    assert report["status"] == "ok"
    assert report["findings"] == []
