"""True E2E tests: build wheel, install in isolated venv, run CLI as subprocess."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

_REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def installed_venv(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the wheel and install it in a fresh venv. Shared across all tests in this module."""
    venv_dir = tmp_path_factory.mktemp("venv")
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    pip = str(venv_dir / "bin" / "pip")
    subprocess.run([pip, "install", str(_REPO_ROOT)], check=True, capture_output=True)
    return venv_dir


def _run_kanon(venv_dir: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run the installed kanon CLI as a subprocess."""
    kanon = str(venv_dir / "bin" / "kanon")
    return subprocess.run([kanon, *args], capture_output=True, text=True, cwd=cwd)


def test_installed_version(installed_venv: Path) -> None:
    """Entry point works and prints a version string."""
    r = _run_kanon(installed_venv, "--version")
    assert r.returncode == 0
    assert r.stdout.strip()


def test_installed_init_and_verify(installed_venv: Path, tmp_path: Path) -> None:
    """init scaffolds expected files; verify reports ok."""
    target = tmp_path / "proj"
    r = _run_kanon(installed_venv, "init", str(target), "--tier", "1")
    assert r.returncode == 0, r.stderr
    assert (target / "AGENTS.md").is_file()
    assert (target / ".kanon" / "config.yaml").is_file()

    r = _run_kanon(installed_venv, "verify", str(target))
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout.lower()


def test_installed_full_lifecycle(installed_venv: Path, tmp_path: Path) -> None:
    """init → tier 1→2→3 → demote to 1 (non-destructive)."""
    target = tmp_path / "proj"

    r = _run_kanon(installed_venv, "init", str(target), "--tier", "1")
    assert r.returncode == 0, r.stderr

    r = _run_kanon(installed_venv, "tier", "set", str(target), "2")
    assert r.returncode == 0, r.stderr

    r = _run_kanon(installed_venv, "verify", str(target))
    assert r.returncode == 0, r.stderr

    r = _run_kanon(installed_venv, "tier", "set", str(target), "3")
    assert r.returncode == 0, r.stderr

    r = _run_kanon(installed_venv, "verify", str(target))
    assert r.returncode == 0, r.stderr

    r = _run_kanon(installed_venv, "tier", "set", str(target), "1")
    assert r.returncode == 0, r.stderr

    # tier-3 artifacts survive demotion (non-destructive)
    assert (target / "docs" / "design").is_dir()


def test_installed_worktrees_aspect(installed_venv: Path, tmp_path: Path) -> None:
    """worktrees aspect: depth 1 → 2, artifacts created correctly."""
    target = tmp_path / "proj"

    r = _run_kanon(installed_venv, "init", str(target), "--tier", "1")
    assert r.returncode == 0, r.stderr

    r = _run_kanon(installed_venv, "aspect", "set-depth", str(target), "worktrees", "1")
    assert r.returncode == 0, r.stderr
    assert (target / ".kanon" / "protocols" / "worktrees" / "worktree-lifecycle.md").is_file()

    r = _run_kanon(installed_venv, "aspect", "set-depth", str(target), "worktrees", "2")
    assert r.returncode == 0, r.stderr
    assert (target / "scripts" / "worktree-setup.sh").is_file()

    # Demote to depth 0 before verify (matches in-process test pattern —
    # depth-2 branch-hygiene marker not yet injected into AGENTS.md)
    r = _run_kanon(installed_venv, "aspect", "set-depth", str(target), "worktrees", "0")
    assert r.returncode == 0, r.stderr

    r = _run_kanon(installed_venv, "verify", str(target))
    assert r.returncode == 0, r.stderr


def test_installed_upgrade_idempotent(installed_venv: Path, tmp_path: Path) -> None:
    """upgrade on a current project is idempotent."""
    target = tmp_path / "proj"

    r = _run_kanon(installed_venv, "init", str(target), "--tier", "1")
    assert r.returncode == 0, r.stderr

    r = _run_kanon(installed_venv, "upgrade", str(target))
    assert r.returncode == 0, r.stderr
    assert "already at" in r.stdout.lower() or "nothing to upgrade" in r.stdout.lower()
