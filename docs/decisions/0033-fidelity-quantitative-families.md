---
status: accepted
date: 2026-04-27
supersedes: 0031
---
# ADR-0033: Fidelity quantitative assertion families and turn-format extensibility

## Context

ADR-0031 ratified `kanon-fidelity` with three lexical assertion families (`forbidden_phrases`, `required_one_of`, `required_all_of`) and explicitly rejected sensei's quantitative bands (`silence_ratio`, `question_density`, `teaching_density`) as pedagogy-specific vocabulary that does not generalise.

Sensei — kanon's reference adoption — has since migrated to kanon but cannot migrate its behavioural verification system because:

1. **Quantitative metrics are missing.** Sensei's three bands are domain-specific in *name* but domain-neutral in *math*: `silence_ratio` is word-share (actor words / total words); `question_density` is pattern-match count per turn; `teaching_density` is pattern-match count per turn with a different regex. The underlying computations generalise to any agent whose behavioural contract includes "don't dominate the conversation" or "avoid certain language patterns."

2. **Turn marker grammar is incompatible.** Sensei's dogfood transcripts use `[MENTOR]`/`[LEARNER]` bracket markers. Kanon's grammar only supports `ACTOR: text` colon format. Sensei cannot migrate its 10 existing dogfood captures without either reformatting them or extending kanon's grammar.

This ADR reverses ADR-0031's rejection of quantitative metrics (Alternative #3) by absorbing the generalised subset as built-in families, and extends the turn-marker grammar to support bracket format.

## Decision

### 1. Two new built-in assertion families

Add to the fidelity fixture schema (spec INV-3, INV-5):

- **`word_share`** — `{min?: float, max?: float}`. Computes `count(\w+ tokens in actor turns) / count(\w+ tokens in all turns)`. Errors when the ratio falls outside the declared band. This is the domain-neutral generalisation of sensei's `silence_ratio`.

- **`pattern_density`** — a list of entries, each with `{pattern?: str, patterns?: list[str], strip_code_fences?: bool, min?: float, max?: float}`. For each entry: count non-overlapping regex matches (across all patterns) in the actor's joined turns, divide by actor turn count. Errors when the density falls outside the declared band. This is the domain-neutral generalisation of both `question_density` (pattern: `\?`) and `teaching_density` (patterns: list of teaching-language regexes).

Both families are optional per-fixture, evaluated independently alongside the existing three lexical families, and produce errors in the same taxonomy (spec INV-8). They operate on the same actor text extracted by the turn grammar — no new I/O paths, no consumer code execution, no violation of INV-10's text-only bounds.

### 2. Turn-format extensibility

Add a `turn_format` key to fixture frontmatter (spec INV-3, INV-4):

- `turn_format: colon` (default when absent) — existing grammar `^([A-Z][A-Z0-9_]*):[ \t]+`.
- `turn_format: bracket` — new grammar `^\[([A-Z][A-Z0-9_]*)\][ \t]+`.

Two pre-compiled regexes in `_fidelity.py`, selected by a string enum. No consumer-supplied regex (ReDoS vector). Per-fixture granularity (a project may have transcripts from different tools). Default is `colon` — zero existing fixtures break.

### 3. Code-fence stripping

The `strip_code_fences` option on `pattern_density` entries removes triple-backtick fenced blocks before counting matches. This prevents code examples in agent output from inflating pattern counts. Default is `false`.

## Alternatives Considered

1. **Module-path plugin system for custom metrics (Option A).** Consumer Python imported during verify via `importlib.import_module`. Rejected: violates INV-10 bound 1 ("no Python imports of consumer code"), collapses the trust boundary, makes `kanon verify` unsafe to run unsandboxed in CI. The project-aspect validator mechanism (`run_project_validators`) already provides an escape hatch for consumers who need arbitrary Python — fidelity replay must remain the stricter sandbox.

2. **DSL/expression language for metric formulas.** A mini-language like `count(pattern) / turns > 0.1`. Rejected: parser complexity for marginal gain. The two built-in families cover the ratio-of-X-per-Y shape that sensei's three metrics use. If a third shape emerges, add a third built-in family (same cost model as adding `required_all_of` was to the original three).

3. **Auto-detect turn format from dogfood content.** Rejected: ambiguous. Markdown uses `[TEXT]` for link references, footnotes, and callouts. Explicit `turn_format` declaration avoids false matches.

4. **Keep ADR-0031 as-is; sensei uses a project-aspect for its bands.** Rejected: the goal is for kanon to be a superset so sensei can delete its custom `tests/transcripts/` system. A project-aspect workaround perpetuates the parallel-systems problem.

## Consequences

- **ADR-0031 is partially superseded.** Its rejection of quantitative metrics (Alternative #3) is reversed. All other decisions in ADR-0031 remain in force: aspect identity, depth-range, capability declaration, scaffolding choices, the three existing assertion families.
- **Fixture schema grows.** Three new optional keys (`turn_format`, `word_share`, `pattern_density`). All are backward-compatible — existing fixtures without them continue to work identically.
- **`_fidelity.py` grows by ~100 LOC.** Two new evaluation blocks, a second turn-marker regex, word-counting and pattern-counting helpers, code-fence stripping.
- **Sensei migration unblocked.** Sensei's 10 fixture/capture pairs can be expressed in kanon's format with lossless metric mapping: `silence_ratio` → `word_share`, `question_density` → `pattern_density` with `\?` pattern, `teaching_density` → `pattern_density` with teaching-language patterns.
- **INV-10 text-only bounds preserved.** Both new families are pure-compute over committed text. No subprocess, no LLM, no network, no consumer code imports.
- **Spec `fidelity.md` requires amendment** to INV-3 (fixture format), INV-4 (turn grammar), INV-5 (assertion families). The Out of Scope section's "score-based assertions" item is narrowed: the two built-in families are threshold-based (band comparison), not score-based (arbitrary numeric scoring). The distinction: bands are bounded ratios with clear semantics; scores are open-ended numbers requiring calibration.

## References

- [ADR-0031](0031-fidelity-aspect.md) — the decision this ADR partially supersedes.
- [ADR-0029](0029-verification-fidelity-replay-carveout.md) — verification-contract carve-out (INV-10).
- [`docs/specs/fidelity.md`](../specs/fidelity.md) — invariant surface requiring amendment.
