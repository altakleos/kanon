---
status: accepted
date: 2026-05-01
---
# ADR-0044: Substrate self-conformance discipline

## Context

[ADR-0040](0040-kernel-reference-runtime-interface.md) introduced the *independence invariant* as a single bullet inside the kernel/reference runtime interface decision: "the substrate's test suite must pass with `kanon-aspects` uninstalled." Round-5 panel review converged on this as load-bearing — three reviewers (architect, critic, code-reviewer) and the verifier independently flagged it as the operational signal that proves the de-opinionation commitment in code paths.

ADR-0044 elevates the independence invariant from a downstream consequence of ADR-0040 to a top-level **substrate self-conformance discipline** with its own ADR, its own spec, and its own permanent CI gate. The substrate's "kernel-as-product, reference-as-demonstration" identity (per [ADR-0048](0048-kanon-as-protocol-substrate.md)) is exactly what this discipline enforces.

The elevation matters because:

1. **ADR-0040 is about the runtime interface (entry-points)**; the independence invariant is one downstream property, mentioned in the Decision but not the structural focus. Future readers of ADR-0040 may treat the invariant as an implementation detail.
2. **Independence needs its own spec INVs** so they can be cited by `acme-` publishers and enforced by CI gates that survive substrate refactors.
3. **The kanon repo's own self-host is itself a probe** (per [`docs/foundations/de-opinionation.md`](../foundations/de-opinionation.md) "self-hosting as falsification") — distinct from substrate-independence but reinforcing it. Both belong in one discipline ADR.

This ADR is small in code-impact (the CI gate is Phase A; this PR is documentation only) but large in normative weight (it makes substrate-independence a permanent commitment, not a Phase A milestone).

## Decision

Three numbered ratifications:

### 1. Substrate-independence is a permanent invariant

`kanon-core`'s test suite passes when run in a clean Python environment with no `kanon-aspects` installed and no `kanon.aspects` entry-points visible. This invariant is permanent — not a Phase A milestone — and applies to every kernel-version-bump commit on the substrate's main branch.

The invariant's machinery: a CI gate (`ci/check_substrate_independence.py` per [ADR-0040](0040-kernel-reference-runtime-interface.md)'s companion design) runs on every PR and every merge-to-main against `kanon-core`. Phase A authors the gate; this ADR ratifies that the gate is part of the substrate's *permanent* CI surface, not a one-time Phase A check.

Failure of the gate is a P0 substrate halt. Future kernel work that breaks independence — accidentally importing reference-aspect content from kernel code, hardcoding aspect names in non-data paths, regressing the entry-point discovery — is rejected before merge.

### 2. Self-host is the primary correctness probe

The kanon repo opts into reference aspects via the publisher recipe per [ADR-0048](0048-kanon-as-protocol-substrate.md)'s self-host commitment and runs `kanon verify .` against itself in CI. The repo's own conformance is the substrate's first quantitative correctness signal.

Self-host conformance is distinct from independence: independence proves the kernel doesn't *require* reference; self-host proves the kernel *works* with reference once a consumer opts in. Both invariants compose to certify the substrate's claim — the kernel ships standalone (independence), and the kernel demonstrably works in production via the kanon repo's own state (self-host).

Self-host failures are also P1 substrate halts. A kernel-version-bump commit that breaks self-host (typically by introducing a regression `kanon verify` catches against the kanon repo's actual `.kanon/` state) is rejected.

### 3. The substrate's CI gate is publicly-readable

The substrate-independence gate's status is public — runnable on a fresh checkout, results visible in the substrate's CI surface, algorithm documented in [`docs/design/kernel-reference-interface.md`](../design/kernel-reference-interface.md). Future `acme-` publishers can replicate the gate against their own bundles to claim substrate-conformance.

This is what makes the independence claim a *credible commitment*. Without public-readability, the substrate's "we don't depend on reference" claim is a self-report; with public-readability, any third party can verify it.

## Alternatives Considered

1. **Keep independence as ADR-0040 bullet only.** Don't elevate; treat as implementation detail of the kernel/reference runtime interface decision. **Rejected.** Independence has its own normative weight: it's the operational signal that proves the de-opinionation commitment in code paths. Burying it inside ADR-0040 means future contributors might treat it as an implementation detail and weaken it during refactors. Independence needs its own ADR with its own spec INVs to be a permanent commitment.

2. **Independence as Phase A milestone only.** "Phase A makes the gate green; we can relax after." **Rejected.** This is exactly the trap the substrate avoids: independence is *what makes the substrate a substrate*, not a one-time check. If the gate goes red post-Phase-A, the substrate is no longer a substrate; it's a kit again. Permanent enforcement is non-negotiable.

3. **Substrate self-conformance via informal review.** Reviewers check independence on every PR; no automated gate. **Rejected.** The substrate's contribution model is a single maintainer with multiple LLM-agent worktrees (per the `solo-with-agents` persona). Informal review is unreliable at multi-agent cadence; an automated gate is the only credible enforcement.

4. **Integrate into ADR-0042 verification scope-of-exit-zero.** ADR-0042 already speaks to what `kanon verify` certifies; extend it to substrate-independence. **Rejected.** ADR-0042 is the *consumer-facing claim* (what exit-0 means for *consumers*). ADR-0044's discipline is the *substrate-author-facing claim* (what `kanon-core`'s own CI gates ensure). Different audiences, different normative surfaces; merging would obscure both.

## Consequences

### Substrate-side

- **Phase A authors `ci/check_substrate_independence.py`** per [ADR-0040](0040-kernel-reference-runtime-interface.md)'s companion design. The gate's first run will likely fail (revealing today's hidden dependencies on reference content); iteration to green is the deliverable that completes the runtime intent of ADR-0040.
- **Phase A wires the gate into the substrate's CI workflow** so it runs on every PR + merge-to-main. The gate is part of the substrate's *permanent* CI surface, alongside `pytest`, `ruff`, and `mypy`.
- **Phase 0.5 self-host hand-over** (per ADR-0048 commitment): the kanon repo's `.kanon/config.yaml` is rewritten to opt-in form via the publisher recipe before Phase A's `defaults:` deletion. This sequencing keeps self-host green throughout the transition.
- **Future kernel work preserves both invariants.** A PR that breaks independence (gate red) or self-host (`kanon verify .` red) is rejected.

### Publisher-side

- **`acme-` publishers can replicate the gate** against their own bundles. Phase B/C publisher onboarding documents the replication pattern.

### Spec-side

- **`docs/specs/substrate-self-conformance.md`** carries the invariants the kernel and CI gate enforce. `acme-` publishers cite by INV ID.

### Out of scope (deferred)

- **The actual gate implementation (`ci/check_substrate_independence.py`)** — Phase A.
- **De-opinionation transition mechanics** — ADR-0045.
- **`acme-` publisher conformance test framework** — Phase B/C; this ADR specifies the gate's replicability, not the publisher-facing test framework.

## Config Impact

- **No consumer-side config change.** ADR-0044 is substrate-author-facing; it specifies the substrate's CI discipline.
- **Substrate-side CI workflow** gains the substrate-independence gate as a required check (Phase A).

## References

- [ADR-0048](0048-kanon-as-protocol-substrate.md) — protocol-substrate commitment (parent); the self-host commitment this ADR formalises.
- [ADR-0040](0040-kernel-reference-runtime-interface.md) — kernel/reference runtime interface; the independence-invariant origin.
- [ADR-0043](0043-distribution-boundary-and-cadence.md) — distribution boundary; the substrate-vs-reference packaging that makes independence testable.
- [ADR-0042](0042-verification-scope-of-exit-zero.md) — verification scope-of-exit-zero; complementary to this ADR (consumer-facing vs substrate-author-facing).
- [`docs/specs/substrate-self-conformance.md`](../specs/substrate-self-conformance.md) — invariants this ADR ratifies.
- [`docs/design/kernel-reference-interface.md`](../design/kernel-reference-interface.md) — gate algorithm (per ADR-0040).
- [`docs/foundations/de-opinionation.md`](../foundations/de-opinionation.md) — "self-hosting as falsification" framing.
- [`docs/foundations/principles/P-self-hosted-bootstrap.md`](../foundations/principles/P-self-hosted-bootstrap.md) — the principle this discipline enforces.
