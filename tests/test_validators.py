"""Tests for kit-aspect validator modules."""
from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from kanon._validators import adr_immutability, link_check, plan_completion

# ── plan_completion ──────────────────────────────────────────────


class TestPlanCompletion:
    def _run(self, tmp_path: Path, files: dict[str, str]) -> list[str]:
        plans = tmp_path / "docs" / "plans"
        plans.mkdir(parents=True)
        for name, content in files.items():
            (plans / name).write_text(content)
        errors: list[str] = []
        plan_completion.check(tmp_path, errors, [])
        return errors

    def test_done_all_ticked(self, tmp_path: Path) -> None:
        assert not self._run(tmp_path, {"a.md": textwrap.dedent("""\
            ---
            status: done
            ---
            - [x] task one
            - [x] task two
        """)})

    def test_done_with_unchecked(self, tmp_path: Path) -> None:
        errs = self._run(tmp_path, {"a.md": textwrap.dedent("""\
            ---
            status: done
            ---
            - [x] task one
            - [ ] task two
        """)})
        assert len(errs) == 1
        assert "1 unchecked" in errs[0]

    def test_not_done_ignored(self, tmp_path: Path) -> None:
        assert not self._run(tmp_path, {"a.md": textwrap.dedent("""\
            ---
            status: in-progress
            ---
            - [ ] task one
        """)})

    def test_no_frontmatter(self, tmp_path: Path) -> None:
        assert not self._run(tmp_path, {"a.md": "- [ ] task one\n"})

    def test_skips_readme_and_roadmap(self, tmp_path: Path) -> None:
        done_unchecked = "---\nstatus: done\n---\n- [ ] oops\n"
        assert not self._run(tmp_path, {
            "README.md": done_unchecked,
            "roadmap.md": done_unchecked,
        })

    def test_missing_plans_dir(self, tmp_path: Path) -> None:
        errors: list[str] = []
        plan_completion.check(tmp_path, errors, [])
        assert not errors

    def test_tilde_counts_as_ticked(self, tmp_path: Path) -> None:
        assert not self._run(tmp_path, {"a.md": textwrap.dedent("""\
            ---
            status: done
            ---
            - [~] partial task
            - [x] done task
        """)})

    def test_unclosed_frontmatter_ignored(self, tmp_path: Path) -> None:
        """Plan with opening --- but no closing --- is not treated as done."""
        assert not self._run(tmp_path, {"a.md": "---\nstatus: done\n# no closing\n"})

    def test_frontmatter_without_status_ignored(self, tmp_path: Path) -> None:
        """Plan with valid frontmatter but no status key is not treated as done."""
        assert not self._run(tmp_path, {"a.md": "---\ntitle: foo\n---\n- [ ] task\n"})


# ── link_check ───────────────────────────────────────────────────


class TestLinkCheck:
    def test_valid_link(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "target.md").write_text("# Target\n")
        (docs / "source.md").write_text("[link](target.md)\n")
        errors: list[str] = []
        link_check.check(tmp_path, errors, [])
        assert not errors

    def test_broken_link(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "source.md").write_text("[link](missing.md)\n")
        errors: list[str] = []
        link_check.check(tmp_path, errors, [])
        assert len(errors) == 1
        assert "missing.md" in errors[0]

    def test_external_link_ignored(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "source.md").write_text("[link](https://example.com)\n")
        errors: list[str] = []
        link_check.check(tmp_path, errors, [])
        assert not errors

    def test_code_block_ignored(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "source.md").write_text(
            "```\n[link](missing.md)\n```\n"
        )
        errors: list[str] = []
        link_check.check(tmp_path, errors, [])
        assert not errors

    def test_anchor_only_ignored(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "source.md").write_text("[link](#heading)\n")
        errors: list[str] = []
        link_check.check(tmp_path, errors, [])
        assert not errors

    def test_missing_docs_dir(self, tmp_path: Path) -> None:
        errors: list[str] = []
        link_check.check(tmp_path, errors, [])
        assert not errors


# ── adr_immutability ─────────────────────────────────────────────


def _git_init(path: Path) -> None:
    """Create a git repo with an initial commit."""
    subprocess.run(["git", "init", "-b", "main"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True, check=True)
    (path / ".gitkeep").write_text("")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)


def _commit(path: Path, msg: str = "update") -> None:
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", msg, "--allow-empty"], cwd=path, capture_output=True, check=True)


_ACCEPTED_ADR = """\
---
status: accepted
---
# ADR-0001

Body text.
"""


class TestAdrImmutability:
    def test_body_change_detected(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        adr = tmp_path / "docs" / "decisions" / "0001-test.md"
        adr.parent.mkdir(parents=True)
        adr.write_text(_ACCEPTED_ADR)
        _commit(tmp_path, "add adr")
        adr.write_text(_ACCEPTED_ADR.replace("Body text.", "Changed body."))
        _commit(tmp_path, "edit adr")
        errors: list[str] = []
        adr_immutability.check(tmp_path, errors, [])
        assert len(errors) == 1
        assert "body change" in errors[0]

    def test_frontmatter_only_change_ok(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        adr = tmp_path / "docs" / "decisions" / "0001-test.md"
        adr.parent.mkdir(parents=True)
        adr.write_text(_ACCEPTED_ADR)
        _commit(tmp_path, "add adr")
        adr.write_text(_ACCEPTED_ADR.replace(
            "status: accepted", "status: accepted\ndate: 2026-01-01"
        ))
        _commit(tmp_path, "update fm")
        errors: list[str] = []
        adr_immutability.check(tmp_path, errors, [])
        assert not errors

    def test_historical_note_append_ok(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        adr = tmp_path / "docs" / "decisions" / "0001-test.md"
        adr.parent.mkdir(parents=True)
        adr.write_text(_ACCEPTED_ADR)
        _commit(tmp_path, "add adr")
        adr.write_text(_ACCEPTED_ADR + "\n## Historical Note\n\nAdded later.\n")
        _commit(tmp_path, "add note")
        errors: list[str] = []
        adr_immutability.check(tmp_path, errors, [])
        assert not errors

    def test_trailer_exemption(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        adr = tmp_path / "docs" / "decisions" / "0001-test.md"
        adr.parent.mkdir(parents=True)
        adr.write_text(_ACCEPTED_ADR)
        _commit(tmp_path, "add adr")
        adr.write_text(_ACCEPTED_ADR.replace("Body text.", "Changed body."))
        _commit(tmp_path, "edit adr\n\nAllow-ADR-edit: 0001 — reason here")
        errors: list[str] = []
        adr_immutability.check(tmp_path, errors, [])
        assert not errors

    def test_non_accepted_ignored(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        adr = tmp_path / "docs" / "decisions" / "0001-test.md"
        adr.parent.mkdir(parents=True)
        adr.write_text("---\nstatus: draft\n---\n# ADR\n\nBody.\n")
        _commit(tmp_path, "add adr")
        adr.write_text("---\nstatus: draft\n---\n# ADR\n\nChanged.\n")
        _commit(tmp_path, "edit")
        errors: list[str] = []
        adr_immutability.check(tmp_path, errors, [])
        assert not errors

    def test_new_adr_not_flagged(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        adr = tmp_path / "docs" / "decisions" / "0001-test.md"
        adr.parent.mkdir(parents=True)
        adr.write_text(_ACCEPTED_ADR)
        _commit(tmp_path, "add adr")
        errors: list[str] = []
        adr_immutability.check(tmp_path, errors, [])
        assert not errors

    def test_deleted_adr_flagged(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        adr = tmp_path / "docs" / "decisions" / "0001-test.md"
        adr.parent.mkdir(parents=True)
        adr.write_text(_ACCEPTED_ADR)
        _commit(tmp_path, "add adr")
        adr.unlink()
        _commit(tmp_path, "delete adr")
        errors: list[str] = []
        adr_immutability.check(tmp_path, errors, [])
        assert len(errors) == 1
        assert "deleted" in errors[0]

    def test_non_adr_file_ignored(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        f = tmp_path / "docs" / "decisions" / "README.md"
        f.parent.mkdir(parents=True)
        f.write_text("# Index\n")
        _commit(tmp_path, "add readme")
        f.write_text("# Updated Index\n")
        _commit(tmp_path, "edit readme")
        errors: list[str] = []
        adr_immutability.check(tmp_path, errors, [])
        assert not errors


# ── _check_one unit tests (no git needed) ────────────────────────


class TestCheckOne:
    def test_body_change_returns_error(self) -> None:
        err = adr_immutability._check_one(
            path="docs/decisions/0001-test.md",
            old_text=_ACCEPTED_ADR,
            new_text=_ACCEPTED_ADR.replace("Body text.", "New."),
            commit_msg="edit", sha="abc12345",
        )
        assert err and "body change" in err

    def test_same_body_returns_none(self) -> None:
        assert adr_immutability._check_one(
            path="docs/decisions/0001-test.md",
            old_text=_ACCEPTED_ADR, new_text=_ACCEPTED_ADR,
            commit_msg="noop", sha="abc12345",
        ) is None


class TestParseTrailers:
    def test_single(self) -> None:
        t = adr_immutability._parse_trailers("msg\n\nAllow-ADR-edit: 0001 — reason")
        assert t == {"0001": "reason"}

    def test_comma_separated(self) -> None:
        t = adr_immutability._parse_trailers("msg\n\nAllow-ADR-edit: 1, 2 — reason")
        assert "0001" in t and "0002" in t

    def test_no_reason_rejected(self) -> None:
        t = adr_immutability._parse_trailers("msg\n\nAllow-ADR-edit: 0001 — ")
        assert not t


class TestSplitFm:
    def test_no_frontmatter(self) -> None:
        fm, body = adr_immutability._split_fm("# Title\nBody\n")
        assert fm == {} and body == "# Title\nBody\n"

    def test_with_frontmatter(self) -> None:
        fm, body = adr_immutability._split_fm("---\nk: v\n---\nbody\n")
        assert fm == {"k": "v"} and body == "body\n"
