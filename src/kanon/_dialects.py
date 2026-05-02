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

Wiring into `_manifest.py` load-time validation lands in a later sub-plan, coupled
with adding `kanon-dialect:` to actual aspect manifests (currently they don't carry it).
The validator is exercised via direct tests in `tests/test_dialects.py`.
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


def validate_dialect_pin(
    manifest_dialect: str | None,
    *,
    source: str | None = None,
) -> None:
    """Validate a manifest's ``kanon-dialect:`` pin.

    Raises :class:`click.ClickException` for:

    - Missing pin (``None`` or empty string) — INV-dialect-grammar-pin-required.
    - Unknown pin (not in :data:`SUPPORTED_DIALECTS`) — INV-dialect-grammar-version-format.

    Emits a stderr deprecation warning when the pin matches a dialect listed in
    :data:`DEPRECATION_WARNING_BEFORE` (substrate still honours, but consumer
    should migrate before next supersession).

    *source* is an optional human-readable label (e.g., aspect slug or
    publisher name) prepended to the error message for diagnostics.
    """
    prefix = f"{source}: " if source else ""
    if manifest_dialect is None or manifest_dialect == "":
        raise click.ClickException(
            f"{prefix}missing required `kanon-dialect:` pin "
            f"(per INV-dialect-grammar-pin-required); "
            f"add `kanon-dialect: {SUPPORTED_DIALECTS[-1]}` to the manifest."
        )
    if manifest_dialect not in SUPPORTED_DIALECTS:
        raise click.ClickException(
            f"{prefix}unsupported `kanon-dialect:` pin {manifest_dialect!r} "
            f"(per INV-dialect-grammar-version-format); "
            f"this substrate supports {list(SUPPORTED_DIALECTS)!r}."
        )
    if manifest_dialect in DEPRECATION_WARNING_BEFORE:
        sys.stderr.write(
            f"warning: {prefix}`kanon-dialect: {manifest_dialect!r}` is "
            f"deprecated; migrate to {SUPPORTED_DIALECTS[-1]!r} before the "
            f"next dialect supersession.\n"
        )
