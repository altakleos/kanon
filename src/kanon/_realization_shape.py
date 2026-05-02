"""Realization-shape — parser + resolution-against-shape validator.

Phase A.6c implementation per ADR-0041 (`docs/decisions/0041-realization-shape-dialect-grammar.md`),
design `docs/design/dialect-grammar.md` §"Realization-shape: concrete schema",
spec `docs/specs/dialect-grammar.md` (INV-dialect-grammar-realization-shape-required,
INV-dialect-grammar-shape-validates-resolutions).

A contract's `realization-shape:` frontmatter declares which verbs, evidence-kinds,
and stages a valid resolution may cite. The substrate validates resolutions against
the contract's declared shape at replay time. Wired into `_resolutions._replay_inner`
via `_validate_shape_against_contract` (PR #77); shape findings surface as
`ReplayError(code="shape-violation", ...)` with the historical impl-specific kind
preserved in `subcode:` ∈ `{invalid-verb, invalid-evidence-kind, invalid-stage,
unknown-key}`. Skip-when-absent: contracts without a `realization-shape:` block
are exempt (today's reference contracts don't declare one).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import click

# v1 dialect (kanon-dialect: 2026-05-01) verb enumeration.
# Per design §"The substrate's v1 dialect verb enumeration". Future dialects
# ship their own enumeration; A.6c hardcodes v1.
V1_DIALECT_VERBS: frozenset[str] = frozenset({
    "lint",        # static-analysis checks
    "test",        # automated test execution
    "typecheck",   # static type validation
    "format",      # code formatting verification
    "scan",        # security or dependency scanning
    "audit",       # compliance or licensing audit
    "sign",        # cryptographic signing
    "publish",     # release / deploy
    "report",      # informational output
})


# Mapping from dialect string → verb enumeration. v1 only for v0.4.
_DIALECT_VERB_REGISTRY: dict[str, frozenset[str]] = {
    "2026-05-01": V1_DIALECT_VERBS,
}


@dataclass(frozen=True)
class RealizationShape:
    """Parsed realization-shape declaration from a contract's frontmatter."""

    verbs: frozenset[str]
    evidence_kinds: frozenset[str]
    stages: frozenset[str]
    additional_properties: bool = False


class ShapeParseError(click.ClickException):
    """Typed realization-shape parse failure.

    Carries the spec-aligned ``code`` field per docs/specs/dialect-grammar.md
    INV 3 (``code: missing-realization-shape`` for absent declarations) and
    the impl-specific ``code: invalid-realization-shape`` for shape blocks
    that are present but malformed (missing required keys, wrong types,
    unsupported dialect, verbs outside the dialect enumeration).

    Subclassing click.ClickException preserves backward compatibility with
    existing `except click.ClickException` callers.
    """

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class ShapeValidationError:
    """One finding from validate_resolution_against_shape.

    Per docs/specs/dialect-grammar.md INV 4 ("Mismatches are
    `code: shape-violation` findings, never silent"), the spec-aligned
    public-facing ``code`` is always ``shape-violation``. The impl-specific
    diagnostic refinement (the kind of mismatch — which verb, which evidence
    kind, etc.) lives in ``subcode`` ∈ ``{invalid-verb, invalid-evidence-kind,
    invalid-stage, unknown-key}``. Tooling that pattern-matches on the spec's
    code reads ``code``; richer diagnostics read ``subcode``.
    """

    code: str = "shape-violation"
    subcode: str | None = None
    contract: str | None = None
    detail: str | None = None


def parse_realization_shape(
    raw: Any,
    *,
    dialect: str,
    source: str | None = None,
) -> RealizationShape:
    """Parse a contract's ``realization-shape:`` frontmatter block.

    Raises :class:`ShapeParseError` (a :class:`click.ClickException` subclass)
    with ``code: invalid-realization-shape`` for missing/malformed shape, an
    unsupported dialect, or verbs not in the dialect's verb enumeration.
    Spec INV 3's ``missing-realization-shape`` code is surfaced upstream by
    callers that detect the absence of a `realization-shape:` block before
    calling this function (e.g., ``cli.py:contracts_validate``).

    *source* is an optional human-readable label (contract id, file path)
    prepended to error messages for diagnostics.
    """
    prefix = f"{source}: " if source else ""
    if dialect not in _DIALECT_VERB_REGISTRY:
        raise ShapeParseError(
            f"{prefix}realization-shape: unsupported dialect {dialect!r}; "
            f"supported: {sorted(_DIALECT_VERB_REGISTRY)!r}.",
            code="invalid-realization-shape",
        )
    if not isinstance(raw, dict):
        raise ShapeParseError(
            f"{prefix}realization-shape must be a mapping "
            f"(got {type(raw).__name__}).",
            code="invalid-realization-shape",
        )
    for required_key in ("verbs", "evidence-kinds", "stages"):
        if required_key not in raw:
            raise ShapeParseError(
                f"{prefix}realization-shape missing required key {required_key!r}.",
                code="invalid-realization-shape",
            )
    verbs_raw = raw["verbs"]
    if not isinstance(verbs_raw, list):
        raise ShapeParseError(
            f"{prefix}realization-shape.verbs must be a list "
            f"(got {type(verbs_raw).__name__}).",
            code="invalid-realization-shape",
        )
    dialect_verbs = _DIALECT_VERB_REGISTRY[dialect]
    invalid_verbs = [v for v in verbs_raw if v not in dialect_verbs]
    if invalid_verbs:
        raise ShapeParseError(
            f"{prefix}realization-shape.verbs contains verb(s) not in "
            f"dialect {dialect!r}: {invalid_verbs!r}; "
            f"valid verbs: {sorted(dialect_verbs)!r}.",
            code="invalid-realization-shape",
        )
    evidence_kinds_raw = raw["evidence-kinds"]
    if not isinstance(evidence_kinds_raw, list):
        raise ShapeParseError(
            f"{prefix}realization-shape.evidence-kinds must be a list "
            f"(got {type(evidence_kinds_raw).__name__}).",
            code="invalid-realization-shape",
        )
    stages_raw = raw["stages"]
    if not isinstance(stages_raw, list):
        raise ShapeParseError(
            f"{prefix}realization-shape.stages must be a list "
            f"(got {type(stages_raw).__name__}).",
            code="invalid-realization-shape",
        )
    additional_properties_raw = raw.get("additional-properties", False)
    if not isinstance(additional_properties_raw, bool):
        raise ShapeParseError(
            f"{prefix}realization-shape.additional-properties must be a bool "
            f"(got {type(additional_properties_raw).__name__}).",
            code="invalid-realization-shape",
        )
    return RealizationShape(
        verbs=frozenset(verbs_raw),
        evidence_kinds=frozenset(evidence_kinds_raw),
        stages=frozenset(stages_raw),
        additional_properties=additional_properties_raw,
    )


def validate_resolution_against_shape(
    realized_by: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    shape: RealizationShape,
    *,
    contract: str | None = None,
) -> list[ShapeValidationError]:
    """Check a resolution's ``realized-by`` + ``evidence`` against the
    contract's declared shape.

    Returns a list of structured findings (empty list = clean). Multiple
    findings accumulate (no early exit) so consumers see every shape
    violation in one pass.
    """
    findings: list[ShapeValidationError] = []
    # Per spec INV 4: every shape mismatch is `code: shape-violation`. The
    # historical impl-specific labels (invalid-verb, invalid-evidence-kind,
    # invalid-stage, unknown-key) survive as `subcode` for diagnostics.
    for inv in realized_by or []:
        if not isinstance(inv, dict):
            findings.append(
                ShapeValidationError(
                    subcode="unknown-key",
                    contract=contract,
                    detail=(
                        f"realized-by entry must be a mapping "
                        f"(got {type(inv).__name__})"
                    ),
                )
            )
            continue
        verb = inv.get("verb") or inv.get("label")
        if verb is not None and verb not in shape.verbs:
            findings.append(
                ShapeValidationError(
                    subcode="invalid-verb",
                    contract=contract,
                    detail=(
                        f"realized-by verb {verb!r} not in shape.verbs "
                        f"{sorted(shape.verbs)!r}"
                    ),
                )
            )
        stage = inv.get("stage")
        if stage is not None and shape.stages and stage not in shape.stages:
            findings.append(
                ShapeValidationError(
                    subcode="invalid-stage",
                    contract=contract,
                    detail=(
                        f"realized-by stage {stage!r} not in shape.stages "
                        f"{sorted(shape.stages)!r}"
                    ),
                )
            )
        if not shape.additional_properties:
            allowed_keys = {"verb", "label", "invocation", "invocation-form", "stage"}
            unknown = set(inv) - allowed_keys
            if unknown:
                findings.append(
                    ShapeValidationError(
                        subcode="unknown-key",
                        contract=contract,
                        detail=(
                            f"realized-by entry has unknown key(s) "
                            f"{sorted(unknown)!r}; shape declares "
                            f"additional-properties=false"
                        ),
                    )
                )
    # Validate evidence kinds (when entries declare a `kind:` field).
    for ev in evidence or []:
        if not isinstance(ev, dict):
            continue
        kind = ev.get("kind")
        if (
            kind is not None
            and shape.evidence_kinds
            and kind not in shape.evidence_kinds
        ):
            findings.append(
                ShapeValidationError(
                    subcode="invalid-evidence-kind",
                    contract=contract,
                    detail=(
                        f"evidence kind {kind!r} not in shape.evidence-kinds "
                        f"{sorted(shape.evidence_kinds)!r}"
                    ),
                )
            )
    return findings
