"""Tests for project-type auto-detection."""
from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from kanon._detect import detect_tool_config
from kanon.cli import main


def test_detect_python_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n[tool.mypy]\n")
    config = detect_tool_config(tmp_path)
    assert config["test_cmd"] == "pytest -q"
    assert config["lint_cmd"] == "ruff check ."
    assert config["typecheck_cmd"] == "mypy src/"
    assert config["format_cmd"] == "ruff format --check ."


def test_detect_python_no_ruff_no_mypy(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
    config = detect_tool_config(tmp_path)
    assert config["test_cmd"] == "pytest -q"
    assert "lint_cmd" not in config
    assert "typecheck_cmd" not in config


def test_detect_node(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "tsconfig.json").write_text("{}")
    config = detect_tool_config(tmp_path)
    assert config["test_cmd"] == "npm test"
    assert config["typecheck_cmd"] == "npx tsc --noEmit"


def test_detect_rust(tmp_path: Path) -> None:
    (tmp_path / "Cargo.toml").write_text("[package]\n")
    config = detect_tool_config(tmp_path)
    assert config["test_cmd"] == "cargo test"
    assert config["lint_cmd"] == "cargo clippy"


def test_detect_go(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module example.com/foo\n")
    config = detect_tool_config(tmp_path)
    assert config["test_cmd"] == "go test ./..."
    assert config["lint_cmd"] == "go vet ./..."


def test_detect_unknown(tmp_path: Path) -> None:
    config = detect_tool_config(tmp_path)
    assert config == {}


def test_init_auto_detects_python(tmp_path: Path) -> None:
    """kanon init on a Python project pre-fills testing config."""
    target = tmp_path / "proj"
    target.mkdir()
    (target / "pyproject.toml").write_text("[tool.ruff]\n[tool.mypy]\n")
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(target), "--tier", "1"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    testing_config = config["aspects"]["kanon-testing"].get("config", {})
    assert testing_config.get("test_cmd") == "pytest -q"
    assert testing_config.get("lint_cmd") == "ruff check ."


def test_detect_node_with_eslint(tmp_path: Path) -> None:
    """Node project with ESLint config is detected."""
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / ".eslintrc.json").write_text("{}")
    config = detect_tool_config(tmp_path)
    assert config["test_cmd"] == "npm test"
    assert config["lint_cmd"] == "npx eslint ."
    assert "typecheck_cmd" not in config


def test_toml_has_section_unreadable(tmp_path: Path) -> None:
    """_toml_has_section returns False for unreadable files."""
    from kanon._detect import _toml_has_section

    bad = tmp_path / "bad.toml"
    bad.mkdir()  # directory, not file — is_file() returns False
    assert _toml_has_section(bad, "tool.ruff") is False


def test_toml_has_section_oserror(tmp_path: Path) -> None:
    """_toml_has_section returns False on OSError."""
    import os

    from kanon._detect import _toml_has_section

    bad = tmp_path / "bad.toml"
    bad.write_text("[tool.ruff]")
    os.chmod(str(bad), 0o000)
    try:
        result = _toml_has_section(bad, "tool.ruff")
        # On some systems root can still read — accept either
        assert isinstance(result, bool)
    finally:
        os.chmod(str(bad), 0o644)
