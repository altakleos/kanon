---
status: accepted
date: 2026-04-24
depth-min: 1
invoke-when: An agent discovers during implementation that the current task requires changes not described in the approved plan
---
# Protocol: Scope-check

## Purpose

Prevent silent scope creep. When an agent discovers work outside the approved plan, it must stop and classify the deviation before proceeding.

## Steps

### 1. Stop implementation

Do not make the unplanned change yet.

### 2. Identify the deviation

What file, function, or dependency is needed that the plan doesn't mention?

### 3. Classify

- **(a) Plan omission** — the plan should have included this. Propose a plan amendment, continue after user approval.
- **(b) Genuine new scope** — this is a separate concern. Propose a separate plan. Do not bundle it.
- **(c) Prerequisite blocker** — the planned work cannot proceed without this. Describe the blocker, ask how to proceed.

### 4. Act on classification

For **(a)**: amend the plan inline (add the task/file), note the amendment, continue.

For **(b)** and **(c)**: do NOT proceed with the unplanned work. Present the finding to the user.

### 5. Maintain the contract

Never silently expand scope — the plan is the contract.

## Exit criteria

The deviation is classified, the user has acknowledged it, and the plan reflects reality.

## Anti-patterns

- **"I'll just fix this while I'm here."** That's scope creep.
- **Amending the plan retroactively after already making the change.** The amendment must come before the change.
- **Classifying everything as (a) to avoid stopping.** If in doubt, it's (b).
