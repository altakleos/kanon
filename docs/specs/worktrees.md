---
status: draft
date: 2026-04-23
realizes:
  - P-prose-is-code
  - P-tiers-insulate
stressed_by:
  - solo-with-agents
  - platform-team
fixtures_deferred: "Worktree aspect tests land with the v0.3 worktrees-aspect implementation plan (plan file TBD)."
---
# Spec: Worktrees — isolated parallel execution for concurrent agents

## Intent

Package the discipline of using git worktrees to isolate concurrent LLM agents operating on the same repo. When a solo developer runs two or more agents in parallel — the default configuration per the `solo-with-agents` persona — agents must not step on each other in a shared working tree. The `worktrees` aspect ships prose procedures (setup, teardown, integration) plus reference helper scripts so agents follow a predictable lifecycle without the human micromanaging the topology.

The aspect's primary trigger is agent-first: the moment a second concurrent agent will edit the same repo, not the day a second human joins. This places worktrees early in the adoption sequence (tier-1 for agent-driven projects) rather than "eventually" under the broader multi-agent-coordination deferred spec.

## Invariants

1. **Scaffolding location.** Each concurrent agent operates inside `.worktrees/<slug>/`, where `<slug>` is a short identifier derived from the plan or task. The kit does not create `.worktrees/`; it reserves the path, documents the convention, and ships setup/teardown helpers the consumer invokes.

2. **Depth range is binary.** `worktrees` aspect declares `depth-range: [0, 1]`. Depth-0 is opt-out (aspect enabled in config but no files scaffolded). Depth-1 is the shipping form — protocol plus helper scripts present.

3. **Protocol-shaped.** The aspect ships one protocol at `.kanon/protocols/worktrees/worktree-lifecycle.md` covering: branch-naming convention, worktree creation steps, integration cadence (how often to rebase/merge main), teardown idempotence, and stale-worktree detection. Frontmatter `invoke-when` names agent-agent collision as the primary trigger, consistent with the solo-with-agents persona.

4. **Reference automation snippets** (per ADR-0013). The aspect scaffolds host-neutral shell helpers under the consumer's tree: `scripts/worktree-setup.sh`, `scripts/worktree-teardown.sh`, `scripts/worktree-status.sh`. These are copy-in templates the consumer invokes directly — not agent-behavior hooks, and not kit-owned once scaffolded (byte-equality not enforced after init; consumers adapt them).

5. **Non-destructive teardown.** A worktree with uncommitted changes is reported and preserved; the helper never forcibly removes in-flight work. The prose protocol describes how the operating agent should resolve (commit, stash, or escalate to the human).

6. **Cross-aspect dependency.** `worktrees` requires `sdd >= 1` in the manifest. The SDD tier-1 plan-before-build gate is a prerequisite: worktree-per-plan correspondence depends on plans existing as first-class artifacts.

7. **Namespaced AGENTS.md section.** At depth-1, the aspect contributes one marker-delimited section `worktrees/branch-hygiene` to AGENTS.md — a short prose summary of the branch-naming convention and integration cadence, so an operating agent sees the rule on the boot chain without having to invoke the protocol file for routine edits.

## Rationale

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
- **ADR-0014** — worktrees aspect (scaffolding shape, lifecycle protocol, reference helper scripts, tier-1 placement).

ADR number is provisional until authored alongside this spec's promotion from `draft` to `accepted`.
