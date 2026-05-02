"""Phase A.6d: composition algebra tests.

Per ADR-0041 §Decision 3, docs/specs/dialect-grammar.md
(INV-dialect-grammar-composition-acyclic, INV-dialect-grammar-replaces-substitution),
docs/design/dialect-grammar.md §"Composition resolution algorithm".
"""

from __future__ import annotations

from kanon._composition import (
    ContractRef,
    compose,
)


def _ids(refs: list[ContractRef]) -> list[str]:
    return [r.contract_id for r in refs]


# --- Smoke ---


def test_empty_contracts_returns_empty() -> None:
    ordering, findings = compose([], surface="preflight.commit")
    assert ordering == []
    assert findings == []


def test_no_contracts_match_surface() -> None:
    contracts = [ContractRef("kanon-x/a", "release-gate.tag")]
    ordering, findings = compose(contracts, surface="preflight.commit")
    assert ordering == []
    assert findings == []


def test_single_contract() -> None:
    contracts = [ContractRef("kanon-x/a", "preflight.commit")]
    ordering, findings = compose(contracts, surface="preflight.commit")
    assert _ids(ordering) == ["kanon-x/a"]
    assert findings == []  # single contract has no ambiguity


# --- before / after edges ---


def test_before_orders_first() -> None:
    """A.before=[B] means A executes BEFORE B."""
    a = ContractRef("a", "s", before=("b",))
    b = ContractRef("b", "s")
    ordering, findings = compose([a, b], surface="s")
    assert _ids(ordering) == ["a", "b"]
    assert all(f.code != "composition-cycle" for f in findings)


def test_after_orders_first() -> None:
    """B.after=[A] also means A executes BEFORE B."""
    a = ContractRef("a", "s")
    b = ContractRef("b", "s", after=("a",))
    ordering, findings = compose([a, b], surface="s")
    assert _ids(ordering) == ["a", "b"]


def test_three_contract_chain() -> None:
    a = ContractRef("a", "s", before=("b",))
    b = ContractRef("b", "s", before=("c",))
    c = ContractRef("c", "s")
    ordering, _ = compose([a, b, c], surface="s")
    assert _ids(ordering) == ["a", "b", "c"]


# --- Cycles ---


def test_two_cycle_detected() -> None:
    a = ContractRef("a", "s", before=("b",))
    b = ContractRef("b", "s", before=("a",))
    ordering, findings = compose([a, b], surface="s")
    assert ordering == []
    cycle_errs = [f for f in findings if f.code == "composition-cycle"]
    assert len(cycle_errs) == 1
    assert "before/after cycle" in cycle_errs[0].detail
    assert "a" in cycle_errs[0].detail
    assert "b" in cycle_errs[0].detail


def test_self_loop_detected() -> None:
    a = ContractRef("a", "s", before=("a",))
    ordering, findings = compose([a], surface="s")
    assert ordering == []
    assert any(f.code == "composition-cycle" for f in findings)


def test_three_cycle_detected() -> None:
    a = ContractRef("a", "s", before=("b",))
    b = ContractRef("b", "s", before=("c",))
    c = ContractRef("c", "s", before=("a",))
    ordering, findings = compose([a, b, c], surface="s")
    assert ordering == []
    assert any(f.code == "composition-cycle" for f in findings)


# --- Ambiguity ---


def test_unrelated_contracts_emit_ambiguity_warning() -> None:
    a = ContractRef("a", "s")
    b = ContractRef("b", "s")
    ordering, findings = compose([a, b], surface="s")
    # Both present, alphabetical fallback.
    assert _ids(ordering) == ["a", "b"]
    ambiguity_warns = [f for f in findings if f.code == "ambiguous-composition"]
    assert len(ambiguity_warns) == 1


def test_chained_contracts_no_ambiguity() -> None:
    """When all contracts are related via before/after, no ambiguity warning."""
    a = ContractRef("a", "s", before=("b",))
    b = ContractRef("b", "s")
    _, findings = compose([a, b], surface="s")
    assert all(f.code != "ambiguous-composition" for f in findings)


# --- replaces ---


def test_replaces_drops_replaced() -> None:
    a = ContractRef("a", "s")
    b = ContractRef("b", "s", replaces=("a",))
    ordering, findings = compose([a, b], surface="s")
    assert _ids(ordering) == ["b"]
    assert all(f.code != "composition-cycle" for f in findings)


def test_replaces_chain() -> None:
    """A replaces B, C replaces A (effectively all dropped except C)."""
    a = ContractRef("a", "s", replaces=("b",))
    b = ContractRef("b", "s")
    c = ContractRef("c", "s", replaces=("a",))
    ordering, _ = compose([a, b, c], surface="s")
    assert _ids(ordering) == ["c"]


def test_replaces_cycle_detected() -> None:
    a = ContractRef("a", "s", replaces=("b",))
    b = ContractRef("b", "s", replaces=("a",))
    ordering, findings = compose([a, b], surface="s")
    assert ordering == []
    cycle_errs = [f for f in findings if f.code == "composition-cycle"]
    assert len(cycle_errs) == 1
    assert "replaces" in cycle_errs[0].detail


def test_replaces_target_not_in_bundle_passes_through() -> None:
    """A.replaces=[external-id] where external-id isn't in the bundle: A stays active."""
    a = ContractRef("a", "s", replaces=("external/contract",))
    ordering, _ = compose([a], surface="s")
    assert _ids(ordering) == ["a"]


# --- Stability ---


def test_stable_ordering_across_runs() -> None:
    """Same input always produces same output (alphabetical tie-break)."""
    contracts = [
        ContractRef("c", "s"),
        ContractRef("a", "s"),
        ContractRef("b", "s"),
    ]
    ordering1, _ = compose(contracts, surface="s")
    ordering2, _ = compose(contracts, surface="s")
    assert _ids(ordering1) == _ids(ordering2) == ["a", "b", "c"]
