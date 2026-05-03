"""Dialect grammar — supported-dialect registry + pin validation.

Phase A.6b implementation per ADR-0041 (`docs/decisions/0041-realization-shape-dialect-grammar.md`),
design `docs/design/dialect-grammar.md`, spec `docs/specs/dialect-grammar.md`.

Six dialect-grammar invariants the spec ratifies. This module enforces two of them
directly:

- INV-dialect-grammar-pin-required: every aspect manifest MUST pin `kanon-dialect:`
  (validate_dialect_pin raises on missing pin).
- INV-dialect-grammar-version-format: pin must match a substrate-supported dialect
  string (`YYYY-MM-DD` format, exact match against ``SUPPORTED_DIALECTS``).

The remaining four invariants (realization-shape-required, shape-validates-resolutions,
composition-acyclic, replaces-substitution) are enforced by the realization-shape
and composition modules (Phase A.6c and A.6d).

Wired into `_manifest.py:_load_aspects_from_entry_points` (PR #78); every
entry-point-discovered aspect's `kanon-dialect:` pin is validated at substrate
startup. All seven reference aspects carry `kanon-dialect: "2026-05-01"`. The
validator surfaces typed `DialectPinError` (subclass of `click.ClickException`)
carrying spec-aligned `code:` ∈ `{missing-dialect-pin, unknown-dialect}` per
docs/specs/dialect-grammar.md INV 1-2.
"""

from __future__ import annotations

import sys

import click

# The substrate's supported dialect set. v0.4 ships v1 only.
# Per ADR-0041 cadence: future dialects are added by ADR-driven supersession,
# not configuration. The substrate honours at least N-1 with a deprecation
# horizon (per INV-dialect-grammar-version-format).
SUPPORTED_DIALECTS: tuple[str, ...] = ("2026-05-01",)

# Dialects whose pin is supported but flagged for migration. Populated when
# the substrate ships its first supersession (e.g., when v0.5 introduces
# "2026-09-01", the prior "2026-05-01" entry moves into this list).
DEPRECATION_WARNING_BEFORE: tuple[str, ...] = ()


class DialectPinError(click.ClickException):
    """Typed dialect-pin validation failure.

    Carries the spec-aligned ``code`` field per docs/specs/dialect-grammar.md
    invariants 1-2: ``missing-dialect-pin`` (INV-dialect-grammar-pin-required)
    or ``unknown-dialect`` (INV-dialect-grammar-version-format). Callers
    (the CLI verb `kanon contracts validate`, the entry-point loader in
    `_load_aspects_from_entry_points`) read ``exc.code`` to surface the
    spec's structured code in their JSON output instead of inventing one.

    Subclassing click.ClickException preserves backward compatibility with
    existing `except click.ClickException` callers.
    """

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def validate_dialect_pin(
    manifest_dialect: str | None,
    *,
    source: str | None = None,
) -> None:
    """Validate a manifest's ``kanon-dialect:`` pin.

    Raises :class:`DialectPinError` (a :class:`click.ClickException` subclass)
    carrying spec-aligned ``code`` for:

    - Missing pin (``None`` or empty string) — ``code: missing-dialect-pin``
      (per INV-dialect-grammar-pin-required, docs/specs/dialect-grammar.md).
    - Unknown pin (not in :data:`SUPPORTED_DIALECTS`) — ``code: unknown-dialect``
      (per INV-dialect-grammar-version-format, docs/specs/dialect-grammar.md).

    Emits a stderr deprecation warning when the pin matches a dialect listed in
    :data:`DEPRECATION_WARNING_BEFORE` (substrate still honours, but consumer
    should migrate before next supersession).

    *source* is an optional human-readable label (e.g., aspect slug or
    publisher name) prepended to the error message for diagnostics.
    """
    prefix = f"{source}: " if source else ""
    if manifest_dialect is None or manifest_dialect == "":
        raise DialectPinError(
            f"{prefix}missing required `kanon-dialect:` pin "
            f"(per INV-dialect-grammar-pin-required); "
            f"add `kanon-dialect: {SUPPORTED_DIALECTS[-1]}` to the manifest.",
            code="missing-dialect-pin",
        )
    if manifest_dialect not in SUPPORTED_DIALECTS:
        raise DialectPinError(
            f"{prefix}unsupported `kanon-dialect:` pin {manifest_dialect!r} "
            f"(per INV-dialect-grammar-version-format); "
            f"this substrate supports {list(SUPPORTED_DIALECTS)!r}.",
            code="unknown-dialect",
        )
    if manifest_dialect in DEPRECATION_WARNING_BEFORE:
        sys.stderr.write(
            f"warning: {prefix}`kanon-dialect: {manifest_dialect!r}` is "
            f"deprecated; migrate to {SUPPORTED_DIALECTS[-1]!r} before the "
            f"next dialect supersession.\n"
        )
