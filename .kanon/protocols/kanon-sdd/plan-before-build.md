---
status: accepted
date: 2026-04-28
depth-min: 1
invoke-when: A non-trivial source change is about to begin, or the agent is unsure whether a change is trivial
gate: hard
label: Plan Before Build
summary: non-trivial changes require an approved plan before source edits.
audit: 'Plan at `<path>` has been approved.'
priority: 100
question: 'If non-trivial: does a plan exist at `docs/plans/<slug>.md` and has the user approved it? If not — **stop and write the plan.**'
---
# Protocol: Plan Before Build

## Purpose

Ensure every non-trivial change has an approved plan before source files are modified. The plan is the contract between the agent and the user.

## Steps

### 1. Classify the change

A change is **non-trivial** (plan first) if any of these apply:

- touches more than one function, file, or public symbol
- adds, removes, or pins a dependency
- changes a CLI flag, public schema, JSON/YAML shape, or protocol prose
- warrants a CHANGELOG entry
- multiple agents will collaborate on it
- you are unsure which side of this line it falls on

A change is **trivial** (act directly, no plan needed) only if:

- typo in a comment or string literal
- fixing a single failing assertion with an unambiguous fix
- renaming a local variable
- deleting code the caller can prove is unreachable

### 2. Write the plan

Your **first output** is a plan file under `docs/plans/<slug>.md`, followed by explicit user approval. You may not call Edit, Write, or mutating Bash on source files before the user has approved the plan.

### 3. State the audit sentence

**Before your first source-modifying tool call, state in one sentence:** "Plan at `<path>` has been approved." If you cannot truthfully emit that sentence, stop and plan. This sentence is the audit trail — its absence in a transcript is how violations get caught.

## Anti-patterns

- **Retroactive plans** are evidence of past violation, not a norm. Do not add to that pile.

## Exit criteria

- A plan file exists at `docs/plans/<slug>.md`.
- The user has explicitly approved the plan.
- The audit sentence has been stated before the first source-modifying tool call.
