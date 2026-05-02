"""Phase A.6c: realization-shape parser + validator tests.

Per ADR-0041 / docs/specs/dialect-grammar.md / docs/design/dialect-grammar.md.
Exercises ``_realization_shape`` directly. Wiring into `_resolutions.py` replay
path is deferred to a later sub-plan; these tests validate the contract.
"""

from __future__ import annotations

import click
import pytest

from kanon._realization_shape import (
    V1_DIALECT_VERBS,
    RealizationShape,
    parse_realization_shape,
    validate_resolution_against_shape,
)

_V1 = "2026-05-01"


# --- V1 dialect verb enumeration ---


def test_v1_dialect_verbs_contains_canonical_nine() -> None:
    expected = {
        "lint", "test", "typecheck", "format",
        "scan", "audit", "sign", "publish", "report",
    }
    assert expected == V1_DIALECT_VERBS


# --- Parser: success path ---


def test_parser_returns_realization_shape() -> None:
    shape = parse_realization_shape(
        {
            "verbs": ["lint", "test"],
            "evidence-kinds": ["config-file", "ci-workflow"],
            "stages": ["commit", "push"],
        },
        dialect=_V1,
    )
    assert isinstance(shape, RealizationShape)
    assert shape.verbs == {"lint", "test"}
    assert shape.evidence_kinds == {"config-file", "ci-workflow"}
    assert shape.stages == {"commit", "push"}
    assert shape.additional_properties is False


def test_parser_accepts_additional_properties_true() -> None:
    shape = parse_realization_shape(
        {
            "verbs": [],
            "evidence-kinds": [],
            "stages": [],
            "additional-properties": True,
        },
        dialect=_V1,
    )
    assert shape.additional_properties is True


# --- Parser: failure paths ---


def test_parser_rejects_non_dict_input() -> None:
    with pytest.raises(click.ClickException, match="must be a mapping"):
        parse_realization_shape(["not", "a", "dict"], dialect=_V1)


def test_parser_rejects_missing_verbs_key() -> None:
    with pytest.raises(click.ClickException, match="missing required key 'verbs'"):
        parse_realization_shape(
            {"evidence-kinds": [], "stages": []}, dialect=_V1
        )


def test_parser_rejects_missing_evidence_kinds_key() -> None:
    with pytest.raises(click.ClickException, match="missing required key 'evidence-kinds'"):
        parse_realization_shape({"verbs": [], "stages": []}, dialect=_V1)


def test_parser_rejects_missing_stages_key() -> None:
    with pytest.raises(click.ClickException, match="missing required key 'stages'"):
        parse_realization_shape({"verbs": [], "evidence-kinds": []}, dialect=_V1)


def test_parser_rejects_non_list_verbs() -> None:
    with pytest.raises(click.ClickException, match="verbs must be a list"):
        parse_realization_shape(
            {"verbs": "lint", "evidence-kinds": [], "stages": []}, dialect=_V1
        )


def test_parser_rejects_unknown_verb() -> None:
    with pytest.raises(click.ClickException, match="not in dialect"):
        parse_realization_shape(
            {"verbs": ["bogus-verb"], "evidence-kinds": [], "stages": []},
            dialect=_V1,
        )


def test_parser_rejects_non_bool_additional_properties() -> None:
    with pytest.raises(click.ClickException, match="must be a bool"):
        parse_realization_shape(
            {
                "verbs": [],
                "evidence-kinds": [],
                "stages": [],
                "additional-properties": "yes",
            },
            dialect=_V1,
        )


def test_parser_rejects_unsupported_dialect() -> None:
    with pytest.raises(click.ClickException, match="unsupported dialect"):
        parse_realization_shape(
            {"verbs": [], "evidence-kinds": [], "stages": []},
            dialect="2099-01-01",
        )


def test_parser_source_label_in_error() -> None:
    with pytest.raises(click.ClickException, match="kanon-testing/preflight:"):
        parse_realization_shape(
            "not a dict",
            dialect=_V1,
            source="kanon-testing/preflight",
        )


# --- Validator: clean resolution ---


def test_validator_clean_resolution_returns_empty_list() -> None:
    shape = RealizationShape(
        verbs=frozenset({"lint", "test"}),
        evidence_kinds=frozenset({"config-file"}),
        stages=frozenset({"commit"}),
    )
    findings = validate_resolution_against_shape(
        realized_by=[
            {"label": "lint", "invocation": "ruff check .", "invocation-form": "shell"},
        ],
        evidence=[{"path": "pyproject.toml", "sha": "x", "kind": "config-file"}],
        shape=shape,
    )
    assert findings == []


# --- Validator: failure paths ---


def test_validator_invalid_verb_surfaces() -> None:
    shape = RealizationShape(
        verbs=frozenset({"lint"}),
        evidence_kinds=frozenset(),
        stages=frozenset(),
    )
    findings = validate_resolution_against_shape(
        realized_by=[{"label": "test", "invocation": "pytest"}],
        evidence=[],
        shape=shape,
        contract="kanon-x/preflight",
    )
    # Per docs/specs/dialect-grammar.md INV 4: every shape mismatch uses the
    # spec-aligned `code: shape-violation`. The impl-specific kind survives
    # in `subcode` for diagnostic granularity.
    assert any(
        f.code == "shape-violation"
        and f.subcode == "invalid-verb"
        and f.contract == "kanon-x/preflight"
        for f in findings
    )


def test_validator_invalid_evidence_kind_surfaces() -> None:
    shape = RealizationShape(
        verbs=frozenset(),
        evidence_kinds=frozenset({"config-file"}),
        stages=frozenset(),
    )
    findings = validate_resolution_against_shape(
        realized_by=[],
        evidence=[{"path": "x", "sha": "y", "kind": "build-script"}],
        shape=shape,
    )
    assert any(
        f.code == "shape-violation" and f.subcode == "invalid-evidence-kind"
        for f in findings
    )


def test_validator_invalid_stage_surfaces() -> None:
    shape = RealizationShape(
        verbs=frozenset({"lint"}),
        evidence_kinds=frozenset(),
        stages=frozenset({"commit"}),
    )
    findings = validate_resolution_against_shape(
        realized_by=[{"label": "lint", "stage": "release"}],
        evidence=[],
        shape=shape,
    )
    assert any(
        f.code == "shape-violation" and f.subcode == "invalid-stage"
        for f in findings
    )


def test_validator_accumulates_findings_no_early_exit() -> None:
    """Multiple violations all surface — consumer sees them in one pass."""
    shape = RealizationShape(
        verbs=frozenset({"lint"}),
        evidence_kinds=frozenset({"config-file"}),
        stages=frozenset({"commit"}),
    )
    findings = validate_resolution_against_shape(
        realized_by=[
            {"label": "test"},  # invalid verb
            {"label": "lint", "stage": "release"},  # invalid stage
        ],
        evidence=[{"path": "x", "sha": "y", "kind": "build-script"}],  # invalid kind
        shape=shape,
    )
    # Every finding carries the spec-aligned `code: shape-violation`. The
    # diagnostic subcodes accumulate independently so consumers see them all.
    assert {f.code for f in findings} == {"shape-violation"}
    subcodes = {f.subcode for f in findings}
    assert "invalid-verb" in subcodes
    assert "invalid-stage" in subcodes
    assert "invalid-evidence-kind" in subcodes


def test_validator_unknown_key_surfaces_when_additional_properties_false() -> None:
    shape = RealizationShape(
        verbs=frozenset({"lint"}),
        evidence_kinds=frozenset(),
        stages=frozenset(),
        additional_properties=False,
    )
    findings = validate_resolution_against_shape(
        realized_by=[
            {"label": "lint", "rogue-key": "value"},
        ],
        evidence=[],
        shape=shape,
    )
    assert any(
        f.code == "shape-violation" and f.subcode == "unknown-key" for f in findings
    )


def test_validator_unknown_key_silent_when_additional_properties_true() -> None:
    shape = RealizationShape(
        verbs=frozenset({"lint"}),
        evidence_kinds=frozenset(),
        stages=frozenset(),
        additional_properties=True,
    )
    findings = validate_resolution_against_shape(
        realized_by=[
            {"label": "lint", "rogue-key": "value"},
        ],
        evidence=[],
        shape=shape,
    )
    assert findings == []


def test_validator_evidence_without_kind_field_passes() -> None:
    """v1 spec: kind: is optional on evidence entries."""
    shape = RealizationShape(
        verbs=frozenset(),
        evidence_kinds=frozenset({"config-file"}),
        stages=frozenset(),
    )
    findings = validate_resolution_against_shape(
        realized_by=[],
        evidence=[{"path": "x", "sha": "y"}],  # no kind:
        shape=shape,
    )
    assert findings == []


# --- Spec/impl parity per docs/specs/dialect-grammar.md "Structured error
# codes — normative emitter map".


def test_shape_parse_error_carries_spec_code() -> None:
    """Malformed shape → typed ShapeParseError with spec-aligned `code`."""
    import pytest as _pt

    from kanon._realization_shape import ShapeParseError, parse_realization_shape

    with _pt.raises(ShapeParseError) as exc_info:
        parse_realization_shape(
            {"verbs": "not-a-list"}, dialect="2026-05-01"
        )
    assert exc_info.value.code == "invalid-realization-shape"


def test_shape_parse_error_subclasses_click_exception() -> None:
    """Backward-compat: ShapeParseError still catchable as click.ClickException."""
    import click

    from kanon._realization_shape import ShapeParseError

    assert issubclass(ShapeParseError, click.ClickException)


def test_shape_validation_error_default_code_is_shape_violation() -> None:
    """Per spec INV 4: every shape mismatch's `code` field is `shape-violation`."""
    from kanon._realization_shape import ShapeValidationError

    err = ShapeValidationError(subcode="invalid-verb", contract="x", detail="y")
    assert err.code == "shape-violation"
    assert err.subcode == "invalid-verb"


# --- Cardinality lock per plan v040a1-followup AC5: V1_DIALECT_VERBS must
# stay at 9 verbs. Accidental drops fail fast.


def test_v1_dialect_verbs_count_is_nine() -> None:
    """v1 dialect (kanon-dialect: 2026-05-01) ships exactly 9 verbs per the
    enumeration in docs/specs/dialect-grammar.md / docs/design/dialect-grammar.md.
    Adding a verb requires an ADR-driven dialect supersession (per ADR-0041);
    silently dropping one would break every contract that pinned the v1
    dialect, so this cardinality lock is a guardrail."""
    from kanon._realization_shape import V1_DIALECT_VERBS

    assert len(V1_DIALECT_VERBS) == 9, (
        f"V1_DIALECT_VERBS has {len(V1_DIALECT_VERBS)} entries; expected 9. "
        f"Current set: {sorted(V1_DIALECT_VERBS)!r}. If this is intentional, "
        "the change requires an ADR-driven dialect supersession per ADR-0041."
    )
    # Spot-check the canonical 9 are present.
    assert frozenset({
        "lint", "test", "typecheck", "format",
        "scan", "audit", "sign", "publish", "report",
    }) == V1_DIALECT_VERBS


