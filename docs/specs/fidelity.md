---
status: accepted
design: "Follows ADR-0033"
date: 2026-04-27
realizes:
  - P-prose-is-code
  - P-verification-co-authored
stressed_by:
  - solo-with-agents
fixtures:
  - tests/test_fidelity.py
invariant_coverage:
  INV-fidelity-aspect-identity:
    - tests/test_fidelity.py::test_aspect_registered
  INV-fidelity-depth-scaffolding:
    - tests/test_fidelity.py::test_depth_1_scaffolds_protocol_and_section
  INV-fidelity-fixture-file-format:
    - tests/test_fidelity.py::test_fixture_frontmatter_required_keys
    - tests/test_fidelity.py::test_dogfood_pairing_required
  INV-fidelity-actor-turn-grammar:
    - tests/test_fidelity.py::test_turn_extractor_basic
    - tests/test_fidelity.py::test_turn_extractor_multiple_turns_concatenated
    - tests/test_fidelity.py::test_turn_extractor_ignores_unnamed_prose
  INV-fidelity-assertion-families:
    - tests/test_fidelity.py::test_forbidden_phrases_match_fails
    - tests/test_fidelity.py::test_required_one_of_no_match_fails
    - tests/test_fidelity.py::test_required_all_of_partial_match_fails
  INV-fidelity-aspect-gated:
    - tests/test_fidelity.py::test_replay_skipped_when_aspect_disabled
  INV-fidelity-text-only-bounds:
    - tests/test_fidelity.py::test_replay_engine_honours_invariant_bounds
  INV-fidelity-failure-taxonomy:
    - tests/test_fidelity.py::test_assertion_failures_become_errors
    - tests/test_fidelity.py::test_missing_dogfood_becomes_warning
  INV-fidelity-out-of-scope-tiers:
    - tests/test_fidelity.py::test_no_subprocess_or_capture_subcommand
  INV-fidelity-stability:
    - tests/test_fidelity.py::test_aspect_stability_experimental
  INV-fidelity-quantitative-families:
    - tests/test_fidelity.py::test_word_share_within_band_passes
    - tests/test_fidelity.py::test_word_share_below_min_fails
    - tests/test_fidelity.py::test_word_share_above_max_fails
    - tests/test_fidelity.py::test_pattern_density_within_band_passes
    - tests/test_fidelity.py::test_pattern_density_below_min_fails
    - tests/test_fidelity.py::test_pattern_density_above_max_fails
  INV-fidelity-turn-format-extensibility:
    - tests/test_fidelity.py::test_bracket_turn_marker_extraction
    - tests/test_fidelity.py::test_colon_default_when_turn_format_absent
---
# Spec: Fidelity — behavioural-conformance verification for prose-as-code protocols

## Intent

Package the discipline of *proving an LLM agent obeys the kit's prose protocols* as an opt-in aspect. Today, `kanon verify` is structural-only — it confirms that protocol prose exists, that AGENTS.md markers balance, that scaffolded files are present. It cannot detect whether an agent that *read* a protocol actually *followed* it. The audit-sentence enforcement pattern (e.g., `kanon-worktrees/worktree-lifecycle.md`'s "Working in worktree …" requirement) is a behavioural specification expressed as prose, with no mechanism to catch the agent that ignored it.

The `kanon-fidelity` aspect closes that loop using the narrowest mechanism that pays rent: lexical assertions over committed agent transcripts. Consumers commit a captured transcript per protocol they want to verify; the aspect ships a YAML schema for declaring what must (and must not) appear in the agent's turns; `kanon verify` runs the assertions when the aspect is enabled. No LLM calls, no subprocesses, no test-runner invocation. The fixture is text; the dogfood is text; the assertion is text-against-text.

The aspect realises the carve-out ratified by [ADR-0029](../decisions/0029-verification-fidelity-replay-carveout.md) against [INV-10 of `verification-contract.md`](verification-contract.md). Tier-2 (workstation capture via a future `kanon transcripts capture` subcommand) and Tier-3 (paid live-LLM nightly) are *not* part of this spec and require their own ADRs.

## Invariants

<!-- INV-fidelity-aspect-identity -->
1. **Aspect identity.** The aspect is named `kanon-fidelity` per the ADR-0028 namespace grammar. It declares `stability: experimental`, `depth-range: [0, 1]`, `default-depth: 1`, `requires: []`, and `provides: [behavioural-verification]`. The capability name is the load-bearing handle: any project- or third-party aspect declaring the same `provides:` capability satisfies the carve-out gate in INV-10 of the verification-contract spec, per ADR-0026 substitutability.

<!-- INV-fidelity-depth-scaffolding -->
2. **Depth scaffolding.** Depth-0 is opt-out (aspect named in config but no scaffolded files). Depth-1 scaffolds:
   - One protocol at `.kanon/protocols/kanon-fidelity/fidelity-fixture-authoring.md` describing the fixture file format and the actor-turn grammar.
   - One AGENTS.md section under the marker `kanon-fidelity/body` summarising what the aspect verifies and pointing at the protocol.
   - One AGENTS.md section under the marker `kanon-fidelity/fidelity-discipline` listing the core rules ("commit your dogfood capture before tagging a release", "regenerate captures when protocol prose changes", "never weaken an assertion to make a fixture pass").
   The aspect does **not** scaffold any sample fixture or `.kanon/fidelity/` directory contents — those are consumer-authored against the protocol's instructions. No CI script ships at depth 1; the assertion engine is in `src/kanon/_fidelity.py` and runs as part of `kanon verify`. The `protocols-index` marker block lists `fidelity-fixture-authoring` automatically when the aspect is active.

<!-- INV-fidelity-fixture-file-format -->
3. **Fixture file format.** A fixture lives at `.kanon/fidelity/<protocol>.md` in the consumer's tree. It carries YAML frontmatter with these keys:
   - `protocol` (string, required) — slug identifying the protocol the fixture verifies. Informational; not used for discovery.
   - `actor` (string, required) — the turn-prefix label whose turns the assertions are evaluated against (e.g., `AGENT`).
   - `forbidden_phrases` (list of strings, optional) — each entry is a Python regex; ANY match within the actor's joined turns fails the assertion.
   - `required_one_of` (list of strings, optional) — each entry is a Python regex; at least one regex must match somewhere within the actor's joined turns.
   - `required_all_of` (list of strings, optional) — each entry is a Python regex; every regex must match somewhere within the actor's joined turns.
   - `turn_format` (string, optional, default `"colon"`) — selects the turn-marker grammar: `"colon"` for `^([A-Z][A-Z0-9_]*):[ \t]+` (existing), `"bracket"` for `^\[([A-Z][A-Z0-9_]*)\][ \t]+` (sensei-compatible). Per-fixture granularity; a project may have transcripts from different tools.
   - `word_share` (object, optional) — `{min?: float, max?: float}`. Computes `count(\w+ tokens in actor turns) / count(\w+ tokens in all turns)`. Errors when the ratio falls outside the declared band.
   - `pattern_density` (list of objects, optional) — each entry has `{pattern?: str, patterns?: list[str], strip_code_fences?: bool, min?: float, max?: float}`. For each entry: count non-overlapping regex matches (union of `pattern` and `patterns`) in the actor's joined turns, divide by actor turn count. Errors when the density falls outside the declared band.
   The body of the fixture file is freeform markdown explaining what the fixture asserts and why; it is not parsed.
   Every fixture file requires a paired capture at `.kanon/fidelity/<protocol>.dogfood.md`. A fixture without a paired dogfood produces a `warning` from `kanon verify`, not an error — the schema exists but the capture is pending. (See INV-8.)

<!-- INV-fidelity-actor-turn-grammar -->
4. **Actor turn extraction grammar.** In a `<protocol>.dogfood.md` file:
   - A *turn marker* is any line matching the regex `^([A-Z][A-Z0-9_]*):[ \t]+` at column zero.
   - A *turn* begins at a turn marker line and ends at the next turn marker line or EOF. The marker line itself is part of the turn.
   - All turns whose marker matches the fixture's `actor` (case-sensitive, exact match on the captured group) are joined with `\n` to form the *actor text* used by the assertions.
   - Lines outside any turn — file headers, scene-setting prose, blank lines preceding the first turn — are ignored.
   - A dogfood file with zero turns matching `actor` produces an `error`, not a warning: a fixture asserting on no input is a defective contract.

   When the fixture declares `turn_format: bracket`, the turn-marker regex is `^\[([A-Z][A-Z0-9_]*)\][ \t]+` instead. The two formats are mutually exclusive per fixture; a dogfood file is parsed with exactly one grammar. The default is `colon` when `turn_format` is absent, preserving backward compatibility.

<!-- INV-fidelity-assertion-families -->
5. **Assertion families and semantics.** The three families are evaluated independently against the actor text. Each family is optional in the fixture; absent families are skipped silently. When present:
   - **`forbidden_phrases`** — for each regex, run `re.search` against the actor text. ANY match produces one error per matching regex. This catches behaviour the agent must never exhibit.
   - **`required_one_of`** — for each regex, run `re.search` against the actor text. If NO regex matches, produce one error naming the pattern set. This catches "agent must demonstrate at least one of these acceptable behaviours."
   - **`required_all_of`** — for each regex, run `re.search` against the actor text. For each regex that produces no match, produce one error naming the missing regex. This catches "every one of these acceptable behaviours must be present."
   - **`word_share`** — compute the ratio of `\w+` tokens in the actor's turns to `\w+` tokens in all turns (all actors combined). If the ratio is below `min` or above `max`, produce one error. This is a threshold comparison, not a regex match.
   - **`pattern_density`** — for each entry in the list: if `strip_code_fences` is true, remove triple-backtick fenced blocks from the actor text before counting. Count non-overlapping `re.findall` matches for each pattern (union of `pattern` and `patterns` fields). Divide total match count by actor turn count. If the density is below `min` or above `max`, produce one error per entry. Regex compilation errors at fixture-load time are errors.
   Regex compilation errors at fixture-load time are themselves errors with `re.error` text included. All assertions are line-anchored only when the regex itself uses `^`/`$`; the engine does not implicitly anchor.

<!-- INV-fidelity-quantitative-families -->
11. **Quantitative assertion families (ADR-0033).** The `word_share` and `pattern_density` families are built-in quantitative assertion families that operate on the same actor text as the lexical families. They are threshold-based (band comparison over well-defined ratios), not open-ended scoring. Both are optional per-fixture, evaluated independently, and produce errors in the same taxonomy as INV-8. They respect the text-only bounds of INV-7 — no consumer code execution, no subprocess, no network. Adding further quantitative families requires an ADR.

<!-- INV-fidelity-turn-format-extensibility -->
12. **Turn-format extensibility (ADR-0033).** The `turn_format` fixture key selects between `colon` (default, existing grammar) and `bracket` (sensei-compatible grammar `^\[([A-Z][A-Z0-9_]*)\][ \t]+`). The two formats are mutually exclusive per fixture. The default is `colon` when absent, preserving backward compatibility. No consumer-supplied regex is accepted (ReDoS vector). If a third format is needed, it is added as a new enum value with its own pre-compiled regex.

<!-- INV-fidelity-aspect-gated -->
6. **Aspect-gated.** `kanon verify` runs fidelity assertions only when an aspect declaring the `behavioural-verification` capability (per ADR-0026) is enabled at depth ≥ 1. The kit-shipped `kanon-fidelity` aspect is the canonical such aspect; consumers MAY ship a `project-fidelity-*` aspect declaring the same capability and inherit the gate. When no such aspect is enabled, `kanon verify` performs zero filesystem reads under `.kanon/fidelity/` and emits no fidelity-related errors or warnings. This invariant is the contractual link to INV-10 of the verification-contract spec.

<!-- INV-fidelity-text-only-bounds -->
7. **Text-only bounds (carve-out conformance).** The replay engine MUST NOT call `subprocess`, MUST NOT import consumer Python modules, MUST NOT invoke a test runner, MUST NOT call out to an LLM model or any network endpoint. It reads only files committed under the consumer's `.kanon/fidelity/` directory. This is the mechanical realisation of the four bounds enumerated in INV-10 of the verification-contract spec. A test enforces this invariant by static inspection of `src/kanon/_fidelity.py` (no `subprocess`, `importlib`, `socket`, or `urllib` references).

<!-- INV-fidelity-failure-taxonomy -->
8. **Failure taxonomy.** Assertion failures are emitted as `errors:` in the `kanon verify` JSON report — they are the consumer's signal that the agent's behaviour drifted from prose intent. The following are emitted as `warnings:` (non-fatal): a fixture file without a paired `.dogfood.md`, a `.dogfood.md` containing zero turns of any actor, a fixture file with malformed but parseable frontmatter (missing optional keys). The following are `errors:` (fatal): missing required frontmatter keys (`protocol`, `actor`), regex compilation errors, dogfood files with zero turns matching the configured `actor`, and any assertion failure from INV-5.

<!-- INV-fidelity-out-of-scope-tiers -->
9. **Tier-2 and Tier-3 are out of scope.** This spec authorises only Tier-1 (lexical replay over committed text). It does NOT introduce a `kanon transcripts capture` subcommand, does NOT introduce a workstation-evidence-as-CI-artifact pattern, does NOT introduce a paid live-LLM nightly. Each of those, if proposed, requires a new ADR amending or extending the carve-out in `verification-contract.md` INV-10 alongside its own spec. The kit MUST NOT silently grow capture or live-LLM machinery under this aspect's depth dial.

<!-- INV-fidelity-stability -->
10. **Stability: experimental.** First release ships as `experimental`. Promotion to `stable` requires (a) at least one downstream consumer (non-kit, non-sensei) adopting the aspect with a committed fixture pair, and (b) the noise-scrubbing question for captured transcripts being settled by the Tier-2 ADR (which itself remains deferred per INV-9).

## Rationale

**Why a separate aspect, not a depth-3 extension of `kanon-testing`.** The Round-2 architect proposed riding on `kanon-testing` to keep the aspect count bounded. The countervailing argument: behavioural verification has a fundamentally different verification-contract footprint (it requires the INV-10 carve-out; structural and unit testing do not), and the `provides: behavioural-verification` capability is the substitutability handle that makes `project-fidelity-*` aspects possible per ADR-0026. Burying that capability under `kanon-testing` would force any consumer who wants to substitute to override an entire testing aspect. A separate aspect at narrow depth-range [0, 1] preserves the kit's "do one thing, do it well" stance while keeping the aspect-budget impact at +1.

**Why three assertion families and no more.** Sensei's `tests/transcripts/test_fixtures.py` ships these three plus three pedagogy-specific bands (`silence_ratio`, `question_density`, `teaching_density`). The bands assume a tutor/learner vocabulary that does not generalise. The three remaining families are sufficient to encode every behavioural rule kanon's existing protocols ship — "must say X" (`required_one_of`/`required_all_of`), "must not say Y" (`forbidden_phrases`). Adding a fourth family before observing a real failure mode the three cannot encode would be premature schema growth.

**Why regex, not literal strings.** Literal-string matching forecloses anchoring and case-insensitive matching. Sensei's `worktree-lifecycle` audit sentence varies the slug and branch name across instances — `Working in worktree \`.worktrees/[a-z0-9-]+/\`` is the right shape; `Working in worktree .worktrees/foo/` would only catch one instance. Regex with explicit anchoring is also the simplest mental model for the consumer who already writes Python: no DSL to learn.

**Why named-actor turns instead of raw text matching.** Without turn extraction, a fixture asserting "the agent must say X" would also pass when the *user prompt* contained X. The actor-turn grammar is the cheapest filter that rules out false positives from prompts, scene-setting prose, or transcript metadata. The grammar (`^[A-Z][A-Z0-9_]*:[ \t]+`) is uppercase-letter-only by design — common transcript conventions (Claude Code, Sensei's dogfood format, ChatGPT export) all use uppercase actor labels. Lowercase, mixed-case, or inline `<actor>` tags are deliberately not supported in v0.3 to keep the grammar simple; future ADRs may extend.

**Why fixture failures are errors, missing dogfood is a warning.** A consumer who has authored a fixture but not yet captured the dogfood is mid-flight — a warning surfaces the gap without breaking their build. A consumer whose dogfood capture demonstrates the agent broke the protocol has shipped a real defect — the failure must block (errors fail `kanon verify`'s exit code; warnings do not).

**Why depth-range [0, 1], not [0, 2].** [0, 2] would reserve room for a future Tier-2 layer at depth-2. It would also create a "ghost cell" today (depth-2 with no content), which `aspects.md` INV-3 explicitly forbids. When Tier-2 ships, it lands as a depth-range widening alongside its ADR — small migration, honest signal.

**Why no scaffolded sample fixture.** A scaffolded sample with placeholder content will be left in place by the consumer, polluting `kanon verify` output with "example" failures forever. The protocol prose at `.kanon/protocols/kanon-fidelity/fidelity-fixture-authoring.md` includes complete example fixtures inline; consumers copy-paste from prose, not from a placeholder file.

## Out of Scope

- **`kanon transcripts capture` subcommand.** Tier-2 capture-from-live-agent is deferred to v0.4 with its own spec and ADR.
- **Live-LLM nightly e2e against an actual Claude Code or other CLI.** Tier-3 is deferred indefinitely; document the recipe only.
- **Score-based assertions beyond built-in families** (e.g., arbitrary numeric scoring functions). The `word_share` and `pattern_density` families are threshold-based (band comparison over well-defined ratios), not open-ended scoring. Adding further quantitative families requires an ADR.
- **Per-fixture model-version pinning.** ADR-0005's `validated-against:` frontmatter MAY be added to fixtures in a future ADR, but the v0.3 spec does not require or recognise it. Today every fixture is implicitly model-agnostic at Tier-1 (lexical assertions don't depend on which model produced the dogfood).
- **Cross-actor assertions** ("after AGENT says X, USER must say Y"). Multi-turn conversation analysis is out of scope; sequence-aware assertions await a separate spec.
- **Auto-generation of fixtures from protocol prose.** Symmetric to the kit's overall stance against spec-to-code generation (`docs/foundations/vision.md` § Non-Goals).
- **Coverage-style "% of protocols with fidelity fixtures" metric.** Useful but premature; revisit after Tier-2 lands.

## Decisions

See:
- [ADR-0029](../decisions/0029-verification-fidelity-replay-carveout.md) — verification-contract carve-out for fidelity-fixture replay (the spec gap this aspect closes).
- [ADR-0031](../decisions/0031-fidelity-aspect.md) — `kanon-fidelity` aspect: depth-range, capability declaration, scaffolding choices, the three-assertion-family decision.
- [ADR-0033](../decisions/0033-fidelity-quantitative-families.md) — quantitative assertion families and turn-format extensibility (supersedes ADR-0031's rejection of quantitative metrics).
