---
status: accepted
date: 2026-04-27
depth-min: 3
invoke-when: An ADR is being modified after acceptance, or a contributor proposes a body edit on an `accepted` / `accepted (lite)` ADR
---
# Protocol: ADR immutability

## Purpose

Make the rule "ADRs are immutable once accepted" survive contact with normal lifecycle (factual corrections, INV-ID renumbering, version-label updates) without weakening into a rubber stamp. Ratified by ADR-0032 in the kit's own repo; consumers adopt this protocol when they want the same discipline in their own ADR catalogs.

## Steps

### 1. Confirm the ADR is past `accepted`

The rule applies only to ADRs whose frontmatter `status` is `accepted` or `accepted (lite)`. Drafts (`status: draft`), provisional ADRs (`status: provisional`), and superseded ADRs (`status: superseded`) are mutable by definition. Body edits to non-accepted ADRs do not need this protocol.

### 2. Classify the proposed edit

Three exception classes from ADR-0032 are mutually exclusive — each edit fits exactly one:

- **Frontmatter-only.** Status FSM transitions (`provisional` → `accepted`, `accepted` → `superseded`), date updates that accompany those transitions, and `superseded-by:` annotations. The body is unchanged byte-for-byte. **No further action; the edit lands as a normal commit.**
- **Appending a `## Historical Note` section.** A strict suffix-only addition that begins with `## Historical Note` (or a deeper heading). Preserves archaeology without altering prior claims. **Land as a normal commit; no trailer required.**
- **Body edit (factual correction, INV-ID migration, version-label refresh).** Changes existing prose. Either supersede or use the trailer (Step 3).

If the proposed edit reverses or substantively changes the *decision* the ADR records, do **not** use either exception. Write a new ADR that supersedes the old one and set the old one's status to `superseded` with a `superseded-by: NNNN` frontmatter field.

### 3. If a body edit is justified, add the `Allow-ADR-edit:` trailer

The trailer is a line in the commit message with this exact shape:

```
Allow-ADR-edit: NNNN — <reason>
```

- `NNNN` is the four-digit ADR number being edited. Comma-separated lists are accepted: `Allow-ADR-edit: 0011, 0013, 0014 — INV-ID migration per ADR-0018`.
- The separator before the reason can be em-dash (`—`), en-dash (`–`), ASCII hyphen (`-`), or colon (`:`).
- The reason MUST be non-empty and SHOULD be a one-sentence justification a reviewer can evaluate in `git log`.

The trailer is the audit log. It travels with the commit forever, visible in `git log` and in PR review without spelunking side discussion.

### 4. Choose the enforcement mechanism for your project

Consumers pick what fits their team's discipline maturity:

- **CI gate.** Copy a script analogous to the kit's `ci/check_adr_immutability.py` (kanon's source repo ships it kit-internal; it is **not** scaffolded by any aspect — copy the file if you want it). Wire into your test workflow with two modes: PR mode runs `--base-ref origin/main` against the PR's commits; push mode (default) runs only against `HEAD`. Hard-fails the CI run on any unannotated body change to an accepted ADR.
- **Pre-commit hook.** Run the same script in `.git/hooks/pre-commit` to catch violations before they reach the remote. Cheaper than CI; misses force-pushed commits.
- **Manual review checklist.** Add the rule to your pull-request template ("Body edits to accepted ADRs require either a superseder or an `Allow-ADR-edit:` trailer"). Cheapest; relies on reviewer discipline.

The kit teaches the rule and ships the reference script; the consumer chooses which enforcement strength fits their repo. There is no "default" — making this an aspect-level config knob would imply a one-size-fits-all answer that does not exist.

### 5. If a violation slips through

Pre-existing violations in `git log` are not retroactively rewritten — that would require a force-push that breaks every downstream consumer's checkout. Two corrective options:

- Append a `## Historical Note` section to the ADR explaining the post-hoc edit, citing the offending commit SHA.
- Write a superseding ADR that records the actual decision history (the original ADR + the post-acceptance amendment + the conclusion).

Both are honest signals that survive in the archaeological record.

## Exit criteria

- The proposed edit fits exactly one of the three exception classes (Step 2).
- If a body edit, the commit message carries a syntactically valid `Allow-ADR-edit:` trailer with a non-empty reason (Step 3).
- The project's chosen enforcement mechanism (CI gate / pre-commit / manual review) is in place (Step 4).
- A reviewer reading the commit can evaluate the justification without external context.

## Anti-patterns

- **Editing accepted ADRs without the trailer because "it's just a typo."** The escape hatch exists precisely for cases like that. Use it.
- **Treating frontmatter-only changes as needing a trailer.** They don't. The rule is body-immutability.
- **Vague reasons in the trailer.** `Allow-ADR-edit: 0011 — fix` tells a future reviewer nothing. Write the one-sentence why.
- **Appending a `## Historical Note` to retroactively justify an arbitrary edit.** The exception is for *adding archaeology*, not rewriting prior claims. If the edit changes existing text, use the trailer or supersede.
- **Force-pushing to rewrite history of merged ADR violations.** Pre-existing violations stay in `git log`; correct via Historical Note or superseding ADR.
- **Shipping the CI gate to consumers as a default-on aspect file.** The kit's stance per ADR-0032: the rule ships as protocol prose; the script ships as a copy-able reference. Consumers opt in by copying.
