---
status: accepted
date: 2026-05-04
---
# ADR-0058: Foundations coherence — automatic vision-drift detection

## Context

When `vision.md` changes in a consumer repo, principles and personas that were
derived from it may become stale or contradictory. Currently nothing detects
this. In agent-driven repos, an LLM writing specs months after a vision change
will read stale principles without any signal that the foundations are
internally inconsistent.

The detection must be fully automatic — no manual date bumping, no manual
acknowledgment commands. Agents and humans alike should receive a clear signal
at both verify time and spec-authoring time that the foundations layer may be
internally inconsistent.

ADR-0057 moved foundations to depth 2, making them active inputs to the spec
authoring flow. That decision amplifies the cost of stale foundations: agents
now consult principles and personas before writing every spec, so outdated
foundations silently degrade spec quality across the entire project.

## Decision

Add a `foundations_coherence` validator at SDD depth 2 that automatically
detects when `vision.md` has changed but no principle or persona file has been
modified since. The validator computes a SHA-256 hash of `vision.md` and stores
it in `.kanon/foundations-vision.sha`. On subsequent runs, if the hash differs
and no `.md` file under `principles/` or `personas/` has a modification time
newer than `vision.md`, it emits a warning. The warning auto-clears when any
downstream file is modified after the vision change — no manual acknowledgment
is required.

The stored hash is not updated when the warning fires. This makes the warning
persistent: it continues to appear on every `kanon verify` run until someone
actually updates a downstream file, at which point the validator updates the
stored hash and goes silent.

Additionally, amend the spec-before-design protocol's Step 2 ("Consult
foundations") to check this condition before the agent writes a spec. If
`kanon verify` has flagged a foundations-coherence warning, the agent surfaces
it to the user before proceeding. This places the staleness signal at authoring
time, not just verify time.

## Alternatives Considered

1. **Frontmatter date fields in each foundation file.** Rejected: requires
   manual bumping. Agents and humans will forget, and the detection becomes
   unreliable.

2. **Single warning with a manual `kanon ack` command.** Rejected: requires
   manual action to clear the warning. The auto-clearing design is strictly
   better — it fires when there is a real problem and goes silent when the
   problem is addressed, with no ceremony.

3. **Do nothing.** Rejected: consumer repos will have frequent vision changes
   as projects mature. Without detection, principles and personas silently
   drift, and agents produce specs grounded in outdated project stances.

4. **Per-principle granular warnings.** Rejected: too noisy. A single summary
   warning ("vision changed, review your foundations") is sufficient to prompt
   a review pass. Per-file warnings would generate N warnings for N principle
   files, all saying the same thing.

## Consequences

- **Positive.** Automatic detection with zero manual ceremony. The warning
  fires at both `kanon verify` time and spec-authoring time (via the
  spec-before-design protocol amendment), covering both CI and interactive
  agent workflows.

- **Positive.** Self-clearing: updating any principle or persona file after
  the vision change silences the warning. No acknowledgment command needed.

- **Negative.** The validator uses file modification times (mtime) for the
  "has a downstream file been updated?" check. This is simple and works
  everywhere (including non-git repos), but mtime can be unreliable across
  file-system operations like `git checkout` or `cp -a`. This is acceptable
  for a warning-level signal — false positives prompt a harmless review,
  and false negatives are corrected on the next vision edit.

## References

- [ADR-0057: Move foundations to depth 2](0057-foundations-to-depth-2.md)
