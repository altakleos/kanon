---
status: accepted
date: 2026-04-23
realizes:
  - P-prose-is-code
  - P-tiers-insulate
stressed_by:
  - solo-with-agents
  - platform-team
fixtures:
  - tests/test_cli.py
  - tests/test_kit_integrity.py
invariant_coverage:
  INV-worktrees-scaffolding-location:
    - tests/test_cli.py::test_init_with_worktrees_depth_1
    - tests/test_cli.py::test_init_with_worktrees_depth_2
  INV-worktrees-depth-range:
    - tests/test_kit_integrity.py::test_worktrees_manifest_has_expected_depths
  INV-worktrees-protocol-shaped:
    - tests/test_cli.py::test_aspect_add
  INV-worktrees-reference-automation-snippets:
    - tests/test_cli.py::test_init_with_worktrees_depth_2
  INV-worktrees-non-destructive-teardown:
    - tests/test_cli.py::test_aspect_remove_leaves_files
  INV-worktrees-cross-aspect-dependency:
    - tests/test_cli.py::test_aspect_add_requires_unmet
    - tests/test_cli.py::test_aspect_add_requires_met
  INV-worktrees-namespaced-agents-md-section:
    - tests/test_kit_integrity.py::test_worktrees_agents_md_exists_per_depth
---
# Spec: Worktrees — isolated parallel execution via git worktrees

## Intent

Package the discipline of using git worktrees to isolate concurrent work streams in the same repo. When a solo developer runs multiple agents — or works alongside an agent — each work stream should operate in its own worktree to prevent filesystem collisions. The `worktrees` aspect ships prose procedures (setup, teardown, integration) and, at higher depth, reference helper scripts so agents follow a predictable lifecycle without the human micromanaging the topology.

The aspect's trigger is unconditional for file-modifying operations. An agent cannot detect whether other agents are running, and even a single-file edit can collide with another agent's work on the same file. When the worktrees aspect is enabled, every file-modifying operation uses a worktree. Read-only operations do not require isolation.

## Invariants

<!-- INV-worktrees-scaffolding-location -->
1. **Scaffolding location.** Each concurrent agent operates inside `.worktrees/<slug>/`, where `<slug>` is a short identifier derived from the plan or task (naming convention defined in the lifecycle protocol, INV-worktrees-protocol-shaped). The kit does not create `.worktrees/`; it reserves the path, documents the convention, and (at depth-2) ships setup/teardown helpers the consumer invokes.

<!-- INV-worktrees-depth-range -->
2. **Depth range is 0–2.** The `worktrees` aspect declares `depth-range: [0, 2]`.
   - **Depth 0** — opt-out. Aspect enabled in config but no files scaffolded.
   - **Depth 1** — prose guidance. Protocol file and AGENTS.md section are scaffolded. Agents understand worktree hygiene and apply judgment based on change scope. Agents use `git worktree add/remove` directly.
   - **Depth 2** — prose guidance plus automation. Shell helper scripts are scaffolded alongside the protocol and AGENTS.md section. Agents use the project's standardized scripts for consistent worktree lifecycle management.

<!-- INV-worktrees-protocol-shaped -->
3. **Protocol-shaped.** The aspect ships one protocol at `.kanon/protocols/worktrees/worktree-lifecycle.md` (depth ≥ 1) covering: branch-naming convention, worktree creation steps, integration cadence (how often to rebase/merge main), teardown idempotence, and stale-worktree detection. Frontmatter `invoke-when` names **any file-modifying operation** as the trigger, with `git worktree list` as a secondary heuristic for detecting concurrent work.

<!-- INV-worktrees-reference-automation-snippets -->
4. **Reference automation snippets** (per ADR-0013, depth-2 only). The aspect scaffolds host-neutral shell helpers under the consumer's tree: `scripts/worktree-setup.sh`, `scripts/worktree-teardown.sh`, `scripts/worktree-status.sh`. These are copy-in templates the consumer invokes directly — not agent-behavior hooks, and not kit-owned once scaffolded (byte-equality not enforced after init; consumers adapt them).

<!-- INV-worktrees-non-destructive-teardown -->
5. **Non-destructive teardown.** A worktree with uncommitted changes is reported and preserved; the helper (or raw `git worktree remove`) never forcibly removes in-flight work. The prose protocol describes how the operating agent should resolve (commit, stash, or escalate to the human).

<!-- INV-worktrees-cross-aspect-dependency -->
6. **Cross-aspect dependency.** `worktrees` requires `sdd >= 1` in the manifest. The SDD tier-1 plan-before-build gate is a prerequisite: worktree-per-plan correspondence depends on plans existing as first-class artifacts.

<!-- INV-worktrees-namespaced-agents-md-section -->
7. **Namespaced AGENTS.md section.** At depth ≥ 1, the aspect contributes one marker-delimited section `worktrees/branch-hygiene` to AGENTS.md — a short prose summary of the branch-naming convention, the unconditional file-modification trigger for worktree creation, and integration cadence, so an operating agent sees the rules on the boot chain without having to invoke the protocol file for routine decisions.

## Rationale

**Why always-isolate, not concurrency detection.** An agent has no reliable way to detect whether other agents are running. Lock files are fragile (stale locks after crashes, race conditions, invisible across machines). Since detection is impossible and even single-file edits can collide, the protocol requires isolation for all file-modifying operations. The cost of an unnecessary worktree (~2 seconds) is negligible; the cost of a collision (broken state, lost work) is not. As a lightweight heuristic, agents check `git worktree list` — existing worktrees signal that parallel work is likely.

**Why depth 0–2, not binary.** The aspect has two separable layers of value: (a) the knowledge layer — protocol and AGENTS.md section that teach agents *when* and *why* to use worktrees, and (b) the automation layer — shell helpers that standardize the *how*. These layers are independently useful. A depth-1 user gets agents that make good worktree decisions using `git worktree add/remove` directly. A depth-2 user additionally gets consistent, project-specific helper scripts. This mirrors SDD's depth progression: depth-1 gives process (plan-before-build); depth-2 gives more structure (specs).

**Why split from `multi-agent-coordination`.** The deferred `multi-agent-coordination` spec bundles reservation ledgers, plan-SHA pins, decision handshakes, and worktree isolation under a single banner. Those are separable primitives with very different landing costs: worktree isolation is cheap prose + ~100 LOC of shell; the others require real state machinery. Carving worktrees into its own aspect lets it ship first, validated against the agent-first persona, without blocking on the rest.

**Why an aspect, not a CLI subcommand.** Worktree lifecycle is mostly judgment-shaped: when to cut a new worktree (plan-scoped? task-scoped?), when to integrate with main, when to tear down a stale one. Those are prose decisions an LLM agent makes, not mechanical operations a Python CLI should orchestrate. The deterministic parts (`git worktree add/remove`) are thin shell wrappers the consumer invokes explicitly.

**Why ADR-0013's snippet carve-out is load-bearing here.** A pure-prose worktree aspect would force every consumer to re-derive shell commands from protocol text on every use — exactly the boilerplate-reinvention failure mode ADR-0013 was written to avoid. Shipping `worktree-*.sh` as copy-in reference templates keeps the kit's value proposition (scaffolding) intact without violating the no-runtime-agent-hooks promise.

**Why tier-1 and not tier-2.** Solo-with-agents persona says agent-agent collision is a day-1 concern. Gating worktrees at tier-2 would force users into tier-up early for a concern their repos face on commit 1. Making it a tier-1 aspect (requires `sdd >= 1`) matches the real adoption curve.

## Out of Scope

- **Non-git worktree systems** (jujutsu, pijul, mercurial). Git is the assumed VCS. Hosts with jj/pijul can author a sibling aspect.
- **Automated conflict resolution on merge.** The protocol documents manual resolution patterns; no heuristic-based auto-merge.
- **Cross-repo coordination.** Single-repo-with-N-agents is the domain; multi-repo agent orchestration is out-of-scope and may live elsewhere.
- **Coordination beyond filesystem isolation.** Plan-SHA pinning, reservation ledgers, decision handshakes — those remain under the `multi-agent-coordination` deferred spec and may land as separate aspects.
- **Host-specific integrations** beyond generic shell helpers. GitHub PR-close webhook cleanup, GitLab Duo integration, etc. are consumer extensions, not kit-owned content.
- **Worktree-per-agent automation** (an orchestrator that spawns agents into worktrees). The kit describes the lifecycle; spawning is the user's harness choice.

## Decisions

See:
- **ADR-0014** — worktrees aspect (scaffolding shape, depth progression, lifecycle protocol, reference helper scripts, tier-1 placement).

ADR number is provisional until authored alongside this spec's promotion from `draft` to `accepted`.
