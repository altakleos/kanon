"""Tests for ci/check_adr_immutability.py.

Each test sets up a synthetic git repo in tmp_path with one or more ADR
files, makes commits that exercise a specific edit pattern, and asserts
the gate's verdict.

Categories covered:
- frontmatter-only changes to an accepted ADR (allowed)
- body changes to a provisional ADR (allowed)
- body changes to an accepted ADR without trailer (fail)
- body changes with a valid trailer (allowed)
- trailer naming a different ADR (fail)
- trailer with empty reason (fail)
- status transition accepted → superseded (allowed)
- appending a `## Historical Note` (allowed)
- new ADR creation (allowed)
- deleted ADR (fail)
- multiple ADRs in one commit, single trailer covering both (allowed)
- multi-file diff with mixed legal/illegal changes
- en-dash and ASCII-hyphen trailer separators (allowed)
- range mode: BASE..HEAD walks every commit
- CLI entry happy path + non-zero exit on violations
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import _git


@pytest.fixture(scope="module")
def _M(load_ci_script):
    return load_ci_script("check_adr_immutability.py")


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "docs" / "decisions").mkdir(parents=True, exist_ok=True)


def _write_adr(
    repo: Path, number: str, status: str, body: str, slug: str = "decision"
) -> Path:
    path = repo / "docs" / "decisions" / f"{number}-{slug}.md"
    text = f"---\nstatus: {status}\ndate: 2026-04-26\n---\n{body}"
    path.write_text(text, encoding="utf-8")
    return path


def _commit(repo: Path, message: str, *paths: str) -> str:
    if paths:
        _git(repo, "add", *paths)
    else:
        _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


# ---------------------------------------------------------------------------
# Library-level cases (check_adr_immutability)
# ---------------------------------------------------------------------------


def test_frontmatter_only_status_flip_is_allowed(_M, tmp_path: Path) -> None:
    """Status FSM transition with body unchanged is exception class 1."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0001", "accepted", "Body content.\n")
    _commit(tmp_path, "docs: add ADR-0001")
    _write_adr(tmp_path, "0001", "superseded", "Body content.\n")
    _commit(tmp_path, "docs: supersede ADR-0001")

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 0, errors
    assert errors == []


def test_body_change_to_provisional_adr_is_allowed(_M, tmp_path: Path) -> None:
    """Provisional ADRs are mutable by definition (rule applies only to accepted)."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0002", "provisional", "Old body.\n")
    _commit(tmp_path, "docs: add ADR-0002 (provisional)")
    _write_adr(tmp_path, "0002", "provisional", "New body, edited freely.\n")
    _commit(tmp_path, "docs: refine ADR-0002 still-provisional draft")

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 0, errors


def test_body_change_to_accepted_adr_without_trailer_fails(
    _M, tmp_path: Path,
) -> None:
    """The core rule: post-acceptance body change without exception fails."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0003", "accepted", "Original body.\n")
    _commit(tmp_path, "docs: add ADR-0003")
    _write_adr(tmp_path, "0003", "accepted", "Sneakily edited body.\n")
    _commit(tmp_path, "docs: tweak ADR-0003")

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 1
    assert any("0003" in e and "not allowed" in e for e in errors)


def test_body_change_with_valid_trailer_is_allowed(_M, tmp_path: Path) -> None:
    """Valid Allow-ADR-edit trailer is exception class 3."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0004", "accepted", "Body.\n")
    _commit(tmp_path, "docs: add ADR-0004")
    _write_adr(tmp_path, "0004", "accepted", "Body with typo fix.\n")
    _commit(
        tmp_path,
        "docs: fix typo in ADR-0004\n\nAllow-ADR-edit: 0004 — typo correction",
    )

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 0, errors


def test_trailer_naming_a_different_adr_fails(_M, tmp_path: Path) -> None:
    """A trailer for ADR-0006 does not authorise editing ADR-0005."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0005", "accepted", "Body.\n", slug="five")
    _commit(tmp_path, "docs: add ADR-0005")
    _write_adr(tmp_path, "0005", "accepted", "Edited.\n", slug="five")
    _commit(
        tmp_path,
        "docs: edit ADR-0005\n\nAllow-ADR-edit: 0006 — wrong number cited",
    )

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 1
    assert any("0005" in e for e in errors)


def test_trailer_with_empty_reason_fails(_M, tmp_path: Path) -> None:
    """A trailer with no reason is silently ignored — the edit is not authorised."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0007", "accepted", "Body.\n")
    _commit(tmp_path, "docs: add ADR-0007")
    _write_adr(tmp_path, "0007", "accepted", "Edited.\n")
    _commit(tmp_path, "docs: tweak\n\nAllow-ADR-edit: 0007 —")

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 1


def test_status_transition_to_superseded_with_body_unchanged(
    _M, tmp_path: Path,
) -> None:
    """Adding `superseded-by:` frontmatter without touching body is allowed."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0008", "accepted", "Original wisdom.\n")
    _commit(tmp_path, "docs: add ADR-0008")
    path = tmp_path / "docs" / "decisions" / "0008-decision.md"
    path.write_text(
        "---\nstatus: superseded\nsuperseded-by: 0009\ndate: 2026-04-26\n---\n"
        "Original wisdom.\n",
        encoding="utf-8",
    )
    _commit(tmp_path, "docs: ADR-0008 superseded by ADR-0009")

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 0, errors


def test_historical_note_append_is_allowed(_M, tmp_path: Path) -> None:
    """Appending a `## Historical Note` section is exception class 2."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0009", "accepted", "Original wisdom.\n")
    _commit(tmp_path, "docs: add ADR-0009")
    _write_adr(
        tmp_path,
        "0009",
        "accepted",
        "Original wisdom.\n\n## Historical Note\n\nLater context.\n",
    )
    _commit(tmp_path, "docs: append historical note to ADR-0009")

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 0, errors


def test_new_adr_creation_is_allowed(_M, tmp_path: Path) -> None:
    """Adding a new ADR file (no parent version) is allowed unconditionally."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0010", "accepted", "Body.\n")
    _commit(tmp_path, "chore: seed repo")
    _write_adr(
        tmp_path, "0011", "accepted", "Fresh ADR body.\n", slug="eleven"
    )
    _commit(tmp_path, "docs: add ADR-0011")

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 0, errors


def test_deleted_adr_fails(_M, tmp_path: Path) -> None:
    """Deleting an accepted ADR is a violation — supersede instead."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0012", "accepted", "Body.\n")
    _commit(tmp_path, "docs: add ADR-0012")
    (tmp_path / "docs" / "decisions" / "0012-decision.md").unlink()
    _commit(tmp_path, "docs: delete ADR-0012")

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 1
    assert any("0012" in e and "deleted" in e for e in errors)


def test_multiple_adrs_with_single_trailer_covering_both(
    _M, tmp_path: Path,
) -> None:
    """Comma-separated ADR numbers in one trailer authorise multiple edits."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0013", "accepted", "Body 13.\n", slug="thirteen")
    _write_adr(tmp_path, "0014", "accepted", "Body 14.\n", slug="fourteen")
    _commit(tmp_path, "docs: add ADR-0013 and ADR-0014")
    _write_adr(tmp_path, "0013", "accepted", "Body 13 v2.\n", slug="thirteen")
    _write_adr(tmp_path, "0014", "accepted", "Body 14 v2.\n", slug="fourteen")
    _commit(
        tmp_path,
        "docs: typo sweep\n\nAllow-ADR-edit: 0013, 0014 — typo sweep",
    )

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 0, errors


def test_mixed_legal_and_illegal_changes_in_one_commit(_M, tmp_path: Path) -> None:
    """A trailer for ADR-0015 does not cover an unannotated edit to ADR-0016."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0015", "accepted", "Body 15.\n", slug="fifteen")
    _write_adr(tmp_path, "0016", "accepted", "Body 16.\n", slug="sixteen")
    _commit(tmp_path, "docs: add ADR-0015 and ADR-0016")
    _write_adr(tmp_path, "0015", "accepted", "Body 15 v2.\n", slug="fifteen")
    _write_adr(tmp_path, "0016", "accepted", "Body 16 v2.\n", slug="sixteen")
    _commit(
        tmp_path,
        "docs: edit ADR-0015 and silently ADR-0016\n\n"
        "Allow-ADR-edit: 0015 — typo",
    )

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 1
    assert len(errors) == 1
    assert "0016" in errors[0]


def test_ascii_hyphen_separator_is_accepted(_M, tmp_path: Path) -> None:
    """The trailer accepts `-` as separator in addition to `—` and `:`."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0017", "accepted", "Body.\n")
    _commit(tmp_path, "docs: add ADR-0017")
    _write_adr(tmp_path, "0017", "accepted", "Edited.\n")
    _commit(
        tmp_path,
        "docs: tweak ADR-0017\n\nAllow-ADR-edit: 0017 - typo correction",
    )

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 0, errors


def test_en_dash_separator_is_accepted(_M, tmp_path: Path) -> None:
    """The trailer accepts en-dash `–` (U+2013) as separator."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0018", "accepted", "Body.\n")
    _commit(tmp_path, "docs: add ADR-0018")
    _write_adr(tmp_path, "0018", "accepted", "Edited.\n")
    _commit(
        tmp_path,
        "docs: tweak ADR-0018\n\nAllow-ADR-edit: 0018 – typo correction",
    )

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 0, errors


def test_colon_separator_is_accepted(_M, tmp_path: Path) -> None:
    """The trailer accepts `:` as separator (Conventional Commits-friendly)."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0019", "accepted", "Body.\n")
    _commit(tmp_path, "docs: add ADR-0019")
    _write_adr(tmp_path, "0019", "accepted", "Edited.\n")
    _commit(
        tmp_path,
        "docs: tweak ADR-0019\n\nAllow-ADR-edit: 0019: typo correction",
    )

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 0, errors


def test_range_mode_walks_every_commit(_M, tmp_path: Path) -> None:
    """In PR mode (BASE..HEAD), every commit in range is checked."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0020", "accepted", "Body.\n")
    base_sha = _commit(tmp_path, "docs: add ADR-0020")
    _git(tmp_path, "checkout", "-q", "-b", "feature")
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    _commit(tmp_path, "docs: README")
    _write_adr(tmp_path, "0020", "accepted", "Stealth edit.\n")
    _commit(tmp_path, "docs: stealth edit ADR-0020")

    # Push-mode (HEAD only) catches the violation.
    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 1

    # Range-mode (base..HEAD) also catches it via the same offending commit.
    code, errors = _M.check_adr_immutability(tmp_path, base_ref=base_sha)
    assert code == 1
    assert any("0020" in e for e in errors)


def test_root_commit_is_skipped(_M, tmp_path: Path) -> None:
    """The root commit has no parent to diff against; it must not crash."""
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0021", "accepted", "Body.\n")
    _commit(tmp_path, "docs: ADR-0021 in root")

    code, errors = _M.check_adr_immutability(tmp_path)
    assert code == 0
    assert errors == []


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------


def test_cli_exit_zero_on_clean_repo(
    _M, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0022", "accepted", "Body.\n")
    _commit(tmp_path, "docs: add ADR-0022")

    rc = _M.main(["--repo", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "adr-immutability: OK" in out


def test_cli_exit_one_on_violation(
    _M, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _init_repo(tmp_path)
    _write_adr(tmp_path, "0023", "accepted", "Body.\n")
    _commit(tmp_path, "docs: add ADR-0023")
    _write_adr(tmp_path, "0023", "accepted", "Sneaky edit.\n")
    _commit(tmp_path, "docs: edit ADR-0023")

    rc = _M.main(["--repo", str(tmp_path)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "FAIL" in err
    assert "0023" in err
