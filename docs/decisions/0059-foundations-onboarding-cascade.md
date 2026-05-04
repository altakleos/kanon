---
status: accepted
date: 2026-05-04
supersedes-partial: 0056 (decision §4 only)
---
# ADR-0059: Foundations onboarding cascade — LLM-human collaboration on project identity

## Context

ADR-0056 rejected a foundations-authoring protocol on the premise that "humans
drive those artifacts" and agents don't autonomously create them. The decision
was sound at the time: foundations are strategic documents, and the substrate
should not have agents unilaterally inventing a project's vision or principles.

ADR-0057 then moved foundations from depth 3 to depth 2, making them active
inputs to the spec authoring flow. The spec-before-design protocol's Step 2
now instructs agents to scan `docs/foundations/` before writing a spec — read
`vision.md` for mission alignment, scan `principles/` for design constraints,
and scan `personas/` for stress dimensions.

But on a fresh depth-2 project, foundations are empty templates. The agent
dutifully scans them in Step 2 and gets zero useful context: a `vision.md`
with `status: draft` and angle-bracket placeholders, empty principle and
persona directories. The entire ADR-0057 benefit — grounding specs in project
identity — is defeated until a human manually populates the files. In practice,
humans don't populate them unprompted. The files sit empty for weeks or months,
and every spec written in that window lacks the context ADR-0057 intended to
provide.

The premise ADR-0056 relied on — that agents don't author foundations — is not
wrong, but it is incomplete. The right model is not "agents author foundations"
or "humans author foundations" but "agents partner with humans to populate
foundations at the natural moment." That moment is when the first spec is about
to be written: the agent needs context, the human has context, and the
conversation is already happening.

## Decision

Supersede ADR-0056 decision §4 ("Do not add a foundations-authoring protocol").

Add a conditional foundations onboarding cascade to spec-before-design Step 2.
When the agent detects that `vision.md` contains only template content
(`status: draft` with no project-specific narrative), it pauses and asks the
user for a one-paragraph project description. If the user provides one, the
agent populates `vision.md` with their answer, structured into Mission,
Non-goals, and Key bets sections. Then, in a single checkpoint, the agent
presents extracted candidate principles and (if derivable) personas, and asks
the user which to capture. The agent writes whichever artifacts the user
approves, then proceeds to write the spec grounded in the populated foundations.

The cascade is interruptible at every step — the user can decline the vision
prompt and skip directly to the spec. This is a recommendation, not a gate.

This is a one-time flow. It fires only when foundations are empty templates.
Once `vision.md` contains project-specific content, every subsequent spec reads
the populated foundations via the existing Step 2 logic and the cascade does
not fire again.

## Alternatives Considered

1. **Separate `kanon foundations init` command.** Rejected: separate commands
   don't get run. The natural moment for populating foundations is when the
   first spec needs them, not as a standalone ceremony that requires the human
   to remember a command exists.

2. **Better templates only.** Rejected: agents treat unfilled templates as
   "not my problem" — they read the template, find no project-specific content,
   and proceed without context. A behavioural trigger is needed to convert the
   empty-template signal into a conversation with the user.

3. **Hard gate requiring foundations before any spec.** Rejected: too
   prescriptive. The user must be able to skip the onboarding flow and write a
   spec without foundations. The cascade is a recommendation, not a gate — the
   user's choice is always respected.

4. **Keep ADR-0056 §4 as-is.** Rejected: the premise that agents don't author
   foundations is invalidated by the LLM-human collaboration model. The agent
   is not autonomously inventing project identity — it is asking the human for
   input and structuring the response. This is collaborative authoring, not
   autonomous authoring, and it falls outside the concern ADR-0056 addressed.

## Consequences

- **Positive.** The first spec in a depth-2 project is grounded in vision,
  principles, and (optionally) personas. Every subsequent spec benefits from
  populated foundations without any additional ceremony.

- **Positive.** Foundations get populated at the moment they are most needed
  and most likely to receive thoughtful input — when the human is already
  engaged in a conversation about what to build.

- **Negative.** The first spec takes approximately five extra minutes for the
  onboarding flow. This is a one-time cost that pays for itself on every
  subsequent spec, but it may surprise users who expect to jump straight into
  spec authoring.

- **Negative.** The cascade adds complexity to spec-before-design Step 2. The
  step now has conditional branching (template detection, user prompts, artifact
  population) in addition to its existing foundations-scanning logic.

## References

- [ADR-0056: SDD protocol gaps](0056-sdd-protocol-gaps.md)
- [ADR-0057: Move foundations to depth 2](0057-foundations-to-depth-2.md)
- [ADR-0058: Foundations coherence](0058-foundations-coherence.md)
