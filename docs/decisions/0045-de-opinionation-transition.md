---
status: accepted
date: 2026-05-01
---
# ADR-0045: De-opinionation transition — Phase 0.5 hand-over and Phase A deletion sequence

## Context

The seventh and final Phase 0 ADR. ADRs 0039–0044 ratified the substrate's runtime model (resolutions), discovery interface (entry-points), contract grammar (realization-shape + dialect + composition), verification scope, distribution boundary + cadence + recipe, and self-conformance discipline. ADR-0045 closes Phase 0 by ratifying the **transition path** — the ordered sequence of commits that moves the kanon repo from kit-shape (today's main branch) to protocol-substrate-shape (post-Phase A).

The commitment to transition was made by [ADR-0048](0048-kanon-as-protocol-substrate.md) and the foundations rewrite. The mechanics — what gets deleted, what gets added, what gets rewritten — live across [ADR-0040](0040-kernel-reference-runtime-interface.md)'s design (kernel/reference interface, `_kit_root()` retirement walkthrough), [ADR-0043](0043-distribution-boundary-and-cadence.md)'s design (distribution split, migration script outline), and [ADR-0044](0044-substrate-self-conformance.md)'s discipline (the gate that fails commits which break self-host).

What none of those ADRs ratify is the **order of the transition commits**. Round-5 panel called this the load-bearing sequencing concern: under [ADR-0044](0044-substrate-self-conformance.md)'s self-conformance discipline, every kernel-version-bump commit must keep self-host green; the wrong order produces P1 halts between commits the substrate doesn't ship from. ADR-0045 ratifies the order.

This ADR is small in code-impact (Phase A executes; this PR is documentation only) and large in operational weight (it specifies the canonical sequence so future contributors don't catastrophically reorder).

## Decision

Three numbered ratifications:

### 1. Phase 0.5 self-host hand-over ships BEFORE any Phase A deletion

Before any commit removes `defaults:`, `_detect.py`, kit-global `files:`, bare-name CLI sugar, or any other kit-shape vestige, **Phase 0.5 ships**: the kanon repo's `.kanon/config.yaml` is rewritten to opt-in form via the publisher recipe (per [ADR-0048](0048-kanon-as-protocol-substrate.md) self-host commitment and [ADR-0043](0043-distribution-boundary-and-cadence.md) recipe artifact); the `reference-default` recipe (or its predecessor authored under Phase 0) is copied to `.kanon/recipes/`; the config carries `provenance:` recording attribution.

After the Phase 0.5 commit lands, the kanon repo is opted-into reference aspects via a publisher recipe — exactly as any external consumer would. The kit-shape `defaults:` / `_detect.py` / kit-global `files:` machinery is *no longer used by the kanon repo's own self-host* even though the machinery still exists. Subsequent Phase A deletions are then no-ops for the kanon repo's behaviour; self-host stays green.

The reverse order — Phase A deletions before Phase 0.5 — would break self-host between commits. The kanon repo's `.kanon/config.yaml` would still rely on `defaults:` after `defaults:` is deleted; `kanon verify .` would fail until Phase 0.5 lands; substrate-self-conformance gate (per ADR-0044) blocks every intervening commit.

### 2. Phase A deletions ship in a documented order; self-conformance gates each commit

The canonical Phase A sequence (steps numbered for traceability; reordering between adjacent steps is acceptable if self-host stays green):

- **A.1 — Distribution split.** Author `kanon-core/pyproject.toml`, `kanon-aspects/pyproject.toml`, `kanon-kit/pyproject.toml` per [`docs/design/distribution-boundary.md`](../design/distribution-boundary.md). Reorganize source tree so substrate ships kernel-only and reference ships aspects-only. CI matrix updated.
- **A.2 — `_kit_root()` retirement.** Replace every call site (10+, walked in [`docs/design/kernel-reference-interface.md`](../design/kernel-reference-interface.md)) with publisher-registry lookups. Author `ci/check_substrate_independence.py`; the gate runs and likely fails — iteration to green is the deliverable.
- **A.3 — Kit-global `files:` and `defaults:` deleted.** `.kanon/kit.md` migrates to an aspect or is deleted. The top-level `defaults:` field is removed from kit manifest. Phase 0.5's hand-over makes this a no-op for the kanon repo.
- **A.4 — `_detect.py` deleted.** Testing-aspect's `config-schema:` for runtime commands (`test_cmd`, `lint_cmd`, etc.) removed. Replaced by the resolution model (per ADR-0039); the kit's runtime-binding lives in `.kanon/resolutions.yaml`, not in `kanon aspect set-config`.
- **A.5 — Bare-name CLI sugar deprecated.** `--aspects sdd:1` keeps working for one minor cycle with a deprecation warning; future cycle requires `--aspects kanon-sdd:1`.
- **A.6 — Resolution + dialect + composition modules.** Author `_resolutions.py` (per ADR-0039 design), `_dialects.py` (per ADR-0041 design), `_composition.py` (per ADR-0041 design). Replay engine, dialect-pin validator, topo-sort with cycle detection.
- **A.7 — New CLI verbs.** Author `kanon resolve` (developer-machine resolver invocation), `kanon resolutions check` (pin-check phase only), `kanon resolutions explain` (diagnostic), `kanon contracts validate <bundle-path>` (publisher-facing validator).
- **A.8 — Scaffolded `ci/check_*.py` retirement.** The four scripts the kit historically scaffolded into consumer trees (`check_deps.py`, `check_security_patterns.py`, `check_test_quality.py`, `release-preflight.py`) are removed from `kanon-aspects`'s scaffolded files. The kanon repo's own consumer-side `ci/check_*.py` files survive as authored realizations the resolution model binds to.
- **A.9 — Migration script.** Author `kanon migrate v0.3 → v0.4` per [`docs/design/distribution-boundary.md`](../design/distribution-boundary.md). Mark deprecated-on-arrival; delete after the kanon repo's own migration commit lands (Phase 0.5 is its first lived event, so deletion happens shortly after Phase A.9 ships).

Substrate-self-conformance (per ADR-0044) gates every step. A step that breaks the substrate-independence gate or the self-host probe is reverted before merge.

### 3. No backward-compatibility shims for v0.3.x

Per [ADR-0048](0048-kanon-as-protocol-substrate.md) clean-break commitment: there are no current external consumers; the cost of breaking compatibility is zero. `kanon-core==1.0.0a1` ships as a hard cut from `kanon-kit==0.3.x`. The `kanon migrate v0.3 → v0.4` script (Phase A.9) handles the kanon repo's own transition and is deprecated-on-arrival.

A future fork of v0.3.x is its forker's responsibility. The substrate's first Phase A release ships with a one-line release note: *"kanon-kit 0.3.x is end-of-life. The substrate is the successor. There is no migration path; opt in explicitly via the migration script."*

## Alternatives Considered

1. **Deletions before hand-over.** Phase A removes `defaults:`/`_detect.py`/etc. first; Phase 0.5 rewrites self-host config afterward. **Rejected.** Self-host breaks between the deletion commit and the hand-over commit; substrate-self-conformance gate blocks every intervening commit. The kanon repo cannot ship from a state where its own self-host is red. Phase 0.5 first is the only ordering that keeps the gate green throughout.

2. **Informal ordering** — let Phase A's PR sequence emerge organically; no canonical sequence in the ADR. **Rejected.** Round-5 panel called sequencing the load-bearing concern. Without a ratified sequence, contributors (the lead, working with multiple LLM-agent worktrees per the `solo-with-agents` persona) may iterate in different orders across worktrees and break self-host. The canonical sequence is the only way to coordinate.

3. **Backward-compatibility shims for v0.3.x consumers.** Ship `kanon-core==1.0.0a1` with a `defaults: [...]` shim that emits deprecation warnings; consumers migrate at their own pace. **Rejected.** Per ADR-0048's clean-break commitment, no current consumers exist; backward-compat would be pure cost without offsetting benefit. The migration script handles the kanon repo (the only existing consumer); future v0.3.x forkers handle themselves.

4. **Defer transition to v1.0.** Keep kit-shape under v0.4.x; cut v1.0 as the protocol-substrate ship. **Rejected.** Two reasons. (a) The substrate's identity is committed by ADR-0048; deferring contradicts the lead's "kit was a prototype against our DNA" framing. (b) Each release-cycle that ships kit-shape accumulates more lock-in (per ADR-0048 alternatives §3): the cheapest moment to migrate is now, with zero current consumers. Deferring increases cost without changing the destination.

## Consequences

### Phase A sequencing

- **The 9-step sequence is canonical.** Phase A executes in this order; deviation requires either (a) self-host staying green throughout (the deviation is acceptable), or (b) a superseding ADR (the deviation is structural and requires re-ratification).
- **The substrate-independence gate's first run will fail.** This is expected and named honestly here. Phase A.2 (`_kit_root()` retirement) is the iteration step that turns the gate green; subsequent steps preserve green.
- **Self-host stays green at every commit Phase A merges.** ADR-0044's discipline blocks merges that violate this.
- **No v0.3.x reverse compatibility.** `kanon-core==1.0.0a1` ships clean.

### Substrate ship

- **`kanon-core==1.0.0a1`** ships when Phase A.1–A.7 complete (the structural transition: distribution + interface + grammar + verification). A.8–A.9 may follow in subsequent point releases.
- **`kanon-aspects==1.0.0a1`** ships in lockstep, with the seven aspects authored against the v1 dialect (`kanon-dialect: 2026-05-01` per ADR-0041).
- **`kanon-kit==1.0.0a1`** meta-alias ships with exact-version pins to substrate and reference.
- **The Phase 0.5 commit is the kanon repo's first migration event.** It exercises the publisher-recipe-opt-in path before any external consumer ever does — and this is the substrate's primary correctness probe.

### Phase 0 closure

- **Phase 0 is complete with this ADR's ratification.** Seven ADRs (0039–0045) ratify the protocol substrate's full normative surface: runtime model, discovery interface, contract grammar, verification scope, distribution boundary, self-conformance discipline, transition sequence.
- **Phase 0.5 is its own plan**, authored after this ADR ships.
- **Phase A is multiple plans**, authored per the canonical sequence.

### Out of scope (deferred)

- **`acme-` publisher migration guidance** — Phase B/C; no `acme-` publishers exist to migrate.
- **The Phase 0.5 plan itself** — separate plan, authored next.

## Config Impact

- **`.kanon/config.yaml` v3 → v4 migration is the kanon repo's first lived event** (Phase 0.5). Downstream consumers (none today) would migrate via the script; the kanon repo migrates as the substrate's primary correctness probe.
- **Manifest changes** (Phase A.3, A.4): the top-level `defaults:` field, the kit-global `files:` field, the testing-aspect's runtime-command `config-schema:`, are all removed. Phase 0.5's hand-over makes these no-ops for the kanon repo.

## References

- [ADR-0048](0048-kanon-as-protocol-substrate.md) — protocol-substrate commitment (parent); the "kit was the detour" framing this ADR operationalizes.
- [ADR-0040](0040-kernel-reference-runtime-interface.md) — kernel/reference runtime interface; ADR-0040's design carries the `_kit_root()` retirement walkthrough.
- [ADR-0043](0043-distribution-boundary-and-cadence.md) — distribution boundary; ADR-0043's design carries the migration-script outline.
- [ADR-0044](0044-substrate-self-conformance.md) — substrate self-conformance discipline; the gate that enforces this ADR's sequencing rules.
- [ADR-0039](0039-contract-resolution-model.md) — contract-resolution model; what `_resolutions.py` (Phase A.6) implements.
- [ADR-0041](0041-realization-shape-dialect-grammar.md) — dialect grammar; what `_dialects.py` and `_composition.py` (Phase A.6) implement.
- [ADR-0042](0042-verification-scope-of-exit-zero.md) — verification scope-of-exit-zero; complementary to substrate-self-conformance.
- [`docs/foundations/de-opinionation.md`](../foundations/de-opinionation.md) — manifesto codifying the lead's framing this ADR closes.
