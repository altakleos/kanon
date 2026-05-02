#!/usr/bin/env python3
"""Enforce ADR body immutability per ``docs/development-process.md`` § ADRs.

Once an ADR reaches ``accepted`` or ``accepted (lite)``, its body — every
byte below the closing ``---`` of the YAML frontmatter — becomes immutable.
To reverse a decision, write a new ADR that supersedes the old one.

Three exception classes are honoured (per ADR-0032):

1. **Frontmatter-only changes.** Status FSM transitions
   (``provisional`` → ``accepted``, ``accepted`` → ``superseded``), date
   updates that accompany those transitions, and ``superseded-by:``
   annotations. The body is unchanged byte-for-byte.

2. **Appending a ``## Historical Note`` (or deeper) section.** A strict
   suffix-only addition starting with that heading. Preserves archaeology
   without altering prior claims.

3. **Explicit opt-out via commit-message trailer.** A line shaped::

       Allow-ADR-edit: NNNN — <reason>

   The trailer cites the four-digit ADR number(s) with a non-empty reason.
   Multiple ADRs may be listed comma-separated. Em-dash, en-dash, ASCII
   hyphen, or colon are all accepted as the separator before the reason.

Operating modes:

* ``--base-ref REF``  PR mode: walk every commit in ``REF..HEAD``.
* (default)            push mode: only the most-recent commit (``HEAD``).

This script is a kit-internal CI gate per ADR-0032. It is **not** scaffolded
to consumers as part of any aspect's ``files:``. Consumers wanting the same
discipline can copy this file (it has no kit-specific imports) or follow the
``adr-immutability`` protocol shipped at ``kanon-sdd`` depth 3 for
non-mechanical enforcement options.

Exit 0 if every ADR change in scope is allowed. Exit 1 with a structured
error per violation otherwise.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print(
        "ERROR: Missing 'pyyaml'. Install with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)


_ADR_PATTERN = re.compile(r"^docs/decisions/(\d{4})-.*\.md$")
_TRAILER_PATTERN = re.compile(
    r"^Allow-ADR-edit:\s*([0-9,\s]+?)\s*[—–\-:]\s*(.+?)\s*$",
    re.MULTILINE,
)
_HISTORICAL_NOTE_PATTERN = re.compile(
    r"^##+\s+Historical[\s\-]?[Nn]ote\b", re.MULTILINE
)
_ACCEPTED_STATUSES = frozenset({"accepted", "accepted (lite)"})


def _git(args: list[str], cwd: Path) -> str:
    """Run git; return stdout (or empty string on non-zero exit)."""
    result = subprocess.run(  # noqa: S603 — args fixed by caller
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body). Empty dict + full text on parse failure."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    try:
        fm = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return {}, text
    body = text[end + len("\n---\n") :]
    return (fm if isinstance(fm, dict) else {}, body)


def _adr_number_from_path(path: str) -> str | None:
    """Return the four-digit ADR number from ``docs/decisions/NNNN-<slug>.md``."""
    m = _ADR_PATTERN.match(path)
    return m.group(1) if m else None


def _parse_trailer_adrs(commit_msg: str) -> dict[str, str]:
    """Return ``{adr_number: reason}`` for every ``Allow-ADR-edit:`` trailer.

    Trailer format (per ADR-0032 §Decision):
        ``Allow-ADR-edit: NNNN[, MMMM, ...] [— | – | - | :] <reason>``
    Multiple trailers in the same commit message are merged; a later trailer
    for the same ADR number wins.
    """
    out: dict[str, str] = {}
    for m in _TRAILER_PATTERN.finditer(commit_msg):
        raw_nums = [n.strip() for n in m.group(1).split(",") if n.strip()]
        reason = m.group(2).strip()
        if not reason:
            continue
        for n in raw_nums:
            if not n.isdigit():
                continue
            out[n.zfill(4)] = reason
    return out


def _is_historical_note_append(old_body: str, new_body: str) -> bool:
    """``True`` iff *new_body* equals *old_body* + a ``## Historical Note`` suffix."""
    if not new_body.startswith(old_body):
        return False
    suffix = new_body[len(old_body) :].lstrip()
    return bool(_HISTORICAL_NOTE_PATTERN.match(suffix))


def _check_one_adr(
    *,
    path: str,
    old_text: str,
    new_text: str,
    commit_msg: str,
    sha: str,
) -> str | None:
    """Return ``None`` when the ADR change is allowed, else an error message.

    Reachable error paths:
        * body changed while old status was accepted, no exception applies.
        * file path doesn't match the ADR pattern (defensive; should not occur).
    """
    old_fm, old_body = _split_frontmatter(old_text)
    _, new_body = _split_frontmatter(new_text)

    old_status = (old_fm.get("status") or "").strip()
    if old_status not in _ACCEPTED_STATUSES:
        # Body of a non-accepted ADR (draft / provisional) is mutable.
        return None

    if old_body == new_body:
        # Frontmatter-only change (exception #1).
        return None

    if _is_historical_note_append(old_body, new_body):
        # Appended ## Historical Note (exception #2).
        return None

    adr_num = _adr_number_from_path(path)
    if adr_num is None:
        return f"{path}: unable to parse ADR number from filename"

    trailer_reasons = _parse_trailer_adrs(commit_msg)
    if adr_num in trailer_reasons:
        # Allow-ADR-edit trailer cites this ADR (exception #3).
        return None

    return (
        f"{path}: body change to accepted ADR-{adr_num} in commit "
        f"{sha[:8]} is not allowed. Either supersede this ADR with a new "
        f"one, append a `## Historical Note` section, or add an "
        f"`Allow-ADR-edit: {adr_num} — <reason>` trailer to the commit "
        f"message naming why the edit is justified."
    )


def _commits_in_range(
    base_ref: str | None, head: str, repo: Path
) -> list[str]:
    """Resolve commits to scan: HEAD only in push-mode, BASE..HEAD in PR-mode."""
    if base_ref is None:
        out = _git(["rev-parse", head], repo).strip()
        return [out] if out else []
    out = _git(["log", "--format=%H", f"{base_ref}..{head}"], repo)
    return [line.strip() for line in out.splitlines() if line.strip()]


def _files_changed_in(sha: str, repo: Path) -> list[str]:
    """Return paths changed by *sha* (one per line, no extra metadata)."""
    out = _git(
        ["show", "--name-only", "--pretty=", sha],
        repo,
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def _file_existed_at(sha: str, path: str, repo: Path) -> bool:
    """``True`` iff *path* is present in the tree of *sha*."""
    result = subprocess.run(  # noqa: S603 — args fixed by caller
        ["git", "cat-file", "-e", f"{sha}:{path}"],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def _has_parent(sha: str, repo: Path) -> bool:
    """``True`` iff *sha* has a parent (i.e., is not the root commit)."""
    return bool(
        _git(["rev-parse", "--quiet", "--verify", f"{sha}^"], repo).strip()
    )


def check_adr_immutability(
    repo_root: Path,
    base_ref: str | None = None,
    head: str = "HEAD",
) -> tuple[int, list[str]]:
    """Walk commits in ``(base_ref..head]`` and check each ADR change.

    Returns ``(exit_code, error_lines)``. ``exit_code == 0`` means clean.
    Per-commit cost is bounded by the number of `docs/decisions/*.md` paths
    in the commit's name-only diff; non-ADR commits short-circuit at the
    `_ADR_PATTERN.match(f)` check.
    """
    errors: list[str] = []
    commits = _commits_in_range(base_ref, head, repo_root)
    if not commits:
        return 0, []

    for sha in commits:
        commit_msg = _git(["log", "-1", "--format=%B", sha], repo_root)
        if not _has_parent(sha, repo_root):
            # Root commit has no parent to diff against.
            continue
        for f in _files_changed_in(sha, repo_root):
            if not _ADR_PATTERN.match(f):
                continue
            new_existed = _file_existed_at(sha, f, repo_root)
            old_existed = _file_existed_at(f"{sha}~", f, repo_root)
            if not old_existed and new_existed:
                # Newly-created ADR — body is the initial body, allowed.
                continue
            if old_existed and not new_existed:
                errors.append(
                    f"{f}: ADR was deleted in commit {sha[:8]} — "
                    f"immutability includes existence. Supersede instead "
                    f"of deleting."
                )
                continue
            old_text = _git(["show", f"{sha}~:{f}"], repo_root)
            new_text = _git(["show", f"{sha}:{f}"], repo_root)
            err = _check_one_adr(
                path=f,
                old_text=old_text,
                new_text=new_text,
                commit_msg=commit_msg,
                sha=sha,
            )
            if err:
                errors.append(err)

    return (1 if errors else 0), errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "").splitlines()[0] if __doc__ else None
    )
    parser.add_argument(
        "--base-ref",
        default=None,
        help=(
            "Compare every commit in BASE_REF..HEAD (PR mode). "
            "Omit to check only the HEAD commit (push mode)."
        ),
    )
    parser.add_argument(
        "--head", default="HEAD", help="Tip of the range to check."
    )
    parser.add_argument(
        "--repo", default=".", help="Repository root (default: cwd)."
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    code, errors = check_adr_immutability(repo, args.base_ref, args.head)
    if errors:
        print("FAIL — ADR immutability violations:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    n = len(_commits_in_range(args.base_ref, args.head, repo))
    print(f"adr-immutability: OK ({n} commit(s) scanned)")
    return code


if __name__ == "__main__":
    sys.exit(main())
