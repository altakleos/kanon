#!/usr/bin/env python3
"""Enforce ADR-0042 canonical exit-zero wording parity between two surfaces.

ADR-0042 §1 ratifies the canonical wording for what ``kanon verify`` exit-0
means. The same prose is embedded as the ``_ADR_0042_VERIFY_SCOPE`` constant in
``packages/kanon-core/src/kanon_core/cli.py``, surfaced via ``kanon verify
--help`` and cited in failure error messages.

ADR-0032's ``check_adr_immutability.py`` gate freezes the ADR body but does
not check the CLI constant. If a contributor edits the constant without
touching the ADR (or vice versa), no validator catches the drift. This gate
fills that gap.

The check is deliberately phrase-substring rather than byte-equality: the ADR
body is markdown (with ``- `` bullets); the CLI constant is a Python string
with ``\\n`` and indented continuation. Byte-equality would require either a
brittle one-way transform or refactoring the CLI to load the wording from the
ADR at runtime — too large for this gate. We assert that the four
load-bearing MUST-NOT clauses (each identified by a stable phrase) appear in
both surfaces. Any change that drops a clause from either surface fires the
gate; reformatting that preserves all four claims stays green.

Exit 0 if every required phrase is present in both surfaces. Exit 1 with a
structured per-violation message otherwise.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# The four MUST-NOT clauses ratified in ADR-0042 §1, identified by a stable
# substring that uniquely appears in each clause. If a future dialect bumps
# the wording, this list and ADR-0042's body change in the same commit.
REQUIRED_PHRASES: tuple[tuple[str, str], ...] = (
    ("good-engineering-practices", "good engineering practices"),
    ("correctness-or-quality-endorsement", "correctness or quality endorsement"),
    ("static-structural-check", "static structural check"),
    ("semantically-correct-realizations", "semantically correct realizations"),
)

ADR_PATH = Path("docs/decisions/0042-verification-scope-of-exit-zero.md")
CLI_PATH = Path("packages/kanon-core/src/kanon_core/cli.py")
CONSTANT_NAME = "_ADR_0042_VERIFY_SCOPE"
ADR_SECTION_HEADING = "### 1. The canonical exit-zero wording"


def _extract_adr_section_1(adr_text: str) -> str:
    """Return the body of ADR-0042 §"1. The canonical exit-zero wording".

    The body is the prose between the ``### 1.`` heading and the next ``### ``
    heading at the same level. Raises ``ValueError`` if the section anchor
    isn't found — that itself is a fatal drift, since this gate's contract
    assumes the section exists at a stable name.
    """
    start = adr_text.find(ADR_SECTION_HEADING)
    if start < 0:
        raise ValueError(
            f"ADR-0042 missing expected section heading: {ADR_SECTION_HEADING!r}"
        )
    body_start = start + len(ADR_SECTION_HEADING)
    # Find the next "### " heading after the body starts. Anchored at line-start
    # so a "### " mid-paragraph won't trip the search.
    rest = adr_text[body_start:]
    next_h3 = rest.find("\n### ")
    if next_h3 < 0:
        # No following heading — body runs to end of file.
        return rest
    return rest[:next_h3]


def _extract_cli_constant(cli_text: str) -> str:
    """Return the string value of ``_ADR_0042_VERIFY_SCOPE`` in ``cli.py``.

    Uses the ``ast`` module so that string-concatenation expressions
    (``"foo\\n" "bar\\n"``) and parenthesised forms both resolve correctly.
    Raises ``ValueError`` if the constant is missing or its value isn't a
    plain string literal.
    """
    tree = ast.parse(cli_text)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == CONSTANT_NAME:
                value = node.value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    return value.value
                # Handle parenthesised concatenation of string literals.
                if isinstance(value, ast.BinOp):
                    try:
                        result = ast.literal_eval(value)
                    except ValueError:
                        result = None
                    if isinstance(result, str):
                        return result
                raise ValueError(
                    f"{CLI_PATH}: {CONSTANT_NAME} is not a plain string literal "
                    f"(got AST node {type(value).__name__})."
                )
    raise ValueError(
        f"{CLI_PATH}: constant {CONSTANT_NAME!r} not found at module level."
    )


def _normalise_whitespace(text: str) -> str:
    """Collapse all whitespace runs (newlines + indent + multi-space) to single
    spaces.

    Both surfaces wrap the canonical wording at different line widths — the
    ADR is markdown bullets, the CLI constant is a multi-line Python string
    with two-space continuation indent — and a future reformatter could
    re-flow either without altering the claim. Phrase matching runs against
    the normalised form so the gate stays scoped to claim-content drift, not
    formatting drift.
    """
    return " ".join(text.split())


def _check_phrases(text: str, surface_label: str) -> list[str]:
    """Return per-missing-phrase error messages, empty list if all present."""
    normalised = _normalise_whitespace(text)
    errors: list[str] = []
    for clause_id, phrase in REQUIRED_PHRASES:
        if phrase not in normalised:
            errors.append(
                f"{surface_label}: missing ADR-0042 §1 clause "
                f"{clause_id!r} (expected substring: {phrase!r})."
            )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repo root (default: current working directory).",
    )
    args = parser.parse_args(argv)
    root: Path = args.root.resolve()

    adr_path = root / ADR_PATH
    cli_path = root / CLI_PATH
    if not adr_path.is_file():
        print(f"FAIL: missing ADR file: {adr_path}", file=sys.stderr)
        return 1
    if not cli_path.is_file():
        print(f"FAIL: missing CLI source: {cli_path}", file=sys.stderr)
        return 1

    adr_text = adr_path.read_text(encoding="utf-8")
    cli_text = cli_path.read_text(encoding="utf-8")

    try:
        adr_section = _extract_adr_section_1(adr_text)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    try:
        cli_constant = _extract_cli_constant(cli_text)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    errors.extend(_check_phrases(adr_section, f"{ADR_PATH} §1"))
    errors.extend(_check_phrases(cli_constant, f"{CLI_PATH}:{CONSTANT_NAME}"))

    if errors:
        print(
            "FAIL: ADR-0042 wording parity broken. "
            "Per ADR-0042 §3 the canonical wording is immutable; any change "
            "ships as a superseding ADR.",
            file=sys.stderr,
        )
        for msg in errors:
            print(f"  - {msg}", file=sys.stderr)
        return 1

    print("OK: ADR-0042 wording parity holds across ADR §1 + CLI constant.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
