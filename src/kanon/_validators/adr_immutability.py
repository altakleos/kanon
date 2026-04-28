"""ADR body immutability validator (kanon-sdd depth 2+).

Checks the most recent commit for body changes to accepted ADRs.
Three exceptions: frontmatter-only changes, Historical Note appends,
and ``Allow-ADR-edit:`` commit-message trailers.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

_ADR_PATTERN = re.compile(r"^docs/decisions/(\d{4})-.*\.md$")
_TRAILER_PATTERN = re.compile(
    r"^Allow-ADR-edit:\s*([0-9,\s]+?)\s*[—–\-:]\s*(.+?)\s*$",
    re.MULTILINE,
)
_HISTORICAL_NOTE = re.compile(
    r"^##+\s+Historical[\s\-]?[Nn]ote\b", re.MULTILINE
)
_ACCEPTED = frozenset({"accepted", "accepted (lite)"})


def check(target: Path, errors: list[str], warnings: list[str]) -> None:
    head = _git(["rev-parse", "HEAD"], target).strip()
    if not head or not _has_parent(head, target):
        return
    commit_msg = _git(["log", "-1", "--format=%B", head], target)
    for f in _files_changed(head, target):
        if not _ADR_PATTERN.match(f):
            continue
        if not _existed_at(f"{head}~", f, target):
            continue
        if not _existed_at(head, f, target):
            errors.append(
                f"adr-immutability: {f}: deleted in HEAD — "
                f"immutability includes existence."
            )
            continue
        old = _git(["show", f"{head}~:{f}"], target)
        new = _git(["show", f"{head}:{f}"], target)
        err = _check_one(path=f, old_text=old, new_text=new,
                         commit_msg=commit_msg, sha=head)
        if err:
            errors.append(err)


def _check_one(
    *, path: str, old_text: str, new_text: str,
    commit_msg: str, sha: str,
) -> str | None:
    old_fm, old_body = _split_fm(old_text)
    _, new_body = _split_fm(new_text)
    if (old_fm.get("status") or "").strip() not in _ACCEPTED:
        return None
    if old_body == new_body:
        return None
    if new_body.startswith(old_body) and _HISTORICAL_NOTE.match(
        new_body[len(old_body):].lstrip()
    ):
        return None
    adr_num = _adr_num(path)
    if adr_num and adr_num in _parse_trailers(commit_msg):
        return None
    return (
        f"adr-immutability: {path}: body change to accepted ADR in "
        f"commit {sha[:8]} is not allowed."
    )


def _split_fm(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    try:
        fm = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return {}, text
    return (fm if isinstance(fm, dict) else {}, text[end + 5:])


def _adr_num(path: str) -> str | None:
    m = _ADR_PATTERN.match(path)
    return m.group(1) if m else None


def _parse_trailers(msg: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _TRAILER_PATTERN.finditer(msg):
        reason = m.group(2).strip()
        if not reason:
            continue
        for n in (x.strip() for x in m.group(1).split(",") if x.strip()):
            if n.isdigit():
                out[n.zfill(4)] = reason
    return out


def _git(args: list[str], cwd: Path) -> str:
    r = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False,
    )
    return r.stdout if r.returncode == 0 else ""


def _has_parent(sha: str, cwd: Path) -> bool:
    return bool(_git(["rev-parse", "--quiet", "--verify", f"{sha}^"], cwd).strip())


def _files_changed(sha: str, cwd: Path) -> list[str]:
    return [line.strip() for line in _git(
        ["show", "--name-only", "--pretty=", sha], cwd
    ).splitlines() if line.strip()]


def _existed_at(sha: str, path: str, cwd: Path) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{sha}:{path}"],
        cwd=cwd, capture_output=True, check=False,
    ).returncode == 0
