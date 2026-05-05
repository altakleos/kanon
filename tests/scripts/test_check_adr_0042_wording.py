"""Tests for scripts/check_adr_0042_wording.py."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def mod(load_ci_script):
    return load_ci_script("check_adr_0042_wording.py")


def _seed_synthetic_repo(
    tmp_path: Path,
    *,
    adr_section_body: str,
    cli_constant_body: str,
) -> Path:
    """Plant minimal versions of the two surfaces under *tmp_path*.

    The validator only reads the two anchor files; nothing else needs to
    exist. Both files are placed at the canonical paths the validator
    expects.
    """
    adr = tmp_path / "docs" / "decisions" / "0042-verification-scope-of-exit-zero.md"
    adr.parent.mkdir(parents=True)
    adr.write_text(
        "---\nstatus: accepted\n---\n# ADR-0042\n\n"
        "## Decision\n\n"
        "### 1. The canonical exit-zero wording\n\n"
        + adr_section_body
        + "\n\n### 2. Cross-publisher symmetry\n\n"
        "Sentinel section so the validator knows where §1 ends.\n",
        encoding="utf-8",
    )
    cli = tmp_path / "packages" / "kanon-core" / "src" / "kanon_core" / "cli.py"
    cli.parent.mkdir(parents=True)
    cli.write_text(
        '"""Test CLI module."""\n\n'
        f"_ADR_0042_VERIFY_SCOPE = (\n{cli_constant_body}\n)\n",
        encoding="utf-8",
    )
    return tmp_path


_ADR_BODY_FULL = (
    "It MUST NOT be interpreted as:\n\n"
    "- a signal that the consumer's repository follows good engineering practices "
    "beyond what the enabled aspects define;\n"
    "- a correctness or quality endorsement of any prose, protocol, or code;\n"
    "- a guarantee that the agent will comply at runtime — exit-0 is a static "
    "structural check, not a runtime behavioural guarantee;\n"
    "- confirmation that resolution-replay invocations are semantically correct "
    "realizations of their contracts."
)

_CLI_BODY_FULL = (
    '    "It MUST NOT be interpreted as:\\n"\n'
    '    "\\n"\n'
    '    "- a signal that the consumer\'s repository follows good engineering practices\\n"\n'
    '    "  beyond what the enabled aspects define;\\n"\n'
    '    "- a correctness or quality endorsement of any prose, protocol, or code;\\n"\n'
    '    "- a guarantee that the agent will comply at runtime — exit-0 is a static\\n"\n'
    '    "  structural check, not a runtime behavioural guarantee;\\n"\n'
    '    "- confirmation that resolution-replay invocations are semantically correct\\n"\n'
    '    "  realizations of their contracts."'
)


def test_real_repo_parity_holds(mod, repo_root, capsys: pytest.CaptureFixture[str]) -> None:
    """The kanon repo itself must pass the wording-parity gate.

    AC1 from docs/plans/active/adr-0042-wording-gate.md.
    """
    rc = mod.main(["--root", str(repo_root)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ADR-0042 wording parity holds" in out


def test_synthetic_parity_holds(mod, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Both surfaces carry all four clauses → exit 0."""
    _seed_synthetic_repo(
        tmp_path,
        adr_section_body=_ADR_BODY_FULL,
        cli_constant_body=_CLI_BODY_FULL,
    )
    rc = mod.main(["--root", str(tmp_path)])
    assert rc == 0


def test_clause_missing_from_cli_fails(
    mod, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Strip a clause from the CLI constant → exit 1, missing clause cited.

    AC2 from docs/plans/active/adr-0042-wording-gate.md.
    """
    cli_body_missing = _CLI_BODY_FULL.replace(
        "good engineering practices",
        "MUTATED ENGINEERING PRACTICES",
    )
    _seed_synthetic_repo(
        tmp_path,
        adr_section_body=_ADR_BODY_FULL,
        cli_constant_body=cli_body_missing,
    )
    rc = mod.main(["--root", str(tmp_path)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "good-engineering-practices" in err
    assert "cli.py:_ADR_0042_VERIFY_SCOPE" in err


def test_clause_missing_from_adr_fails(
    mod, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Strip a clause from the ADR §1 body → exit 1, missing clause cited.

    AC3 from docs/plans/active/adr-0042-wording-gate.md.
    """
    adr_body_missing = _ADR_BODY_FULL.replace(
        "static structural check",
        "MUTATED STRUCTURAL CHECK",
    )
    _seed_synthetic_repo(
        tmp_path,
        adr_section_body=adr_body_missing,
        cli_constant_body=_CLI_BODY_FULL,
    )
    rc = mod.main(["--root", str(tmp_path)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "static-structural-check" in err
    assert "0042-verification-scope-of-exit-zero.md §1" in err


def test_missing_adr_file_fails(mod, tmp_path: Path) -> None:
    """No ADR file at the expected path → fail fast with diagnostic."""
    rc = mod.main(["--root", str(tmp_path)])
    assert rc == 1


def test_missing_cli_constant_fails(
    mod, tmp_path: Path,
) -> None:
    """ADR present but CLI constant missing → fail with named diagnostic."""
    adr = tmp_path / "docs" / "decisions" / "0042-verification-scope-of-exit-zero.md"
    adr.parent.mkdir(parents=True)
    adr.write_text(
        "### 1. The canonical exit-zero wording\n\n" + _ADR_BODY_FULL,
        encoding="utf-8",
    )
    cli = tmp_path / "packages" / "kanon-core" / "src" / "kanon_core" / "cli.py"
    cli.parent.mkdir(parents=True)
    cli.write_text("# constant absent\n", encoding="utf-8")
    rc = mod.main(["--root", str(tmp_path)])
    assert rc == 1


def test_normalise_whitespace_collapses_newlines_and_indent(mod) -> None:
    """Direct unit test on the helper — proves multi-line phrases match."""
    multi_line = "semantically correct\n  realizations of their contracts"
    normalised = mod._normalise_whitespace(multi_line)
    assert "semantically correct realizations" in normalised
