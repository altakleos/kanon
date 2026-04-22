# `agent-sdd`'s Instantiation of the SDD Stack

The development process in [`development-process.md`](development-process.md) describes Spec-Driven Development as a method: six generic layers (Foundations above Specs → Design → ADRs → Plans → Implementation → Verification). This document describes how `agent-sdd` specifically instantiates the bottom two layers — **Implementation** and **Verification** — and carries the load-bearing principles that make `agent-sdd`'s instantiation distinctive.

For the generic method, read `development-process.md`. For `agent-sdd`'s artifact choices, read this doc.

> **Status: bootstrap.** This file is intentionally minimal during Phase A of v0.1. It is fleshed out in Phase C (Implementation) and Phase D (Verification) as those layers land.

## Implementation Layer

Implementation in `agent-sdd` is realized across three artifact types:

| Artifact type | Location | Executor | Role |
|---|---|---|---|
| Python CLI | `src/agent_sdd/cli.py` | CPython via `agent-sdd` entry point | Mechanical work: scaffolding, atomic upgrade, tier migration, verify |
| Tier bundles | `src/agent_sdd/templates/tier-{0,1,2,3}/` | copied onto consumer repos by `init` | Prose-as-code SDD rules the consumer's LLM reads |
| Harness registry | `src/agent_sdd/templates/harnesses.yaml` | loader inside CLI | Per-harness shim paths + frontmatter |

## Verification Layer

Verification asserts both that the kit's own Python behaves correctly and that the tier bundles remain internally consistent:

| Artifact type | Location | Role |
|---|---|---|
| Pytest suite | `tests/` | CLI atomicity, tier-migration round-trips, template integrity |
| CI validators | `ci/check_foundations.py`, `ci/check_links.py`, `ci/check_package_contents.py`, `ci/check_template_consistency.py` | Cross-artifact invariants |
| Top-level runner | `agent-sdd verify` (CLI, shipped to consumers) | Entry point for consumer repos to verify their own SDD shape |

## Load-Bearing Principles

Live at [`docs/foundations/principles/`](foundations/principles/). Authored in Phase B.
