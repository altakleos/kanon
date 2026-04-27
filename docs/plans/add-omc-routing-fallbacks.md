---
status: done
---

# Plan: Add Missing OMC Agent Routing Fallbacks

## Problem

The Agent Routing table in AGENTS.md says "fall back to the built-in equivalent shown in parentheses" but 11 of 15 mappings have no parenthesized fallback. When OMC is not installed, agents have no guidance for these task shapes.

## Scope

Single-section edit to the project-specific preamble in AGENTS.md (lines 56–78). No kit template changes — this section is not kit-scaffolded.

## Gap 5 (boot chain inconsistency) — No Action

The `kanon-sdd/body` boot chain omits `docs/kanon-implementation.md` (present in the preamble). This is by design: the body section is the generic kit template shipped to all consumers; `kanon-implementation.md` is project-specific. The preamble augments the generic boot chain. No fix needed.

## Changes

Add `(else ...)` fallback directives to all 11 mappings that currently lack them:

| Task Shape | OMC Agent | Proposed Fallback |
|------------|-----------|-------------------|
| Focused implementation | `executor` | (else proceed directly) |
| Independent second opinion | `critic` | (else request review from a second agent pass) |
| Root-cause debugging | `debugger` + `tracer` | (else debug directly with systematic diagnosis) |
| Test strategy / TDD | `test-engineer` | (else follow `test-discipline` and `ac-first-tdd` protocols) |
| Security scan | `security-reviewer` | (else follow `secure-defaults` protocol + run `ci/check_security_patterns.py`) |
| Verifying "is this done?" | `verifier` | (else follow `completion-checklist` protocol) |
| External docs / API lookup | `document-specialist` | (else search documentation directly) |
| Git operations | `git-master` | (else use git CLI directly) |
| Technical writing | `writer` | (else write directly) |
| UI/UX work | `designer` | (else proceed directly) |
| Code simplification | `code-simplifier` | (else refactor directly) |

## Acceptance Criteria

- [x] All 15 routing entries have a parenthesized fallback or explicit directive
- [x] Fallbacks reference existing protocols where applicable (test-discipline, secure-defaults, completion-checklist)
- [x] The intro paragraph's promise ("fall back to the built-in equivalent shown in parentheses") is satisfied by every entry

## Out of Scope

- Changing the kit template for the `kanon-sdd/body` boot chain (gap 5 — by design)
- Adding new built-in agent definitions
- Changing OMC agent behavior
