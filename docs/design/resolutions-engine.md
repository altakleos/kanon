---
status: accepted
date: 2026-05-01
implements: docs/specs/resolutions.md
---
# Design: Resolutions engine — artifact format, replay algorithm, and the resolver/replayer split

## Context

[`docs/specs/resolutions.md`](../specs/resolutions.md) defines *what* a resolution is and what invariants the substrate enforces. This design doc specifies *how* the kernel implements those invariants: the YAML schema, the replay algorithm, the stale-detection algorithm, the resolver's contract with the kernel, and the Phase A implementation footprint.

[ADR-0039](../decisions/0039-contract-resolution-model.md) is the parent ratification.

## The artifact: `.kanon/resolutions.yaml`

### Top-level shape

```yaml
schema-version: 1
resolved-at: "2026-05-01T14:22:00Z"
resolver-environment:
  model: "claude-opus-4-7-2026-04-22"
  harness: "claude-code"
contracts:
  <publisher>-<aspect>/<contract-slug>:
    semantic-version: "1.0"
    contract-content-sha: "sha256:abc123..."
    realized-by:
      - label: "lint"
        invocation: "ruff check src/ tests/ ci/"
        invocation-form: "shell"
      - label: "test"
        invocation: "pytest -q"
        invocation-form: "shell"
    evidence:
      - path: "pyproject.toml"
        sha: "sha256:def456..."
        cite: "[tool.pytest.ini_options] declares pytest as the test runner"
      - path: "Makefile"
        sha: "sha256:789abc..."
        cite: "test: target invokes pytest -q"
    meta-checksum: "sha256:fedcba..."
```

Top-level fields:

- `schema-version: 1` — fixed at v1 by this design. Future schema bumps follow the dialect-deprecation horizon (ratified by ADR-0041 alongside dialect grammar).
- `resolved-at` — ISO-8601 timestamp, monotonic. Excluded from replay-determinism comparison (per INV-resolutions-replay-deterministic).
- `resolver-environment` — captures the resolver's identity. `model` is the resolver-model pin (one of the four version-pins per INV-resolutions-quadruple-pin). `harness` is informational.
- `contracts` — map keyed by `<publisher>-<aspect>/<contract-slug>` (e.g., `kanon-testing/preflight`, `acme-fintech-compliance/audit-review`).

Per-contract fields:

- `semantic-version` — the contract's `semantic-version:` frontmatter at resolution time (one of the four version-pins).
- `contract-content-sha` — SHA-256 of the contract file's full bytes at resolution time (one of the four version-pins).
- `realized-by` — list of invocations the agent identified. Each entry has `label` (human-readable), `invocation` (the command string), and `invocation-form` (one of `shell` | `argv` | `python-callable` — with `python-callable` reserved for future ADR; v1 supports `shell` and `argv`).
- `evidence` — list of cited evidence files. Each entry has `path` (consumer-relative), `sha` (per-evidence pin per INV-resolutions-quadruple-pin), and `cite` (a one-line human-readable note explaining why this evidence supports the realization). Per INV-resolutions-evidence-grounded, the list is non-empty.
- `meta-checksum` — SHA-256 over the canonicalized bytes of this contract entry (excluding the `meta-checksum` field itself). Used by the kernel to detect hand-edits per INV-resolutions-machine-only-owned.

### Canonicalization for `meta-checksum`

To make `meta-checksum` reproducible across different YAML serializers, the kernel canonicalizes the entry as follows:

1. Strip the `meta-checksum` field.
2. Sort all keys recursively in alphabetical order.
3. Serialize as JSON with `sort_keys=True, separators=(",", ":")` (compact, deterministic JSON).
4. Compute SHA-256 over the resulting bytes.

This is the standard "JSON canonicalization scheme" pattern; it is independent of YAML serializer quirks.

## The replay algorithm

`_resolutions.py:replay(target: Path) -> ReplayReport`. Pseudocode:

```python
def replay(target: Path) -> ReplayReport:
    report = ReplayReport()
    rfile = target / ".kanon" / "resolutions.yaml"
    if not rfile.exists():
        return report  # no resolutions = no replay; not an error per se
    yaml = parse_yaml(rfile.read_text())
    if yaml.get("schema-version") != 1:
        report.error(code="unknown-schema-version", value=yaml.get("schema-version"))
        return report

    for contract_id, entry in yaml.get("contracts", {}).items():
        # 1. Hand-edit detection (INV-resolutions-machine-only-owned)
        actual = canonicalize_and_sha(entry)
        if actual != entry["meta-checksum"]:
            report.error(code="hand-edit-detected", contract=contract_id)
            continue

        # 2. Contract content-SHA pin (INV-resolutions-quadruple-pin)
        contract_path = locate_contract(contract_id)  # via aspect registry
        if contract_path is None:
            report.error(code="missing-contract", contract=contract_id)
            continue
        current_contract_sha = sha256(contract_path.read_bytes())
        if current_contract_sha != entry["contract-content-sha"]:
            report.error(code="stale-resolution", contract=contract_id, reason="contract-content drift")
            continue

        # 3. Evidence grounding (INV-resolutions-evidence-grounded)
        if not entry.get("evidence"):
            report.error(code="ungrounded-resolution", contract=contract_id)
            continue

        # 4. Per-evidence SHA pin (INV-resolutions-stale-fails)
        for ev in entry["evidence"]:
            ev_path = target / ev["path"]
            if not ev_path.exists():
                report.error(code="missing-evidence", contract=contract_id, path=ev["path"])
                continue
            current_ev_sha = sha256(ev_path.read_bytes())
            if current_ev_sha != ev["sha"]:
                report.error(code="sha-mismatch", contract=contract_id, path=ev["path"])
                continue

        # 5. Execute realizations (only if all above passed)
        for inv in entry["realized-by"]:
            result = execute_invocation(inv, target)
            report.add_result(contract=contract_id, label=inv["label"], result=result)

    return report
```

Key properties:

- **Determinism**: every step is a pure function of the inputs (the YAML bytes plus the consumer-repo state). No timestamps, no random IDs, no environment-variable reads beyond `cwd`. INV-resolutions-replay-deterministic holds.
- **Fail-closed**: any pin mismatch halts execution for that contract, recording a finding. Subsequent contracts continue (they may be unaffected). INV-resolutions-stale-fails holds.
- **Hand-edit detection runs before SHA pins**: this surfaces hand-edits as `hand-edit-detected` rather than as `sha-mismatch`, which is more diagnosable.

## The resolver's contract with the kernel

`_resolutions.py` defines the kernel's side. The resolver — invoked via `kanon resolve` on a developer machine — has the following contract:

**Inputs the resolver receives:**

- The list of enabled contracts (publisher + aspect + contract-slug, with their content-SHA + semantic-version at the moment of invocation).
- A handle to the consumer repo (filesystem access).
- The consumer's installed LLM harness (Claude Code, Cursor, etc.).

**Outputs the resolver MUST produce:**

- A `.kanon/resolutions.yaml` file conforming to the schema above.
- For each enabled contract: at least one `realized-by` entry; at least one `evidence` entry; correct `meta-checksum`.
- For each evidence file cited: the file MUST exist at the path given; the `sha` MUST match the file's bytes at the moment of resolution.

**Outputs the resolver MUST NOT produce:**

- A `meta-checksum` that doesn't match the canonicalized entry. (The kernel computes and compares.)
- An `invocation-form` outside `{shell, argv}` for v1 (future schema bumps may add).
- Resolutions for contracts not enabled in the consumer's `.kanon/config.yaml`.

The kernel does not implement the resolver. `kanon resolve` is a thin Python wrapper that hands off to the consumer's harness; the harness is responsible for invoking an LLM, presenting it with the contract prose, and producing the YAML. Phase A authors `kanon resolve` as a CLI verb that emits a structured prompt and accepts the harness's response.

## Stale-detection algorithm

Stale-detection is a sub-case of replay. The pin checks (steps 2 and 4 above) ARE the stale-detection. There is no separate "is this resolution stale?" pass; replay surfaces staleness by failing the corresponding pin check.

A standalone `kanon resolutions check` verb (Phase A) runs the replay's pin-check phase only, without executing invocations. This gives consumers a fast "are my resolutions fresh?" signal in the development loop, before they invoke `kanon preflight` or push to CI.

## CLI verbs (Phase A)

- `kanon resolve [--target PATH] [--contracts SLUG[,SLUG...]]` — invoke the resolver via the installed harness; write `.kanon/resolutions.yaml`.
- `kanon resolutions check [--target PATH]` — pin-check phase only; reports staleness without executing invocations. Cheap; suitable for IDE integration.
- `kanon resolutions explain <CONTRACT-ID>` — diagnostic verb. Reports why a contract is enabled (which `requires:` predicate, which capability, which publisher), which evidence the resolution cited, and the four pin values.

## Phase A implementation footprint

- `src/kanon/_resolutions.py` (~280 LOC): replay engine, canonicalization, stale-detection, JSON report shape.
- `src/kanon/cli.py` extensions: `kanon resolve`, `kanon resolutions check`, `kanon resolutions explain` (~80 LOC across three verbs; resolver verb is the lightest as it delegates to harness).
- `src/kanon/_verify.py` extensions: integrate replay results into the existing verify report (~30 LOC).
- `tests/test_resolutions.py`: ~25 test cases covering the six invariants (one positive case + edge cases per invariant).

Total Phase A delta for ADR-0039 implementation: ~390 LOC source + ~600 LOC tests, ~5 files.

## Decisions

- [ADR-0039](../decisions/0039-contract-resolution-model.md) — contract-resolution model (this design's parent decision).
- [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) — protocol-substrate commitment (the why).
- [ADR-0029](../decisions/0029-verification-fidelity-replay-carveout.md) — verification-contract carve-out for text-only replay; the replay engine inherits.
