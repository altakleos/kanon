"""Fidelity-replay engine tests.

The engine itself ships in Track 1 of `docs/plans/fidelity-and-immutability.md`.
This file exists at Track 0 to satisfy the spec→fixture binding for INV-10
(`INV-verification-contract-fidelity-replay-carveout`) without forward-pointing
at a missing path.

Track 1 will add the real engine tests:
- ``test_replay_engine_honours_invariant_bounds`` — INV-10 bounds enforced
- ``test_forbidden_phrases_match`` / ``test_required_one_of_match`` /
  ``test_required_all_of_match`` — assertion families
- ``test_aspect_gate_off_means_no_replay`` — INV-10.3 gating
"""

from __future__ import annotations

from pathlib import Path

import pytest


def test_invariant_anchor_resolves() -> None:
    """Anchor test for INV-verification-contract-fidelity-replay-carveout.

    Asserts that the spec carries the carve-out anchor and ADR-0029 exists.
    Replaced in Track 1 by behavioural tests once the engine ships.
    """
    repo = Path(__file__).resolve().parents[1]
    spec = repo / "docs" / "specs" / "verification-contract.md"
    text = spec.read_text(encoding="utf-8")
    assert "INV-verification-contract-fidelity-replay-carveout" in text, (
        "verification-contract.md must declare INV-10 (the fidelity carve-out)"
    )
    adr = repo / "docs" / "decisions" / "0029-verification-fidelity-replay-carveout.md"
    assert adr.is_file(), "ADR-0029 must exist to ratify INV-10"


@pytest.mark.skip(reason="Awaiting Track 1: kanon-fidelity engine (_fidelity.py + manifest).")
def test_replay_engine_honours_invariant_bounds() -> None:
    """Placeholder for the real engine test — Track 1.

    Will assert that the lexical replay engine refuses to issue subprocess,
    LLM, or import calls — exactly INV-10.1's text-only constraint.
    """
