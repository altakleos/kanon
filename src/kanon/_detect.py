"""Project-type auto-detection for preflight tool configuration."""
from __future__ import annotations

from pathlib import Path


def detect_tool_config(target: Path) -> dict[str, str]:
    """Inspect *target* for ecosystem markers and return preflight tool commands.

    Returns a dict with keys matching the testing aspect's config-schema:
    test_cmd, lint_cmd, typecheck_cmd, format_cmd. Only non-empty values
    are included (undetected tools are omitted).
    """
    config: dict[str, str] = {}

    # Python
    if (target / "pyproject.toml").is_file() or (target / "setup.py").is_file():
        config["test_cmd"] = "pytest -q"
        # Detect ruff
        if (target / "ruff.toml").is_file() or _toml_has_section(
            target / "pyproject.toml", "tool.ruff"
        ):
            config["lint_cmd"] = "ruff check ."
            config["format_cmd"] = "ruff format --check ."
        # Detect mypy
        if (target / "mypy.ini").is_file() or _toml_has_section(
            target / "pyproject.toml", "tool.mypy"
        ):
            config["typecheck_cmd"] = "mypy src/"

    # Node / TypeScript
    elif (target / "package.json").is_file():
        config["test_cmd"] = "npm test"
        if (target / "tsconfig.json").is_file():
            config["typecheck_cmd"] = "npx tsc --noEmit"
        if _has_eslint_config(target):
            config["lint_cmd"] = "npx eslint ."

    # Rust
    elif (target / "Cargo.toml").is_file():
        config["test_cmd"] = "cargo test"
        config["lint_cmd"] = "cargo clippy"
        config["format_cmd"] = "cargo fmt --check"

    # Go
    elif (target / "go.mod").is_file():
        config["test_cmd"] = "go test ./..."
        config["lint_cmd"] = "go vet ./..."

    return config


def _toml_has_section(path: Path, section: str) -> bool:
    """Check if a TOML file contains a [section] header (simple text scan)."""
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8")
        # Convert dotted section to TOML header: tool.ruff → [tool.ruff]
        return f"[{section}]" in text
    except OSError:
        return False


def _has_eslint_config(target: Path) -> bool:
    """Check for any ESLint config file."""
    for name in (".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml",
                 "eslint.config.js", "eslint.config.mjs", "eslint.config.ts"):
        if (target / name).is_file():
            return True
    return False
