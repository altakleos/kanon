---
status: accepted
date: 2026-05-01
---
# Vision — What `kanon` Is, and What It Is Not

## What `kanon` Is

`kanon` is a **protocol substrate for prose-as-code engineering discipline in LLM-agent-driven repos**. It publishes a contract grammar and a replay engine; consumer repos and third-party publishers compose disciplines on top.

The substrate's bet, traced back to the project's first commits and ratified in [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md): **prose consumed by an LLM agent is the new source of truth.** A kanon project is one where the agent reads an `AGENTS.md`, follows the protocols routed from it, and produces evidence the kernel can replay — atomically, deterministically, and without intercepting the agent's behaviour.

Three properties define the substrate:

1. **Prose-as-code at every interface.** The substrate's communication medium with publishers, consumers, and agents is prose. Manifests are machine-parsed; protocols, contracts, and `AGENTS.md` prose are agent-read and human-read. Resolutions are downstream artifacts. See [`P-prose-is-code`](principles/P-prose-is-code.md).
2. **De-opinionated about disciplines, opinionated about substrate.** The kernel ships no defaults. `kanon init` enables nothing. Reference aspects (`kanon-sdd`, `kanon-testing`, `kanon-worktrees`, `kanon-release`, `kanon-security`, `kanon-deps`, `kanon-fidelity`) are de-installable demonstrations, not the product. The substrate IS opinionated about contract grammar, dialect semantics, capability symmetry, and the public principle set — that is what publishers rely on. See [`de-opinionation.md`](de-opinionation.md).
3. **Self-hosting as falsification.** This repo is a kanon project. It opts into reference aspects via the same publisher recipes any new project uses; the kernel grants no carve-outs. Self-hosting is the substrate's primary correctness probe under vision-led design — if `kanon verify .` cannot pass on this repo, the substrate is broken.

## Public Protocol Commitments

The substrate publishes six principles as stable protocol commitments. They are versioned with the dialect, citable by `acme-` publishers, and immutable post-acceptance under the same discipline that protects ADR bodies (per [ADR-0032](../decisions/0032-adr-immutability-gate.md), extended by [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md)).

| Principle | What the substrate commits to |
|---|---|
| [`P-prose-is-code`](principles/P-prose-is-code.md) | Prose consumed by an LLM agent is code; the substrate authors all communication-medium prose to that standard |
| [`P-protocol-not-product`](principles/P-protocol-not-product.md) | The substrate ships a contract grammar and replay engine; reference aspects are demonstrations, not the product |
| [`P-publisher-symmetry`](principles/P-publisher-symmetry.md) | Kit-shipped, project-defined, and third-party aspects resolve through the same code path; namespace asymmetries must be justified or refactored |
| [`P-runtime-non-interception`](principles/P-runtime-non-interception.md) | The substrate MUST NOT acquire a runtime component that intercepts or validates LLM-agent behaviour at runtime |
| [`P-specs-are-source`](principles/P-specs-are-source.md) | SDD artifacts are authoritative; code and resolutions are derived |
| [`P-verification-co-authored`](principles/P-verification-co-authored.md) | Tests, fixtures, and resolutions are co-authoritative with specs, not subordinate |

Two further principles remain kit-author-internal — they govern how kanon develops kanon and are not part of the published protocol:

- [`P-self-hosted-bootstrap`](principles/P-self-hosted-bootstrap.md) — the kit develops itself as a peer consumer
- [`P-cross-link-dont-duplicate`](principles/P-cross-link-dont-duplicate.md) — kit-author hygiene

One principle is retired: [`P-tiers-insulate`](principles/P-tiers-insulate.md) (superseded by ADR-0048; tier vocabulary is gone under protocol-shape).

## Substrate Guarantees

What `kanon-substrate` provides regardless of which aspects a consumer enables:

- **Atomic, crash-recoverable file writes** for kit-managed files, with `.pending` sentinel replay across interrupted operations.
- **Aspect registry composition** across kit-shipped (`kanon-`), consumer-defined (`project-`), and third-party (`acme-`) namespaces, with capability-keyed substitutability.
- **Dialect-versioned contract grammar.** Aspect manifests pin a `kanon-dialect:`; the substrate honours at least N-1 dialects with a documented deprecation horizon.
- **Resolution replay.** `.kanon/resolutions.yaml` is machine-only-owned, evidence-grounded, and SHA-pinned. CI replays cached resolutions mechanically; the resolver runs only on developer machines.
- **Verification orchestration.** `kanon verify` runs structural checks, project-validators, kit-validators, and (when an aspect declares the `behavioural-verification` capability) fidelity replay against committed `.dogfood.md` captures.
- **Cross-harness shims.** A consumer's choice of LLM harness — Claude Code, Cursor, Codex, Windsurf, Cline, Roo, JetBrains AI, Kiro, GitHub Copilot — does not change which discipline applies. Shims point at `AGENTS.md`; new harness support is a data-file edit.
- **Self-hosting falsifiability.** The kanon repo opts into reference aspects with no kernel-side privilege. Substrate behaviours that fail self-host are P0/P1 halts.

## What `kanon` Is Not

`kanon` explicitly does not:

- **Generate code from specs.** There is no spec-to-code compiler. Agents read prose and write code; the substrate does not close that loop.
- **Intercept, block, or validate LLM-agent actions at runtime.** No daemon, no hook, no session supervisor. Prose gates are enforced by agent compliance, observable from transcripts. (Promoted from a non-goal to a public principle: [`P-runtime-non-interception`](principles/P-runtime-non-interception.md).) *Scope carve-out:* reference automation snippets for cryptographic, irreversible, or stateful operations the *consumer* executes (release-pipeline GitHub Actions templates, pre-commit configs, Makefile targets) are in scope for aspects that package them. See [ADR-0013](../decisions/0013-vision-amendment-reference-automation.md).
- **Privilege the `kanon-` namespace in resolver paths.** Reference aspects are de-installable; their CLI handling is symmetric with `acme-` and `project-` aspects.
- **Ship default disciplines.** `kanon init` enables nothing. Recipes (publisher-shipped target-tree YAML) are how a consumer adopts a starter set; the substrate has no opinion about which recipe.
- **Replace product-management tooling.** Plans, ADRs, and specs are engineering artifacts. Jira, Linear, and product-roadmap tools live outside the substrate.
- **Define a machine-parseable schema for `AGENTS.md` prose or protocol prose bodies.** Manifests are machine-parsed; the substrate's human/agent prose surface is read, not validated against a schema. (`realization-shape:` schemas exist at the per-contract artifact level — that does not contradict this commitment.)
- **Promise correctness or quality endorsement on `kanon verify` exit-0.** Exit-0 means conformance to enabled aspects only — the consumer's chosen disciplines, whose authority is the publisher's responsibility (per [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) and a forthcoming verification-contract INV).

## Why prose-as-code is the bet

In an AI-coded future where humans read specs far more than they read generated code, the SDD artifacts become the authoritative source. A spec is not documentation of code; the code is a downstream artifact of the spec. This stance was captured at the project's start as [`P-specs-are-source`](principles/P-specs-are-source.md).

The protocol substrate extends the bet one layer down: not only are specs authoritative for product code, but **prose contracts are authoritative for runtime bindings too.** A `.kanon/resolutions.yaml` is not a configuration the user maintains; it is a derived artifact a publisher's prose contract produced when an agent resolved it against this specific repo. The kernel replays the artifact mechanically; the prose contract is the source.

If the bet is right — if frontier LLMs can reliably resolve prose contracts into evidence-grounded runtime bindings — then a kanon project is one where the engineering rules live in prose any contributor (human or agent) can read. If the bet is wrong, the substrate is reducible to "a fancy Makefile with version-pinning." The substrate commits to the bet without hedging it.

## Self-hosting under vision-led design

This repo has zero current external consumers. That is intentional, not a deficit. Vision-led architecture commits to a shape before demand exists, in exchange for the optionality of designing without legacy.

What this elevates: **self-hosting is the only validation surface available.** The kanon repo is not a user sample; it is the entire empirical universe. Every Phase-0 decision must survive the question: *does this still allow the repo to pass `kanon verify .`?* Every claim about the substrate's behaviour must be testable against this repo's own state. [`P-self-hosted-bootstrap`](principles/P-self-hosted-bootstrap.md) codifies the discipline.

What this constrains: substrate features that cannot be exercised by the kanon repo's own state are speculative. The substrate refuses to ship them until self-host can falsify them.

## Success Criteria

### v0.1 (achieved)

- The repo passed `kanon verify .` as a tier-3 consumer of the kit-shape prototype.
- `kanon init` produced a valid scaffold for tier-0 through tier-3.
- PyPI release cut without manual intervention beyond the trusted-publishing gate.

### v0.2 (achieved)

- Aspects subsumed tiers; `kanon-sdd` was the first aspect; capability registry shipped.
- The kit ran the full set of seven aspects (`kanon-sdd:3`, `kanon-worktrees:2`, `kanon-release:2`, `kanon-testing:3`, `kanon-security:2`, `kanon-deps:2`, `kanon-fidelity:1`) under self-host.

### v0.3 (achieved through v0.3.0a9)

- Aspect decoupling, project-aspect namespacing, in-process validators, fidelity replay, ADR immutability gate, three-source registry semantics.

### v0.4 (in flight — protocol substrate transition)

- `kanon-substrate` ships as a separately-installable distribution; the kernel scaffolds nothing on its own behalf.
- `kanon-reference` ships the seven reference aspects as data; `kanon-kit` meta-alias preserves the convenience-install path.
- `kanon init` produces a bare scaffold with no aspects auto-enabled.
- The repo passes `kanon verify .` opting into reference aspects via a publisher recipe, with no kernel-side privilege.
- Public-tier principles are versioned with the dialect; `acme-` publishers can cite them.
- Phase 0 ADRs (0039–0044, plus 0040.5 kernel/reference runtime interface) ratify the implementation.

### v1.0 (vision)

- An `acme-X` author can read the dialect spec, ship a contract bundle, and have it resolve through the substrate identically to a `kanon-` reference aspect.
- The substrate's daily-alpha kernel cadence and quarterly dialect cadence operate cleanly across at least one dialect supersession.
- The repo's self-host falsification probes (substrate-determinism, self-host-from-clone, resolution-determinism) have run continuously without firing P0/P1 halts.

## Amendment Trail

| Date | ADR | What changed |
|---|---|---|
| 2026-04-23 | [ADR-0013](../decisions/0013-vision-amendment-reference-automation.md) | Non-Goal #2 scope carve-out for reference automation snippets |
| 2026-04-23 | [ADR-0015](../decisions/0015-vision-amendment-aspect-identity.md) | §What kanon Is, §Current Promises, §Success Criteria updated to reflect aspect model |
| 2026-05-01 | [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) | Full vision rewrite: kanon committed as a protocol substrate; kit-shape retired; six public-tier principles ratified; tier vocabulary retired (see [`de-opinionation.md`](de-opinionation.md)) |

## Historical Note

The pre-protocol-commitment vision described kanon as *"a portable, self-hosting kit that packages development disciplines"* — the kit-shape framing that v0.4 supersedes. The previous vision body is preserved verbatim at commit `7b7d8d4` ("docs: vision + README sweep against current shipped state"). The body is preserved per the immutability discipline applied to vision documents from this PR onward.

The kit-shape vision was correct for what it described — a transitional packaging that proved out the aspect model, the cross-harness shim registry, and the self-hosting property. It was incorrect as a destination. The protocol substrate is what the project always was reaching toward; the kit was the path, not the place.

For archaeological context, see [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md)'s Context section, which traces the three forces that made the protocol commitment unavoidable.
