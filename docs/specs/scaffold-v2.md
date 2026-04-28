---
status: draft
date: 2026-04-28
realizes:
  - P-prose-is-code
  - P-tiers-insulate
stressed_by:
  - solo-engineer
  - onboarding-agent
fixtures_deferred: "Spec covers architectural changes; fixtures will be added with implementation plans"
---
# Spec: Scaffold v2 — thin kernel, routing-index AGENTS.md, three file categories

## Intent

Restructure kanon's scaffolding model so that (1) no aspect is structurally privileged, (2) AGENTS.md is a slim routing index rather than a content repository, (3) files are cleanly categorized as kit-global, aspect-level, or depth-level, and (4) agents load discipline content on-demand via protocol references rather than reading it inline at boot.

## Invariants

<!-- INV-scaffold-v2-three-categories -->
1. **Three file categories.** Every scaffolded file belongs to exactly one category:
   - **Kit-global**: declared in the top-level manifest under `files:`. Scaffolded for every `kanon init` regardless of which aspects are enabled. Source: `src/kanon/kit/files/`.
   - **Aspect-level**: declared in an aspect sub-manifest under a top-level `files:` key (outside any `depth-N:` block). Scaffolded when the aspect is enabled at any depth ≥ 0.
   - **Depth-level**: declared in an aspect sub-manifest under `depth-N: files:`. Scaffolded when the aspect is at depth ≥ N (existing union semantics, unchanged).

<!-- INV-scaffold-v2-no-privileged-aspect -->
2. **No privileged aspect.** Any aspect — including `kanon-sdd` — can be completely disabled. A project with `kanon init --aspects worktrees:1,testing:1` (no sdd) receives zero sdd files, zero sdd protocols, and zero sdd AGENTS.md sections. The `defaults:` key in the top-level manifest is a CLI convenience default, not a structural requirement.

<!-- INV-scaffold-v2-routing-index -->
3. **AGENTS.md is a routing index.** AGENTS.md contains identity, boot chain, project layout, key constraints, a task playbook, a hard-gates table, the protocols-index, and contribution conventions. It does NOT inline discipline prose, aspect body descriptions, or protocol procedures. All discipline content lives in protocol files referenced by the protocols-index table.

<!-- INV-scaffold-v2-hard-gates-inline -->
4. **Hard gates stay inline (compressed).** The plan-before-build, spec-before-design, and worktree-isolation gates remain in AGENTS.md as a hard-gates table: one row per gate with trigger condition, one-sentence summary, audit-trail sentence, and link to the full protocol. This preserves enforcement proximity per ADR-0010's principle while eliminating the 48 lines of inlined gate prose. The full gate procedures (trivial/non-trivial criteria, detailed rules) move to protocol files.

<!-- INV-scaffold-v2-no-duplicate-content -->
5. **No duplicate content.** Content that exists in a protocol file does NOT also exist as an AGENTS.md marker section. The current duplication (test-discipline, secure-defaults, dependency-hygiene exist as both AGENTS.md sections AND protocol files) is eliminated. The protocol file is the single source; the protocols-index table is the routing pointer.

<!-- INV-scaffold-v2-sections-eliminated -->
6. **Marker sections eliminated (except protocols-index).** The `sections:` key in aspect sub-manifests is removed. The `<!-- kanon:begin/end -->` marker mechanism is retained only for the dynamically-rendered `protocols-index` table. All former section content moves to protocol files.

<!-- INV-scaffold-v2-sdd-method -->
7. **SDD method document.** `docs/development-process.md` is renamed to `docs/sdd-method.md`, owned by the sdd aspect as an aspect-level file. It is trimmed to ~50 lines containing only content with no other home: the layer stack table, how-work-flows routing, document authority, and glossary. Duplicated content (when-to-write-a-plan, when-to-write-a-spec) is removed — those rules live in the gate protocols. Depth-specific content (foundations, design docs) moves to depth-level files or artifact-directory READMEs.

<!-- INV-scaffold-v2-kit-global-files -->
8. **Kit-global files.** The top-level manifest declares `.kanon/kit.md` as a kit-global file. `kit.md` is rewritten to be aspect-neutral (no sdd-specific references). Harness shims remain handled by `harnesses.yaml` (already aspect-agnostic).

<!-- INV-scaffold-v2-agents-md-assembly -->
9. **AGENTS.md assembly simplification.** `_assemble_agents_md()` loads the base template, renders the protocols-index table, and stops. No body injection, no section filling, no inactive-section cleanup. The base template is the complete routing index; the protocols-index is the only dynamic element.

<!-- INV-scaffold-v2-aspect-dependencies -->
10. **Aspect dependency loosening.** `kanon-worktrees` changes `requires: "kanon-sdd >= 1"` to `suggests: "kanon-sdd >= 1"`. Worktree isolation is orthogonal to planning discipline. Other aspects with sdd hard-dependencies are similarly loosened to `suggests:` where the dependency is advisory rather than functional.

## Rationale

The current AGENTS.md is 406 lines at depth 3, of which 71% is inlined content that duplicates protocol files or describes aspect bodies. This content competes with the actual task in the agent's context window. Anthropic's Agent Skills research shows 40-60% context waste with monolithic loading. The routing-index model reduces AGENTS.md to ~85 lines at depth 3 and ~60 lines at depth 1, with discipline content loaded on-demand when protocol triggers fire.

The three file categories make the manifest's intent explicit: kit-global files are always present, aspect-level files appear when an aspect is enabled, depth-level files appear at specific depths. This eliminates the current hack of declaring aspect-wide files at depth-0 or depth-1 and relying on union semantics to make them persist.

Making sdd fully optional follows the aspect model's own design principle: aspects are opt-in discipline bundles. A project that wants worktree isolation and test discipline without SDD's planning ceremony is a legitimate use case.

## Out of Scope

- Third-party aspect publishing (`acme-*` namespace) — remains deferred per ADR-0012.
- Conditional file content based on which aspects are enabled (cross-aspect file dependencies).
- Runtime harness detection for AGENTS.md content adaptation (all harnesses get the same AGENTS.md).
- Depth-3 fidelity (workstation capture, live-LLM nightly) — remains deferred.

## Decisions

Supersedes ADR-0010 § enforcement-proximity (refines, does not reverse: hard gates stay inline as compressed table rows; soft guidance moves to protocol-only). Extends ADR-0012 (aspect model) with the three file categories. Extends ADR-0016 (aspect decoupling) by completing sdd's de-privileging.
