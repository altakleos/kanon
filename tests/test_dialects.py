"""Phase A.6b: dialect-grammar validator tests.

Per ADR-0041 / docs/specs/dialect-grammar.md / docs/design/dialect-grammar.md.
Exercises ``_dialects.validate_dialect_pin`` directly. Wiring into `_manifest.py`
load path is deferred to a later sub-plan; these tests validate the contract.
"""

from __future__ import annotations

import click
import pytest

from kanon import _dialects
from kanon._dialects import (
    DEPRECATION_WARNING_BEFORE,
    SUPPORTED_DIALECTS,
    validate_dialect_pin,
)

# --- Module-level constants ---


def test_supported_dialects_contains_v1_2026_05_01() -> None:
    """Per ADR-0041, the v0.4 substrate ships v1 dialect = 2026-05-01."""
    assert "2026-05-01" in SUPPORTED_DIALECTS


def test_deprecation_warning_before_is_empty_in_v0_4() -> None:
    """Nothing deprecated yet; first supersession will populate this."""
    assert DEPRECATION_WARNING_BEFORE == ()


# --- INV-dialect-grammar-version-format: supported pin passes silently ---


def test_supported_pin_passes_silently(capfd: pytest.CaptureFixture[str]) -> None:
    validate_dialect_pin("2026-05-01")
    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == ""


# --- INV-dialect-grammar-pin-required: missing pin raises ---


def test_missing_pin_none_raises() -> None:
    with pytest.raises(click.ClickException, match="missing required `kanon-dialect:`"):
        validate_dialect_pin(None)


def test_missing_pin_empty_string_raises() -> None:
    with pytest.raises(click.ClickException, match="missing required `kanon-dialect:`"):
        validate_dialect_pin("")


def test_missing_pin_error_includes_supported_in_suggestion() -> None:
    with pytest.raises(click.ClickException) as excinfo:
        validate_dialect_pin(None)
    # The error text suggests the latest supported dialect.
    assert "2026-05-01" in str(excinfo.value)


def test_missing_pin_cites_invariant() -> None:
    with pytest.raises(click.ClickException, match="INV-dialect-grammar-pin-required"):
        validate_dialect_pin(None)


# --- INV-dialect-grammar-version-format: unknown pin raises ---


def test_unknown_dialect_raises() -> None:
    with pytest.raises(click.ClickException, match="unsupported"):
        validate_dialect_pin("unknown")


def test_unknown_dialect_error_lists_supported() -> None:
    with pytest.raises(click.ClickException) as excinfo:
        validate_dialect_pin("unknown")
    assert "2026-05-01" in str(excinfo.value)


def test_unknown_dialect_cites_invariant() -> None:
    with pytest.raises(click.ClickException, match="INV-dialect-grammar-version-format"):
        validate_dialect_pin("unknown")


def test_future_dialect_raises_until_substrate_ships_it() -> None:
    """A pin like 2099-01-01 isn't yet shipped; substrate refuses."""
    with pytest.raises(click.ClickException, match="unsupported"):
        validate_dialect_pin("2099-01-01")


def test_past_dialect_raises_when_not_in_supported() -> None:
    """A pin from before v0.4 (e.g., a hypothetical 2025-01-01) is rejected."""
    with pytest.raises(click.ClickException, match="unsupported"):
        validate_dialect_pin("2025-01-01")


def test_malformed_pin_raises() -> None:
    """Substrate doesn't try to parse format; missing-from-allowlist suffices."""
    with pytest.raises(click.ClickException, match="unsupported"):
        validate_dialect_pin("not-a-date-at-all")


# --- source label in error messages ---


def test_source_label_prefixes_missing_pin_error() -> None:
    with pytest.raises(click.ClickException, match="kanon-fintech-compliance:"):
        validate_dialect_pin(None, source="kanon-fintech-compliance")


def test_source_label_prefixes_unknown_pin_error() -> None:
    with pytest.raises(click.ClickException, match="acme-strict:"):
        validate_dialect_pin("2099-01-01", source="acme-strict")


# --- Deprecation warning (synthetic via monkeypatch) ---


def test_deprecation_warning_fires_when_pin_in_deprecation_list(
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """Inject a deprecated dialect via monkeypatch; assert stderr warning."""
    monkeypatch.setattr(_dialects, "DEPRECATION_WARNING_BEFORE", ("2026-05-01",))
    validate_dialect_pin("2026-05-01")
    captured = capfd.readouterr()
    assert "deprecated" in captured.err
    assert "2026-05-01" in captured.err
    assert "supersession" in captured.err


def test_deprecation_warning_does_not_fire_for_undeprecated_pin(
    capfd: pytest.CaptureFixture[str],
) -> None:
    validate_dialect_pin("2026-05-01")  # not in DEPRECATION_WARNING_BEFORE today
    captured = capfd.readouterr()
    assert captured.err == ""


def test_deprecation_warning_includes_source_label(
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(_dialects, "DEPRECATION_WARNING_BEFORE", ("2026-05-01",))
    validate_dialect_pin("2026-05-01", source="kanon-sdd")
    captured = capfd.readouterr()
    assert "kanon-sdd:" in captured.err


# --- Spec/impl parity per docs/specs/dialect-grammar.md "Structured error
# codes — normative emitter map".


def test_missing_pin_raises_dialect_pin_error_with_spec_code() -> None:
    """Missing pin → typed DialectPinError carrying spec-aligned `code`."""
    from kanon._dialects import DialectPinError

    with pytest.raises(DialectPinError) as exc_info:
        validate_dialect_pin(None, source="acme-x")
    assert exc_info.value.code == "missing-dialect-pin"


def test_unknown_pin_raises_dialect_pin_error_with_spec_code() -> None:
    """Unsupported pin → typed DialectPinError carrying spec-aligned `code`."""
    from kanon._dialects import DialectPinError

    with pytest.raises(DialectPinError) as exc_info:
        validate_dialect_pin("9999-12-31", source="acme-x")
    assert exc_info.value.code == "unknown-dialect"


def test_dialect_pin_error_subclasses_click_exception() -> None:
    """Backward-compat: DialectPinError still catchable as click.ClickException."""
    import click

    from kanon._dialects import DialectPinError

    assert issubclass(DialectPinError, click.ClickException)

