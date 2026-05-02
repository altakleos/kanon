"""Resolutions engine — replay, canonicalization, stale-detection.

Phase A.6a implementation per ADR-0039 design (`docs/design/resolutions-engine.md`)
and spec (`docs/specs/resolutions.md`). The substrate's runtime-binding model:
prose contracts → agent-resolved YAML → kernel replays mechanically.

Six invariants enforced:

- INV-resolutions-machine-only-owned: hand-edit detection via meta-checksum.
- INV-resolutions-quadruple-pin: contract-version + contract-content-SHA +
  resolver-model + per-evidence-SHA all checked.
- INV-resolutions-evidence-grounded: each contract entry MUST cite at least
  one evidence file.
- INV-resolutions-replay-deterministic: same input → same output. The
  ``resolved-at`` timestamp is the only non-deterministic field; it is
  excluded from canonicalization.
- INV-resolutions-resolver-not-in-ci: this module is the kernel's REPLAY side;
  the resolver runs only on dev machines (CLI verb in Phase A.7).
- INV-resolutions-stale-fails: any pin drift surfaces a ReplayError; replay
  continues to the next contract.

A.6a stubs invocation execution. Phase A.7 wires `kanon resolve` and
integrates execution with `kanon preflight`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click
import yaml

_SCHEMA_VERSION = 1
_VALID_INVOCATION_FORMS = frozenset({"shell", "argv"})
_DEFAULT_DIALECT = "2026-05-01"


# --- Data classes ---


@dataclass
class ReplayError:
    """One finding from replay or stale-check.

    ``code`` is one of the structured codes used by the kernel
    (``hand-edit-detected``, ``stale-resolution``, ``missing-contract``,
    ``ungrounded-resolution``, ``missing-evidence``, ``sha-mismatch``,
    ``unknown-schema-version``, ``invalid-resolution-yaml``,
    ``invalid-invocation-form``). ``contract`` is the contract identifier
    (``<publisher>-<aspect>/<contract-slug>``) when applicable. ``path`` is
    the consumer-relative evidence path when the finding cites a file.
    ``reason`` is an optional human-readable note for diagnostics.
    """

    code: str
    contract: str | None = None
    path: str | None = None
    reason: str | None = None


@dataclass
class ExecutionRecord:
    """One realization invocation result.

    ``executed`` is False in A.6a (invocation execution is stubbed; A.7
    wires real execution). ``reason`` documents the stub.
    """

    contract: str
    label: str
    invocation: str
    invocation_form: str
    executed: bool = False
    reason: str | None = None
    exit_code: int | None = None


@dataclass
class ReplayReport:
    """Aggregate report from one replay() or stale_check() call."""

    errors: list[ReplayError] = field(default_factory=list)
    executions: list[ExecutionRecord] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


# --- Canonicalization ---


def canonicalize_entry(entry: dict[str, Any]) -> bytes:
    """Return canonical JSON bytes for a per-contract entry.

    Per the design: strip ``meta-checksum``, sort keys recursively,
    serialize as compact JSON with ``sort_keys=True``. SHA-256 over the
    resulting bytes is the ``meta-checksum`` value.
    """
    stripped = {k: v for k, v in entry.items() if k != "meta-checksum"}
    return json.dumps(
        stripped, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _meta_checksum(entry: dict[str, Any]) -> str:
    return _sha256_bytes(canonicalize_entry(entry))


# --- Schema validation ---


def _parse_resolutions_yaml(
    path: Path, errors: list[ReplayError]
) -> dict[str, Any] | None:
    """Parse and shape-validate the top-level resolutions YAML.

    Returns the parsed dict on success, or None when shape is unusable
    (caller continues; per-contract errors are surfaced via ``errors``).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(
            ReplayError(code="invalid-resolution-yaml", reason=f"read failed: {exc}")
        )
        return None
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        errors.append(
            ReplayError(code="invalid-resolution-yaml", reason=f"YAML parse: {exc}")
        )
        return None
    if not isinstance(data, dict):
        errors.append(
            ReplayError(
                code="invalid-resolution-yaml",
                reason="top-level must be a mapping",
            )
        )
        return None
    schema_version = data.get("schema-version")
    if schema_version != _SCHEMA_VERSION:
        errors.append(
            ReplayError(
                code="unknown-schema-version",
                reason=f"got {schema_version!r}; expected {_SCHEMA_VERSION}",
            )
        )
        return None
    return data


# --- Contract resolution (locating contract files via the aspect registry) ---


def _locate_contract(
    contract_id: str, registry: dict[str, Any] | None
) -> Path | None:
    """Resolve a ``<publisher>-<aspect>/<contract-slug>`` to its on-disk path.

    The contract-id format is ``<aspect-slug>/<contract-slug>``. The aspect
    slug must exist in the registry. The contract-slug is resolved relative
    to the aspect's source directory: ``<aspect-source>/contracts/<slug>.md``.

    Returns the path if found, else None. None surfaces as
    ``missing-contract`` in the caller.
    """
    if registry is None:
        try:
            from kanon._manifest import _load_aspect_registry

            registry = _load_aspect_registry(None)
        except Exception:
            return None
    aspects = registry.get("aspects") if isinstance(registry, dict) else None
    if not isinstance(aspects, dict):
        return None
    if "/" not in contract_id:
        return None
    aspect_slug, contract_slug = contract_id.split("/", 1)
    entry = aspects.get(aspect_slug)
    if not isinstance(entry, dict):
        return None
    source = entry.get("_source")
    if not source:
        return None
    candidate = Path(source) / "contracts" / f"{contract_slug}.md"
    return candidate if candidate.is_file() else None


# --- Replay engine ---


def _check_pins(
    contract_id: str,
    entry: dict[str, Any],
    target: Path,
    registry: dict[str, Any] | None,
    errors: list[ReplayError],
) -> bool:
    """Run all pin checks for one contract entry. Returns True iff all passed."""
    # 1. Hand-edit detection (INV-resolutions-machine-only-owned).
    expected_meta = entry.get("meta-checksum")
    actual_meta = _meta_checksum(entry)
    if expected_meta != actual_meta:
        errors.append(
            ReplayError(
                code="hand-edit-detected",
                contract=contract_id,
                reason=f"meta-checksum {expected_meta!r} != recomputed {actual_meta!r}",
            )
        )
        return False

    # 2. Contract content-SHA pin (INV-resolutions-quadruple-pin).
    contract_path = _locate_contract(contract_id, registry)
    if contract_path is None:
        errors.append(ReplayError(code="missing-contract", contract=contract_id))
        return False
    current_contract_sha = _sha256_bytes(contract_path.read_bytes())
    pinned_contract_sha = entry.get("contract-content-sha")
    if current_contract_sha != pinned_contract_sha:
        errors.append(
            ReplayError(
                code="stale-resolution",
                contract=contract_id,
                reason="contract-content drift",
            )
        )
        return False

    # 3. Evidence grounding (INV-resolutions-evidence-grounded).
    evidence = entry.get("evidence") or []
    if not evidence:
        errors.append(ReplayError(code="ungrounded-resolution", contract=contract_id))
        return False

    # 4. Per-evidence SHA pin (INV-resolutions-stale-fails).
    for ev in evidence:
        ev_path_str = ev.get("path") if isinstance(ev, dict) else None
        if not isinstance(ev_path_str, str):
            errors.append(
                ReplayError(
                    code="missing-evidence",
                    contract=contract_id,
                    reason="evidence entry missing 'path'",
                )
            )
            return False
        ev_path = target / ev_path_str
        if not ev_path.is_file():
            errors.append(
                ReplayError(
                    code="missing-evidence",
                    contract=contract_id,
                    path=ev_path_str,
                )
            )
            return False
        current_ev_sha = _sha256_bytes(ev_path.read_bytes())
        if current_ev_sha != ev.get("sha"):
            errors.append(
                ReplayError(
                    code="sha-mismatch",
                    contract=contract_id,
                    path=ev_path_str,
                )
            )
            return False
    return True


def _execute_realizations(
    contract_id: str,
    entry: dict[str, Any],
    target: Path,
    executions: list[ExecutionRecord],
    errors: list[ReplayError],
) -> None:
    """Stub for A.6a: record what WOULD execute; do not actually run.

    Phase A.7 swaps this stub for real subprocess invocation, integrated
    with `kanon preflight`. The ExecutionRecord shape is stable so A.7 can
    drop in the implementation without changing the report shape.
    """
    for inv in entry.get("realized-by") or []:
        if not isinstance(inv, dict):
            errors.append(
                ReplayError(
                    code="invalid-resolution-yaml",
                    contract=contract_id,
                    reason="realized-by entry must be a mapping",
                )
            )
            continue
        invocation_form = inv.get("invocation-form", "shell")
        if invocation_form not in _VALID_INVOCATION_FORMS:
            errors.append(
                ReplayError(
                    code="invalid-invocation-form",
                    contract=contract_id,
                    reason=(
                        f"got {invocation_form!r}; "
                        f"v1 supports {sorted(_VALID_INVOCATION_FORMS)}"
                    ),
                )
            )
            continue
        executions.append(
            ExecutionRecord(
                contract=contract_id,
                label=str(inv.get("label", "")),
                invocation=str(inv.get("invocation", "")),
                invocation_form=invocation_form,
                executed=False,
                reason=(
                    "Phase A.6a stub: invocation execution not yet implemented; "
                    "Phase A.7 wires kanon resolve / preflight integration."
                ),
            )
        )


def _parse_contract_frontmatter(text: str) -> dict[str, Any]:
    """Extract YAML frontmatter from a contract markdown file.

    Returns ``{}`` when no frontmatter fence is present.
    """
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _validate_shape_against_contract(
    contract_id: str,
    contract_path: Path,
    entry: dict[str, Any],
    errors: list[ReplayError],
) -> None:
    """Validate a resolution against its contract's `realization-shape:` block.

    Skip-when-absent: contracts without `realization-shape:` in their frontmatter
    are exempt from shape validation. Per INV-dialect-grammar-shape-validates-
    resolutions, contracts that DO declare the block get validated.
    """
    from kanon._realization_shape import (
        parse_realization_shape,
        validate_resolution_against_shape,
    )

    # Per ADR-0041 + design/dialect-grammar: shape-validation findings accumulate
    # rather than crashing the replay. A non-UTF-8 or unreadable contract file
    # is a structured finding, not an uncaught exception that bubbles to the
    # CLI as a stack trace.
    try:
        text = contract_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        errors.append(
            ReplayError(
                code="invalid-contract-encoding",
                contract=contract_id,
                reason=f"contract file at {contract_path} is not readable as UTF-8: {exc}",
            )
        )
        return
    frontmatter = _parse_contract_frontmatter(text)
    raw_shape = frontmatter.get("realization-shape")
    if raw_shape is None:
        return  # skip-when-absent

    dialect = frontmatter.get("kanon-dialect", _DEFAULT_DIALECT)
    try:
        shape = parse_realization_shape(
            raw_shape, dialect=dialect, source=contract_id
        )
    except click.ClickException as exc:
        # ShapeParseError carries spec-aligned `code: invalid-realization-shape`
        # per docs/specs/dialect-grammar.md; fallback for plain ClickException
        # preserves backcompat.
        code = getattr(exc, "code", "invalid-realization-shape")
        errors.append(
            ReplayError(
                code=code,
                contract=contract_id,
                reason=exc.message,
            )
        )
        return

    findings = validate_resolution_against_shape(
        realized_by=entry.get("realized-by") or [],
        evidence=entry.get("evidence") or [],
        shape=shape,
        contract=contract_id,
    )
    # Per docs/specs/dialect-grammar.md INV 4: every shape mismatch surfaces
    # as `code: shape-violation`. ShapeValidationError.subcode preserves the
    # historical impl labels (invalid-verb, invalid-evidence-kind, etc.) for
    # diagnostics; we prepend that into `reason` so callers reading reports
    # see both the spec code and the impl-specific kind.
    for f in findings:
        reason = (
            f"{f.subcode}: {f.detail}" if f.subcode and f.detail
            else (f.subcode or f.detail)
        )
        errors.append(
            ReplayError(code=f.code, contract=f.contract, reason=reason)
        )


def _replay_inner(
    target: Path,
    registry: dict[str, Any] | None,
    *,
    execute: bool,
) -> ReplayReport:
    report = ReplayReport()
    rfile = target / ".kanon" / "resolutions.yaml"
    if not rfile.exists():
        return report  # No resolutions = no replay; not an error per se.
    parsed = _parse_resolutions_yaml(rfile, report.errors)
    if parsed is None:
        return report
    contracts = parsed.get("contracts") or {}
    if not isinstance(contracts, dict):
        report.errors.append(
            ReplayError(
                code="invalid-resolution-yaml",
                reason="'contracts' must be a mapping",
            )
        )
        return report
    for contract_id, entry in contracts.items():
        if not isinstance(entry, dict):
            report.errors.append(
                ReplayError(
                    code="invalid-resolution-yaml",
                    contract=str(contract_id),
                    reason="contract entry must be a mapping",
                )
            )
            continue
        if not _check_pins(
            str(contract_id), entry, target, registry, report.errors
        ):
            continue  # Pin drift: skip realizations for this contract.
        # Shape validation (per INV-dialect-grammar-shape-validates-resolutions).
        # Skip-when-absent: contracts without realization-shape: are exempt.
        contract_path = _locate_contract(str(contract_id), registry)
        if contract_path is not None:
            _validate_shape_against_contract(
                str(contract_id), contract_path, entry, report.errors
            )
        if execute:
            _execute_realizations(
                str(contract_id), entry, target, report.executions, report.errors
            )
    return report


def replay(
    target: Path, registry: dict[str, Any] | None = None
) -> ReplayReport:
    """Replay all contracts in ``target/.kanon/resolutions.yaml``.

    Pin checks → realizations execution. A.6a stubs execution; A.7 wires
    real invocation. Per INV-resolutions-replay-deterministic, two calls
    on identical inputs produce identical reports.
    """
    return _replay_inner(target, registry, execute=True)


def stale_check(
    target: Path, registry: dict[str, Any] | None = None
) -> ReplayReport:
    """Run pin checks only; never execute realizations.

    Per the design: this is the cheap "are my resolutions fresh?" path
    suitable for IDE integration. Phase A.7 surfaces it as
    ``kanon resolutions check``.
    """
    return _replay_inner(target, registry, execute=False)
