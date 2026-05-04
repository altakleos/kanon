---
status: accepted
date: 2026-05-04
implements: ADR-0056
---
# Design: SDD Protocol Gaps

## Context

The SDD aspect has five depth-1 protocols (`plan-before-build`, `scope-check`, `completion-checklist`, `verify-triage`, `tier-up-advisor`) and three depth-2 protocols (`spec-review`, `spec-before-design`, `adr-immutability`). Depth 3 has zero protocols despite scaffolding design docs and foundations.

Two behavioural gaps remain:

1. **ADR authoring discipline.** Agents skip ADRs for non-obvious choices, or write them retroactively after the code is committed. The `docs/decisions/README.md` rubric exists but nothing forces the agent to consult it at decision time.
2. **Design-before-plan ordering.** At depth 3, agents jump from spec straight to plan, bypassing the design doc that captures component boundaries and cross-component interfaces. The `docs/design/README.md` skip conditions exist but nothing gates the transition.

Both gaps are behavioural (agents skip steps), not qualitative (agents write bad docs). The fix is two new gate protocols — one at depth 1, one at depth 3.

## Architecture

### Protocol 1: `adr-authoring` (depth-min: 1, gate)

**Trigger:** A non-obvious technical choice is being made during design or planning, or the agent identifies a choice with genuine alternatives, or the agent is unsure whether an ADR is needed.

**Steps:**

1. **Classify** the decision using the rubric from `docs/decisions/README.md`: full ADR (model change, genuine debate, constrains future work) vs ADR-lite (gate/default/boundary change within existing model) vs no ADR needed (bug fix, threshold tuning, pattern-following). If no ADR needed, stop.
2. **Search existing ADRs:** scan `docs/decisions/` for ADRs touching the same component or capability. List related ADRs for the References section.
3. **Write the ADR** using `docs/decisions/_template.md`. Number sequentially. Write as `status: draft` (never `status: accepted` — the user promotes).
4. **Quality gate:** Alternatives Considered must list ≥2 genuine alternatives for full ADRs (≥1 for lite). "Do nothing" counts. Consequences must include at least one tradeoff or cost. Decision statement must be a single declarative sentence.
5. **Ordering guard:** An ADR records a decision *being made*, not a decision already implemented. If the code already exists, flag this to the user — it's a Historical Note, not a standard ADR.
6. **State the audit sentence:** "ADR at `<path>` has been drafted for review."

**Exit criteria:** ADR file exists at `docs/decisions/NNNN-<slug>.md` with valid frontmatter, all required sections populated, `status: draft`, and audit sentence stated.

**Anti-patterns:**

- Retroactive ADRs disguised as forward decisions
- Strawman alternatives ("Alternative: don't do it" with no analysis)
- Missing cross-references to related ADRs
- Writing as `status: accepted` (bypasses review)

### Protocol 2: `design-before-plan` (depth-min: 3, gate)

**Trigger:** About to write a plan for a change where (a) a spec exists, AND (b) the change introduces new component boundaries, cross-component interfaces, or non-obvious architectural mechanisms.

**Steps:**

1. **Check** if a design doc already exists for this spec. If yes and it covers the architectural scope, state the audit sentence and proceed to planning.
2. If no design doc exists, or the existing one doesn't cover the new scope: **write** a design doc at `docs/design/<slug>.md` using the template. The design doc must have: Context, Architecture (naming components and their boundaries), Interfaces (public contracts between components), and Decisions (non-obvious choices made).
3. The design doc's frontmatter must include `implements:` linking to the relevant ADR or spec.
4. **State the audit sentence:** "Design doc at `<path>` covers the architectural scope."

**Exit criteria:** Design doc exists with valid frontmatter, Architecture section names components, Interfaces section lists boundaries, and audit sentence stated.

**When NOT to fire** (explicit skip conditions from `docs/design/README.md`):

- The change follows an existing pattern with no new boundaries
- The change is a bug fix or threshold tuning
- The spec is self-contained and the implementation is obvious
- The plan would be identical to the design doc (no added value)

## Interfaces

### Manifest changes

The SDD sub-manifest (`kanon_sdd/manifest.yaml`) gains one protocol entry at each affected depth:

```yaml
depth-1:
  protocols:
    # ... existing 5 ...
    - adr-authoring.md          # NEW

depth-3:
  protocols:
    - design-before-plan.md     # NEW
```

Strict-superset semantics means `adr-authoring` is active at depths 1–3 and `design-before-plan` is active at depth 3 only.

### AGENTS.md protocols-index additions

Two new rows in the `kanon-sdd` table:

| Protocol | Depth | Trigger |
|----------|-------|---------|
| `adr-authoring` | 1 | A non-obvious technical choice is being made during design or planning |
| `design-before-plan` | 3 | About to write a plan where a spec exists and the change introduces new component boundaries |

### Protocol file locations

```
packages/kanon-aspects/src/kanon_aspects/aspects/kanon_sdd/protocols/
├── adr-authoring.md          # NEW
└── design-before-plan.md     # NEW
```

## Decisions

1. **Gate over quality.** Both protocols are gates (block action until satisfied), not quality reviews. The gap is behavioural (agents skip steps), not qualitative (agents write bad docs). A gate is the minimal mechanism that closes the gap.

2. **`adr-authoring` at depth 1, not depth 2.** ADRs are scaffolded at depth 1 — `docs/decisions/README.md` and `_template.md` land there. If you have the template, you should have the discipline. Deferring to depth 2 leaves a gap where agents make decisions without recording them.

3. **`design-before-plan` at depth 3, not depth 2.** Depth-2 specs are often self-contained enough that a separate design doc adds no value. Depth 3 is where component boundaries and cross-cutting concerns justify the ceremony — it's also where `docs/design/` is first scaffolded.

4. **No foundations protocol.** Vision, personas, and principles are human-directed. Agents don't autonomously create them. Templates + README guidance is sufficient; a gate protocol would fire on false positives.

5. **Lightweight classification step in `adr-authoring`.** The protocol must not become a tax on every change. Step 1 (classify) should take <30 seconds for the agent. The `docs/decisions/README.md` full/lite/none rubric is the decision tree — the protocol references it rather than duplicating it.
