"""README invariants for the v0.4 protocol-substrate framing.

Per plan v040a1-release-prep PR 4: README must reflect ADR-0048 (kanon as
protocol substrate, not kit) and ADR-0045 Phase A.5 (bare-name CLI shorthand
deprecated) on its first-impression surface. Specifically: the first 80
lines of README.md (everything a casual reader sees before scrolling) must
NOT carry the retired v0.3 vocabulary.

This test fails fast if a future commit re-introduces v0.3 framing — a
common drift mode when copying examples from old docs.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_README = Path(__file__).resolve().parent.parent / "README.md"

# Phrases retired by the v0.4 pivot. None of these may appear in the
# first-impression surface (lines 1-80) of README.md.
_RETIRED_PHRASES = (
    # ADR-0048: the kit-shape framing is retired in favour of protocol substrate.
    "development-discipline kit",
    # ADR-0045 Phase A.5: --tier CLI flag is deprecated.
    "--tier ",
)

# Bare-name CLI usages (e.g., `kanon aspect set-depth . sdd 2`). The
# bare-name shorthand is deprecated per ADR-0045 Phase A.5; canonical form
# is `kanon-<local>`. Match: bare name preceded by whitespace (NOT a hyphen,
# so `kanon-sdd 2` doesn't trip) followed by a space and a digit (the depth).
_BARE_NAME_CLI_PATTERN = re.compile(
    r"(?:\s|^)(sdd|worktrees|testing|security|deps|release|fidelity)\s+\d"
)


@pytest.fixture(scope="module")
def first_80_lines() -> str:
    text = _README.read_text(encoding="utf-8")
    return "\n".join(text.splitlines()[:80])


def test_readme_first_80_lines_avoid_retired_v03_phrases(first_80_lines: str) -> None:
    """The README's first-impression surface must not carry v0.3 framing."""
    found = [p for p in _RETIRED_PHRASES if p in first_80_lines]
    assert not found, (
        f"README first 80 lines contain retired v0.3 phrases: {found!r}. "
        "These must be replaced with the v0.4 protocol-substrate framing "
        "per ADR-0048 / ADR-0045."
    )


def test_readme_first_80_lines_avoid_bare_name_cli_examples(
    first_80_lines: str,
) -> None:
    """Bare-name CLI shorthand is deprecated per ADR-0045 Phase A.5."""
    matches = _BARE_NAME_CLI_PATTERN.findall(first_80_lines)
    assert not matches, (
        f"README first 80 lines contain deprecated bare-name CLI usage "
        f"(e.g., 'sdd 2'): {matches!r}. Use the canonical 'kanon-<local>' "
        "form (e.g., 'kanon-sdd 2')."
    )


def test_readme_advertises_protocol_substrate_framing(first_80_lines: str) -> None:
    """Positive assertion: ADR-0048's framing is present in the README opener."""
    flat = " ".join(first_80_lines.split())
    assert "protocol substrate" in flat, (
        "README first 80 lines must describe kanon as a protocol substrate "
        "per ADR-0048."
    )
    assert "ADR-0048" in flat, (
        "README first 80 lines must cite ADR-0048 (the protocol-substrate "
        "commitment) for traceability."
    )
