---
status: accepted
date: 2026-05-01
design: "docs/design/distribution-boundary.md"
realizes:
  - P-publisher-symmetry
  - P-protocol-not-product
stressed_by:
  - acme-publisher
fixtures_deferred: "Phase A authors the release-cadence CI gate (`ci/check_release_cadence.py` or analogous), the wheel-split release workflows, and the migration script. The release-cadence invariants below are the contract; tests land in the implementation PR."
---
# Spec: Release cadence — kernel-reference-dialect cadence separation

## Intent

Define the substrate's release cadence policy across three surfaces: kernel (`kanon-substrate`), reference (`kanon-reference`), and dialect (`kanon-dialect: YYYY-MM-DD` artifacts). Cadence separation is what makes the substrate safe for `acme-` publishers: kernel evolution stays fast (daily-alpha permitted), reference evolution stays steady (weekly), dialect evolution stays slow (quarterly minimum) — and breaking changes never ship as kernel releases.

Per [ADR-0043](../decisions/0043-distribution-boundary-and-cadence.md), this spec carries the invariants the kernel and release workflows enforce. The cadence is opinionated by design; round-5 panel: "a breaking dialect change every day would shred any future `acme-` author."

## Invariants

<!-- INV-release-cadence-kernel-daily-alpha-permitted -->
1. **Kernel daily-alpha permitted.** `kanon-substrate` MAY ship daily alpha releases under semver. Daily-alpha is the substrate-author's option, not an obligation. Bug fixes, contract validators, CLI ergonomics, structural validator improvements, performance work — all are kernel-cadence work and may ship at daily alpha.

<!-- INV-release-cadence-reference-weekly -->
2. **Reference ships at weekly cadence.** `kanon-reference` ships at weekly cadence (substrate-author discretion). Reference releases never include kernel-level changes. A change that affects both surfaces (e.g., a new dialect that bumps reference contracts and substrate validators) ships as separate, coordinated releases — kernel ships first; reference ships within the same week.

<!-- INV-release-cadence-dialect-quarterly-minimum -->
3. **Dialect ships at quarterly minimum, annual default.** A new dialect version (`kanon-dialect: YYYY-MM-DD` per [`docs/specs/dialect-grammar.md`](dialect-grammar.md) `INV-dialect-grammar-version-format`) ships at quarterly minimum, annual default. Dialect supersession is calendar-driven; an ADR ratifies the new dialect; the new dialect's spec describes what changed relative to its predecessor.

<!-- INV-release-cadence-breaking-not-in-kernel -->
4. **Breaking changes never ship as kernel releases.** A grammar change, capability-registry semantic change, or any other change that breaks `acme-` publisher bundles authored under a previous dialect MUST ship as a *dialect supersession* (a new ADR + a new dialect spec + the substrate honouring the previous dialect for at least the deprecation horizon), not as a `kanon-substrate` kernel release. The release-cadence CI gate (Phase A) enforces this by failing builds where a kernel release commit touches dialect-grammar files.

<!-- INV-release-cadence-substrate-honours-n-minus-1 -->
5. **Substrate honours at least N-1 dialects.** At any time, `kanon-substrate` MUST honour at least the current dialect (N) and the previous dialect (N-1). Manifests pinning N-2 or older receive a deprecation warning but still load (per `INV-dialect-grammar-version-format`); manifests pinning a dialect newer than the substrate knows fail at load (per `INV-dialect-grammar-pin-required`). The deprecation horizon is at least 4 quarters; a substrate planning to drop dialect support before 4 quarters elapse must publish an ADR justifying the shorter horizon.

## Rationale

The five invariants together codify the substrate's commitment that **kernel evolution and grammar evolution are decoupled**. Without invariant 1 (daily-alpha permitted), substrate authors lose the iteration cadence kanon depends on. Without invariant 2 (reference weekly), reference aspect prose churns out of sync with the kernel. Without invariant 3 (dialect quarterly minimum), publishers can't pin against a stable target. Without invariant 4 (breaking-changes-not-in-kernel), kernel daily-alpha becomes a publisher-extinction risk. Without invariant 5 (N-1 honoured), publishers must migrate every dialect cut — which is the same as no dialect-versioning.

The cadence is opinionated. A future ADR may revise based on lived experience. v0.4 ships these invariants as the foundation; revision happens through dialect supersession, not through silent edits to this spec.

## Out of Scope

- **Specific calendar dates for dialect supersessions.** Each dialect ships with its own ADR; this spec specifies the cadence range, not the calendar.
- **`acme-` publisher cadence policies.** Publishers set their own cadence; the substrate has no opinion.
- **Tooling for publishing the three release surfaces.** Phase A authors release workflows; this spec specifies the policy they implement.
- **Multi-substrate-version migration UX.** Future ADR territory if a real consumer hits the deprecation horizon.

## Decisions

- [ADR-0043](../decisions/0043-distribution-boundary-and-cadence.md) — distribution boundary, release cadence, recipe artifact (this spec's parent decision).
- [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) — protocol-substrate commitment.
- [ADR-0041](../decisions/0041-realization-shape-dialect-grammar.md) — dialect grammar; this spec's cadence policy governs dialect supersession.
- [ADR-0040](../decisions/0040-kernel-reference-runtime-interface.md) — runtime interface; the distribution boundary lives over the entry-point discovery mechanism.
