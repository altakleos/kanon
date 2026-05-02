# Specs

Product intent — WHAT the project does from the user's perspective.

## What is a spec

A spec describes WHAT the project does from a product perspective. It is implementation-agnostic — a spec makes sense even if the entire technical architecture changed. Specs capture product intent before any design work begins.

A spec answers: What problem does this solve? What properties must the output have? What invariants must always hold? What is explicitly out of scope?

A spec-level statement describes a user-facing property or invariant without naming any mechanism, data format, or executor. If a sentence mentions which component stores something, which language implements it, or which process runs it, it has crossed into design or implementation territory. See the project's instantiation doc for concrete examples of spec-level invariants.

Specs come BEFORE ADRs. They define the intent that ADRs record decisions about. A feature might reference an existing spec (most new work serves an existing product guarantee) or require a new one (when the project takes on a genuinely new capability).

Specs are named descriptively, not numbered chronologically, because they represent product capabilities with no meaningful ordering — unlike ADRs, where chronological sequence is load-bearing (later decisions build on earlier ones).

Specs use a lightweight format: YAML frontmatter (`status`, `date`, plus optional foundation backreferences `serves`, `realizes`, `stressed_by`, and fixture fields `fixtures`, `fixtures_deferred`), then sections for Intent, Invariants, Rationale, Out of Scope, and Decisions.

### Fixture-naming convention

Any spec claiming to `realize:` a principle or `serve:` a foundation must name at least one concrete fixture that proves it — a test file, a transcript fixture, or an E2E test. If no fixture yet exists, use `fixtures_deferred:` with a reason.

## Index

*(empty — add specs as you define user-visible capabilities)*

## Template

See [`_template.md`](_template.md).
