---
status: accepted
date: 2026-04-22
---
# ADR-0010: Protocol layer — prose-as-code judgment procedures at `.kanon/protocols/`

## Context

The kit has specs (what), design (how), ADRs (why), plans (when) — and nothing for "here is the procedure an operating agent should follow to make this judgment." Three concrete operations exposed this gap during v0.1 dogfooding:

1. **Tier-up decisions.** `tier set N+1` is a one-line CLI command, but *whether* to run it is a judgment call — read the project, weigh signals, consider readiness. No document in the kit teaches that judgment.
2. **Verify-report triage.** `kanon verify` emits a JSON report of findings. Some are blockers, some are warnings, some are near-misses. Current agent behavior: ad-hoc triage, inconsistent across sessions.
3. **Spec review.** Reviewing a draft spec for ambiguity, falsifiability, invariant clarity is mechanical enough to standardize but judgment-heavy enough that a Python linter can't do it.

These are all multi-step procedures that need structured prose, versioning, and discoverability. Hardcoding them into the CLI would fail (judgment doesn't compile to deterministic code). Leaving them as agent improvisation loses reproducibility across sessions and harnesses.

Sensei ships a parallel layer at `.sensei/protocols/` (personality, mode system, review harness) that has worked in practice for months. The pattern — prose read by an LLM runtime at invocation time — is `P-prose-is-code` made concrete.

## Decision

Ship `.kanon/protocols/` as a first-class kit layer in v0.1, with three initial protocols:

- **`tier-up-advisor.md`** (tier-min: 1) — invoked when the user or agent considers raising the project's tier.
- **`verify-triage.md`** (tier-min: 1) — invoked on a `kanon verify` failure report; triages findings into an action list.
- **`spec-review.md`** (tier-min: 2) — invoked when reviewing a draft spec before promotion to `status: accepted`.

The layer's contract is defined in `docs/specs/protocols.md`:

- Location: `.kanon/protocols/<name>.md` in consumer repos, mirrored byte-identically from `src/kanon/kit/protocols/<name>.md` in the kit source.
- Frontmatter: `status`, `date`, `tier-min`, `invoke-when`.
- Discovery: an AGENTS.md marker section `protocols-index` at tier ≥ 1 lists active protocols with name, trigger, and tier-min.
- Integrity: byte-equality enforced by `ci/check_kit_consistency.py`; `kanon verify` catches drift in consumer repos.
- No runtime dispatch command in v0.1 — the operating agent reads the file; the CLI's role is scaffolding and integrity-checking.

## Alternatives Considered

1. **Inline into AGENTS.md as marker sections.** Each protocol becomes another `<!-- kanon:begin:X -->` block. Rejected: protocols are long (multi-step, 100+ lines each). Inlining would balloon AGENTS.md beyond the "read me first" budget and make tier-up-advisor visible at tier-0 where it doesn't apply. Separate files with an index marker keeps AGENTS.md lean.
2. **Hardcode procedures into Python (`kanon advise`, `kanon triage`, `kanon review`).** Rejected: these are judgment procedures whose steps read more like a checklist for an LLM than an algorithm for an interpreter. A Python implementation would either wrap an LLM call (moving the prose into a string constant — worse than a file) or attempt deterministic heuristics (fragile and wrong).
3. **Consumer-authored only; no kit-shipped protocols.** Rejected: the three target protocols are kit-wide best practices. Shipping them guarantees every consumer repo has them available at the right tier; bare-kit protocols can arrive later.
4. **Separate package (`kanon-protocols`).** Rejected: protocols are tier-gated, which means they need to participate in the same manifest+CLI that decides tier content. Splitting the package adds release coupling without buying independence.
5. **Protocol dispatch CLI (`kanon protocol <name>`).** Rejected for v0.1: the command would either print the protocol file (redundant — the agent can read the file directly) or attempt to run it (requires an LLM subprocess, out of v0.1 scope). Deferred as a v0.2+ nice-to-have.

## Consequences

- **Adds a new invariant surface.** `ci/check_kit_consistency.py` grows a byte-equality whitelist entry per protocol. `kanon verify` grows a check. `tests/test_protocols.py` is added.
- **AGENTS.md grows a `protocols-index` marker section at tier ≥ 1.** Existing tier-migration non-destructiveness (ADR-0008) carries unchanged — the new section is just another managed block.
- **Self-hosting extends.** Kanon's own repo-root gets `.kanon/protocols/` with the three protocols (it is itself a tier-3 kanon consumer). Self-hosted byte-equality check applies.
- **Pattern is extensible.** Future protocols (release-cut-checklist, migration-writer, adversarial-review) plug in by adding a file + a manifest entry. No core code changes.
- **Enforcement proximity preserved.** The two load-bearing rule sections (`plan-before-build`, `spec-before-design`) stay as AGENTS.md marker sections, not protocols. The distinction: rules that must bind on every turn live in AGENTS.md; procedures invoked under specific triggers live in protocols.

## Config Impact

None. Tier membership is data in `kit/manifest.yaml`, not config in `.kanon/config.yaml`.

## References

- ADR-0011 — kit-bundle refactor that makes this layer cheap to add.
- `docs/specs/protocols.md` — the invariant surface for this layer.
- `P-prose-is-code`, `P-specs-are-source` — principles realized.
- Sensei's `.sensei/protocols/` layer — prior-art that validates the pattern.
