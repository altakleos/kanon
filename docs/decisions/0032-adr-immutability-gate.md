---
status: accepted
date: 2026-04-27
---
# ADR-0032: ADR-immutability gate — mechanical enforcement with a calibrated escape hatch

## Context

`docs/development-process.md` § ADRs has long stated:

> ADRs are **immutable** once accepted. To reverse a decision, write a new ADR that supersedes it and set the old one's status to `superseded`.

The Round-2 verification panel surfaced empirical evidence that this rule has zero mechanical enforcement and is being violated in kanon's own history. A `git log --diff-filter=M -- 'docs/decisions/*.md'` reveals at least four post-acceptance ADR-body modifications without superseding ADRs and without any in-band annotation:

- `0cbcbdd` — substantive Decision-block edit on the accepted ADR-0001 (package-name change from `kanon` to `kanon-kit`); the author labelled it "factual correction" in the commit message but did not supersede or annotate the ADR itself.
- `021d178` — body edit to the accepted ADR-0011 ("v0.2 protocol layer" → "the protocol layer"); self-justified as a version-label correction.
- `45cd42d` — body edits across three accepted ADRs (0011, 0013, 0014) replacing legacy invariant numbers with the new INV-IDs introduced by ADR-0018.

The Round-1 process-archaeology panelist recommended shipping a CI gate (EH-P1, High confidence). The Round-2 critic correctly observed that the *bare* immutability rule is too strict for normal lifecycle (factual corrections, INV-ID renumbering, version-label updates are real maintenance work that should not require a superseder per case). The countervailing rebuttal: sensei's reference implementation already calibrated this — the `Allow-ADR-edit: NNNN — <reason>` commit-message trailer is the documented escape hatch that absorbs lifecycle work without weakening the rule. We adopt the calibrated form, not the bare rule.

The gate runs **kit-internal only**. Per the Round-1 critic's remaining concern, shipping the script as a default-on kit asset would implicitly classify ADR mutations as bugs in *every* consumer's repo regardless of their discipline maturity — a strong claim the evidence does not support. Consumers who want the same gate get a consumer-facing protocol at `kanon-sdd` depth 3 listing several enforcement options (CI gate, pre-commit hook, manual review checklist); they pick what fits their team.

## Decision

Three parts:

### 1. Mechanical enforcement on kanon's own CI

Ship `ci/check_adr_immutability.py` (ported from sensei with kit-internal path constants) and wire it into `.github/workflows/verify.yml` as a hard CI gate. Two operating modes:

- **PR mode** (default for `pull_request` events): walk every commit in `BASE_REF..HEAD` (typically `origin/main..HEAD`) and check each ADR change.
- **Push mode** (default for `push` events on `main`): check only the most-recent commit (HEAD).

Failure surfaces a structured error per violation listing the ADR number, the offending commit, and the canonical remediation: write a superseding ADR, append a `## Historical Note` section, or add an `Allow-ADR-edit:` trailer.

### 2. Three exception classes (the calibration)

The bare rule "ADR bodies are immutable once accepted" is too strict for normal lifecycle. Three explicit exceptions are honoured by the gate:

1. **Frontmatter-only changes.** Status FSM transitions (`provisional` → `accepted`, `accepted` → `superseded`), date updates that accompany those transitions, and `superseded-by:` annotations. Body bytes are unchanged.
2. **Appending a `## Historical Note` section.** The diff is a strict suffix-only addition that begins with a `## Historical Note` (or deeper) heading. Preserves archaeology without altering prior claims.
3. **Explicit opt-out via commit-message trailer.** A line of the form `Allow-ADR-edit: NNNN — <reason>` cites the four-digit ADR number with a non-empty reason. Multiple ADRs can be listed comma-separated. Em-dash, en-dash, ASCII hyphen, or colon all work as the separator before the reason. The trailer is the audit trail for the rare case where superseding is the wrong tool (typo, factual correction post-merge, INV-ID migration); reviewers see the rationale in `git log` without having to spelunk side discussion.

### 3. Consumer-facing protocol prose at `kanon-sdd` depth 3

Author `src/kanon/kit/aspects/kanon-sdd/protocols/adr-immutability.md` describing the rule and listing enforcement options for downstream consumers — CI gate (port the kit's script), pre-commit hook (run the same script against `HEAD`), manual review (the kit teaches the rule; review enforces it). The kit does **not** ship the script itself as a scaffolded file under any aspect — consumers opt in by copying the script if they want it, or by following the protocol prose for unmechanised review.

`docs/development-process.md` § ADRs gains a paragraph naming the trailer's exact shape so authors find it without having to read this ADR.

## Alternatives Considered

1. **Ship the bare rule with no escape hatch.** Rejected: the Round-2 scientist counted ~24 lifecycle modifications/month under a strict definition (cosmetic mass-renames, cross-reference updates, factual corrections). Without an escape hatch, every one of those would require a superseding ADR — a clear over-engineering. Sensei learned this empirically; we adopt their fix from the start.

2. **Don't ship the gate; rely on prose only.** Rejected: empirically, prose enforcement has produced ≥4 unannotated violations in kanon's own history. The Round-2 verifier's `git log` survey settled this — the rule is real-incidence, not aspirational. The Round-1 critic was correct that the gate must be calibrated; the Round-2 evidence is correct that uncalibrated prose is insufficient.

3. **Ship the script as a default-on kit asset that consumers inherit at every depth.** Rejected: implicitly classifies ADR mutations as bugs in every consumer's repo regardless of their discipline maturity (Round-1 critic's argument). Different consumers want different enforcement strengths. Shipping a protocol at `kanon-sdd` depth 3 with several enforcement-option listings respects the consumer's discipline ladder — the same instinct that motivated the [0,1] depth-range of the `kanon-fidelity` aspect (ADR-0031).

4. **Use an ADR-internal frontmatter field (e.g., `editable: true`) instead of a commit-message trailer.** Rejected: the trailer is *post-hoc audit* tied to the commit that does the editing, which is exactly where reviewers look. A frontmatter field would have to be added BEFORE the edit (chicken-and-egg) and would persist after the edit (clutter); the trailer disappears once the commit is merged but lives in `git log` forever. Sensei's choice is correct here.

5. **Implement the gate as part of `kanon verify` instead of a standalone CI script.** Rejected: `kanon verify` is structural-only by INV-9 of `verification-contract.md`. INV-10 (ADR-0029) carved out one narrow exception for fidelity replay; carving out a second for git-history walking would dilute the carve-out's bound. The immutability gate belongs in the kit-author's CI surface, not the consumer-facing verify surface. ADR-0030 (recovery-model) likewise kept its discipline as a CI-shaped concern, not a verify-time one.

6. **Bundle the gate's rollout with a backfill of `Allow-ADR-edit:` trailers on the four pre-existing violations.** Rejected: those violations are in merged commits; rewriting their messages would require a force-push to `main`. The honest signal is to leave them as historical violations (`git log` will continue to show them as such; the gate runs forward-only via PR mode against `origin/main`). A `## Historical Note` could be appended retroactively to the affected ADRs if the maintainer chooses, but that is a separate decision and out of scope for this ADR.

## Consequences

- **kanon's CI gains a hard gate.** PRs that mutate accepted-ADR bodies fail unless they (a) supersede with a new ADR, (b) append a `## Historical Note` section, or (c) carry an `Allow-ADR-edit:` trailer. The gate runs on every push to `main` and every PR.
- **Pre-existing violations remain in history.** The four unannotated body modifications enumerated in §Context stay as-is; the gate runs forward-only.
- **A new consumer-facing protocol** (`adr-immutability.md`) ships under `kanon-sdd` depth 3 listing enforcement options. Consumers at depth 0–2 see no change.
- **`docs/development-process.md` § ADRs gains a trailer paragraph** so the rule and its escape hatch are discoverable without reading this ADR.
- **`Allow-ADR-edit:` becomes a contract trailer**: future kanon-author tooling (e.g., commit templates) can reference it; reviewers learn to recognise it.
- **No new aspect.** The gate lives in `ci/`, the prose in `kanon-sdd/protocols/`. The kit's aspect-count remains at 7 (Skeptic's hard-cap-at-8 from Round-2 still satisfied).
- **Trust boundary unchanged.** The gate runs git commands against the kit's own repo in CI; no LLM, no network, no consumer code execution. Same posture as `check_kit_consistency.py`.

## Config Impact

None. The gate has no tunable thresholds today; the three exception classes are baked-in by design (every additional escape hatch widens the rule's permissiveness). A future ADR may revisit if a real consumer demonstrates a fourth legitimate exception class.

## References

- `docs/plans/fidelity-and-immutability.md` — the plan this ADR is Track 2 of.
- `docs/development-process.md` § ADRs — the prose rule this ADR mechanises.
- [ADR-0024](0024-crash-consistent-atomicity.md) — atomic-write contract; orthogonal but the ADR-immutability gate composes with it (CI runs against committed state, atomicity is a runtime concern).
- [ADR-0029](0029-verification-fidelity-replay-carveout.md) and [ADR-0031](0031-fidelity-aspect.md) — Track 0 and Track 1 of the same plan; this ADR is Track 2.
- [ADR-0030](0030-recovery-model.md) — also a CI-shaped discipline addition, sets the precedent that kit-internal CI gates ship as `ci/check_*.py` rather than as kit-shipped consumer assets.
- Sensei `ci/check_adr_immutability.py` and `docs/plans/adr-immutability-gate.md` — reference implementation; this ADR's gate is a near-verbatim port with kanon-specific path constants.
