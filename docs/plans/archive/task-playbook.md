---
status: done
design: "No design needed — project-specific AGENTS.md prose edit"
touches:
  - AGENTS.md
---

# Plan: Restructure agent routing as a capability-neutral Task Playbook

## Motivation

The "Agent Routing" section in AGENTS.md is organized around OMC
agent names with parenthetical fallbacks. This makes the section
irrelevant for the 8 non-OMC harnesses. More fundamentally, it
couples the guidance to one harness's agent taxonomy instead of
describing what each work phase *needs*.

## Change

Replace the "Agent Routing (when oh-my-claudecode is available)"
section (lines 56–78) with a "Task Playbook" that describes
capability profiles per work phase. The harness matches profiles
to whatever is locally available — agents, skills, modes, or
built-in features.

### New section structure

1. **Intro paragraph** — match your activity to a phase; prefer a
   specialist capability matching the listed profile if available;
   otherwise handle directly using the referenced protocol.

2. **Phase table** — columns: Phase, Capability profile, Protocol /
   guidance. No harness-specific names. Profiles use generic terms
   (planner, architect, debugger, reviewer, etc.).

### Phase table content

| Phase | Capability profile | Protocol / guidance |
|-------|-------------------|---------------------|
| Planning | Planner, interviewer, deep-reasoning | § Plan Before Build |
| Architecture | Architect, design critic | Review against ADRs + design docs |
| Implementation | Executor, code generator | Follow approved plan, verify each AC |
| Exploration | Explorer, codebase search | Pattern discovery, file navigation |
| Code review | Reviewer, code critic | Severity ratings; check spec/plan drift |
| Debugging | Debugger, tracer, root-cause analysis | `error-diagnosis` protocol |
| Testing | Test engineer, TDD specialist | `test-discipline` + `ac-first-tdd` |
| Security | Security reviewer, vulnerability scanner | `secure-defaults` + CI scanner |
| Completion check | Verifier, checklist runner | `completion-checklist` protocol |
| Documentation | Writer, doc specialist | Match project tone |
| Git operations | Git specialist, rebase/commit tooling | Use git CLI |
| Release | — | `release-checklist` protocol |

## Files changed

| File | Change |
|------|--------|
| `AGENTS.md` | Replace lines 56–78 (Agent Routing section) |

No kit files, no protocol files, no code. This is project-specific
preamble prose.

## Acceptance criteria

1. The section is organized by work phase with capability profiles,
   not by harness-specific agent names.
2. Every phase entry has self-contained guidance that works regardless
   of which harness or agent system is available.
3. No OMC, Claude Code, Cursor, Kiro, or other harness names appear
   in the phase table.
4. `kanon verify .` passes.
5. No kit-managed marker sections are affected.
