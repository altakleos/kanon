# Architecture Decision Records

Each file in this directory records a single architectural decision with its context, the choice made, alternatives considered, and consequences.

## What is an ADR

An Architecture Decision Record captures a single decision with its context, the choice made, alternatives considered, and consequences. ADRs are the "why" layer — they explain reasoning that might otherwise seem arbitrary to a future reader.

ADRs are NOT the starting point for new work. They are produced DURING design and implementation, as decisions crystallize. A feature might produce zero ADRs (if it follows existing patterns) or several (if it requires novel choices).

ADRs are **immutable** once accepted. To reverse a decision, write a new ADR that supersedes it and set the old one's status to `superseded`.

The immutability rule honours three exception classes for normal lifecycle: (1) **frontmatter-only changes** (status FSM transitions, date updates, `superseded-by:` annotations), (2) **appending a `## Historical Note` (or deeper) section** at the end of the file, and (3) **explicit opt-out via a commit-message trailer** of the form `Allow-ADR-edit: NNNN — <reason>` citing the four-digit ADR number with a non-empty reason. Multiple ADRs can be listed comma-separated; em-dash, en-dash, ASCII hyphen, or colon all work as the separator before the reason. The trailer is the post-hoc audit log for the rare case (typo, factual correction, INV-ID migration) where superseding is the wrong tool. Projects that want to enforce this discipline mechanically can run a CI gate over `git log` against `docs/decisions/*.md`.

## Status values

- `accepted` — decision is committed; behavior must match.
- `accepted (lite)` — ADR-lite format; same weight as `accepted`.
- `provisional` — accepted on current evidence, flagged for review when verification evidence lands (e.g., the protocol it governs gains a passing transcript fixture, or a superseding ADR proves the original wrong). A commitment to revisit, not a deferral.
- `superseded` — replaced by a later ADR. The superseding ADR's number must appear in the original's header.

Authors of new ADRs should prefer `provisional` when the decision governs a feature still in draft or when no fixture has yet validated the design property the decision turns on.

## When to write an ADR

ADRs come in two weights.

### Full ADR (~40 lines)

Use when the decision changes the **model** — new architecture, new enforcement philosophy, genuine debate with multiple viable alternatives. Format: YAML frontmatter (`status`, `date`), then Context, Decision, Alternatives Considered, Consequences, optional Config Impact.

Warranted when:
- The decision has genuine alternatives that were debated.
- A future reader might ask "why was it done this way?" and need a full narrative.
- The decision constrains future work (establishing an invariant, choosing a data format, picking an architecture pattern).
- The decision was debated or reversed a previous approach.

When in doubt whether a decision warrants a full ADR or an ADR-lite, default to full ADR. The cost of over-documenting a decision is low; the cost of under-documenting one that a future contributor needs to understand is high.

### ADR-lite (~12 lines)

Use when the decision changes **behavior within an existing model** — gate changes, default changes, boundary changes. Format: YAML frontmatter (`status`, `date`, `weight: lite`, `protocols: [names]`), then three fields: Decision, Why, Alternative.

Concrete triggers (any one):
1. Changes a human approval gate (adds, removes, or bypasses).
2. Changes a default that alters out-of-box behavior.
3. Moves something from blocked to allowed (or vice versa).
4. Introduces a config knob whose existence encodes a design choice.

### No ADR needed

Bug fixes, threshold tuning, documentation improvements, presentation/formatting changes, adding a new output type that follows existing patterns, routine implementation updates with no meaningful alternative.

## Index

*(empty — add ADRs as you make load-bearing decisions)*

## ADR Template

See [`_template.md`](_template.md).
