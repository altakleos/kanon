---
status: superseded
date: 2026-04-27
superseded-by: 0033
---
# ADR-0031: `kanon-fidelity` aspect — Tier-1 behavioural-conformance verification

## Context

`kanon verify` is structural-only by default per `docs/specs/verification-contract.md` INV-9 — it confirms file presence, AGENTS.md marker balance, fidelity-lock SHAs. It cannot detect whether an agent that *read* a protocol actually *followed* it. Kanon's growing audit-sentence enforcement pattern (e.g., the worktree-lifecycle protocol's `Working in worktree …` requirement, introduced in commit `b9524aa9`) is a behavioural specification expressed as prose with no mechanism to catch the agent that ignored it.

The Round-2 verification panel surfaced INV-9 as a hard architectural blocker for every behavioural-verification proposal. ADR-0029 amended `verification-contract.md` with INV-10 — a narrowly-scoped carve-out authorising text-only lexical replay of `.kanon/fidelity/<protocol>.dogfood.md` capture files when an aspect declaring the `behavioural-verification` capability (per ADR-0026) is enabled. This ADR ratifies the kit-shipped aspect that consumes that carve-out.

The aspect's design is anchored on Round-2 panel input: keep it narrow (one capability, two depths, three assertion families); avoid sensei's pedagogy-specific extensions (`silence_ratio`, `question_density`, `teaching_density`); leave Tier-2 (workstation capture) and Tier-3 (paid live-LLM nightly) explicitly out of scope under their own future ADRs; preserve the ADR-0026 substitutability handle so a `project-fidelity-*` aspect can substitute for the kit-shipped one without consumers having to re-implement the verify-side glue.

See [`docs/specs/fidelity.md`](../specs/fidelity.md) for the invariant surface this ADR ratifies.

## Decision

Ship `kanon-fidelity` as a new kit aspect with the following declarative shape:

- **Name**: `kanon-fidelity` per ADR-0028 namespace grammar.
- **Stability**: `experimental`. Promotion to `stable` requires (a) ≥1 non-kit, non-sensei consumer adoption with a committed fixture pair and (b) the Tier-2 noise-scrubbing question being settled by a future ADR.
- **Depth range**: `[0, 1]`. Depth-0 is opt-out; depth-1 is the working depth. The narrow range avoids the ghost-cell prohibition of `aspects.md` INV-3 and keeps the door open to widen the range alongside a Tier-2 ADR rather than sneaking in a placeholder.
- **Default-depth**: `1`.
- **Requires**: `[]`. The aspect stands alone; it composes with `kanon-sdd`, `kanon-testing`, or any other aspect without ordering constraints.
- **Provides**: `[behavioural-verification]`. This is the load-bearing capability flag per ADR-0026 — INV-10 of the verification-contract spec is gated on any aspect declaring this capability, so a `project-fidelity-*` aspect that declares the same `provides:` substitutes natively.
- **Depth-1 scaffolding**: one protocol (`fidelity-fixture-authoring.md`) and two AGENTS.md sections (`kanon-fidelity/body`, `kanon-fidelity/fidelity-discipline`). No CI script ships under the aspect — the assertion engine lives in `src/kanon/_fidelity.py` and runs as part of `kanon verify`. No sample fixture is scaffolded; the protocol prose includes complete example fixtures inline.

Engine implementation:

- **`src/kanon/_fidelity.py`** holds `load_fixtures(target)`, `extract_actor_text(dogfood_text, actor)`, and `evaluate_fixture(fixture, dogfood_text)`. Pure-compute except for the file reads. ~200 LOC.
- **`src/kanon/_verify.py`** gains `check_fidelity_assertions(target, aspects, errors, warnings)`, called from `cli.verify` only when an aspect declaring `behavioural-verification` is enabled at depth ≥ 1. Honours every bound in INV-10 (no subprocess, no LLM, no test-runner, no consumer-Python imports).
- **Failure taxonomy**: assertion failures and malformed fixtures are `errors:`; missing `.dogfood.md` pairs and zero-turn dogfood files are `warnings:`. Per spec INV-8.

## Alternatives Considered

1. **Make fidelity verification a depth-3 of `kanon-testing` instead of a separate aspect.** Round-2 architect's preferred option. Rejected: the `provides: behavioural-verification` capability flag is the substitutability handle that lets a `project-fidelity-*` aspect substitute without forcing consumers to override an entire testing aspect (per ADR-0026 source-neutrality). Burying the capability inside `kanon-testing` would re-couple substitutability to the parent aspect — exactly what ADR-0026 was written to prevent. The +1 aspect-count cost is a deliberate trade for keeping the substitutability surface clean.

2. **Wider depth-range `[0, 2]` reserving room for Tier-2 today.** Rejected: `aspects.md` INV-3 forbids ghost cells (depth levels with no content). Tier-2 lands as a depth-range widening alongside its ADR; that's the honest signal.

3. **Adopt sensei's full assertion set including `silence_ratio`, `question_density`, `teaching_density` bands.** Rejected: those metrics encode a tutor/learner vocabulary that does not generalise. Round-2 verification engineer also rejected this on the same grounds.

4. **Literal-string matching instead of regex.** Rejected: literal matching forecloses anchoring (`^`/`$`), case-insensitivity, and slug-shape capture (e.g., `Working in worktree \`\.worktrees/[a-z0-9-]+/\``). Sensei's audit sentences vary slug and branch name across instances; literal matching would catch one instance only.

5. **Scaffold a sample fixture file at depth-1.** Rejected: a placeholder fixture would be left in place by the consumer, polluting `kanon verify` output with "example" failures forever. The protocol prose at `.kanon/protocols/kanon-fidelity/fidelity-fixture-authoring.md` includes complete example fixtures inline; consumers copy from prose, not from a placeholder file that pretends to be theirs.

6. **Bundle Tier-2 capture (`kanon transcripts capture` subcommand) in the same release.** Rejected: Tier-2 introduces a new CLI subcommand, a workstation-evidence-as-CI-artifact pattern, and noise-scrubbing for live LLM output. Each is its own decision surface; ADR-0029 explicitly excluded both from the carve-out. Bundling them would dilute review and obscure the cost of each.

7. **Make assertion failures warnings instead of errors.** Rejected: the entire point of the carve-out is to produce a binding signal that the agent's behaviour drifted from prose intent. A warning is what we already have — `kanon verify` returns `status: ok` with warnings today, and consumers do not gate on warnings. Errors fail the exit code, which is the only signal CI gates on.

## Consequences

- **Aspect count grows from 6 to 7.** Skeptic's Round-2 hard-cap-at-8 remains satisfied; depth-range widening for Tier-2 lands inside the existing aspect rather than as a new one.
- **A new spec `docs/specs/fidelity.md` (status: accepted)** and a new test file `tests/test_fidelity.py` (replacing the Track-0 stub).
- **~200 LOC of engine code** under `src/kanon/_fidelity.py` plus a ~30 LOC integration in `_verify.py`.
- **INV-10 of `verification-contract.md` is exercised, not theoretical.** The carve-out gains a working consumer.
- **Tier-2 and Tier-3 remain deferred under future ADRs.** This ADR explicitly does not authorise either; any expansion lands as a depth-range widening accompanied by its own decision record.
- **Self-hosting**: kanon's own repo enables `kanon-fidelity:1` and ships at least one exemplar fixture (`worktree-lifecycle`) demonstrating the assertion families against a real protocol.
- **`kanon verify` runtime cost**: O(milliseconds) per fixture; lexical replay is regex/substring over committed text. The fast-CI ethos is preserved.
- **Trust boundary**: read-only against the consumer's tree; no network, no subprocess, no LLM. Identical to the trust posture of every other `kanon verify` check.

## Config Impact

A consumer enabling the aspect adds an entry to `.kanon/config.yaml`:

```yaml
aspects:
  kanon-fidelity:
    depth: 1
    enabled_at: <ISO-8601>
    config: {}
```

No new top-level config keys. The aspect's `config-schema:` block is empty in v0.3 — fidelity has no tunable thresholds today. A future ADR may add (e.g.) a per-fixture timeout if the lexical-replay cost grows, but that is not anticipated.

Consumer-side directory `.kanon/fidelity/` is created by the consumer on first fixture authorship; the aspect does not pre-create it.

## References

- [`docs/specs/fidelity.md`](../specs/fidelity.md) — invariant surface this ADR ratifies (10 invariants).
- [ADR-0029](0029-verification-fidelity-replay-carveout.md) — verification-contract carve-out for fidelity-fixture replay (INV-10); the spec gap this aspect closes.
- [ADR-0026](0026-aspect-provides-and-generalised-requires.md) — `provides:` capability registry; this aspect provides `behavioural-verification`.
- [ADR-0028](0028-project-aspects.md) — project-aspect namespace grammar; `project-fidelity-*` aspects can substitute via the same capability.
- [ADR-0012](0012-aspect-model.md) — aspect model; this is the seventh kit aspect.
- [`docs/specs/aspects.md`](../specs/aspects.md) — INV-3 (no ghost cells) governs the choice of depth-range `[0, 1]`.
- `docs/plans/fidelity-and-immutability.md` — the plan this ADR is Track 1 of.
