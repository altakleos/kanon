---
status: accepted
date: 2026-04-28
depth-min: 1
invoke-when: Committing fidelity captures, editing protocol prose, or working with fidelity fixtures
---
# Protocol: Fidelity Discipline

## Purpose

Ensure behavioural-conformance fixtures stay in sync with protocol prose and agent behaviour.

## Steps

### 1. Commit fixtures before tagging

A release tag stamps the protocol prose at a SHA; the paired dogfood capture must reflect agent behaviour at that SHA. Tagging with stale captures ships a hidden contract violation.

### 2. Recapture when the protocol changes

If you edit a protocol's prose, the previous dogfood capture no longer reflects what the agent should now do. Recapture as part of the same change; commit the new dogfood alongside the prose edit.

### 3. Never weaken an assertion to make a fixture pass

A failing fidelity assertion means the agent did the wrong thing. Fix the agent's prompt, fix the protocol prose, or accept that the rule does not actually hold — and remove the assertion deliberately, with a note. Silently relaxing the regex is the same anti-pattern as weakening a unit-test assertion.

### 4. Interpret results

- **Failures are errors** — a capture that fails assertions is a real defect. `kanon verify` errors and CI breaks.
- **Missing dogfood is a warning** — a fixture without its paired capture is in-flight work.

## Exit criteria

- Every protocol with a fidelity fixture has a paired `.dogfood.md` capture.
- No assertions were weakened to make a fixture pass.
- `kanon verify .` shows no fidelity errors.
