---
id: P-self-hosted-bootstrap
kind: technical
tier: kit-author-internal
status: accepted
date: 2026-04-22
---
# The kit develops itself as a peer consumer

## Statement

`kanon` is developed using `kanon`. The kanon repo is a peer consumer of the substrate: it opts into reference aspects via the same publisher recipes any new project uses, with no kernel-side carve-outs and no privileged paths. Self-hosting is the substrate's primary correctness probe under vision-led design — if `kanon verify .` cannot pass on this repo, the substrate is broken.

## Rationale

Self-hosting is the cheapest test of fitness. Under demand-led design, self-hosting is dogfooding (the team feels the user's pain). Under vision-led design with no current external consumers, self-hosting is categorically different: it is the only falsification surface available. The kanon repo is not a user sample; it is the entire empirical universe.

If the substrate's grammar feels onerous when applied to the kanon repo's own evolution, it will feel worse when adopted by external projects. If the substrate's reference aspects drift from the substrate's own grammar, downstream consumers will adopt the references and produce projects that don't pass `kanon verify`. Both failure modes are obvious only when self-hosting is mandatory.

## Implications

- **The kanon repo's `.kanon/config.yaml` opts into reference aspects via a publisher recipe** (`reference-default` shipped by `kanon-reference`), with `provenance:` recording the recipe and publisher. The opt-in is identical to what any external consumer would author. The substrate does not know the kanon repo is special.
- **No kernel-side carve-outs for the kanon repo.** Code paths that would have privileged the repo (kit-global `files:`, `defaults:`, bare-name namespace sugar at runtime) are removed under the protocol-substrate commitment.
- **Self-hosting falsification probes are the substrate's primary correctness signal.** Their detail (P1 self-host-from-clone, P2 substrate-determinism, P0 resolution-determinism) lives in [`de-opinionation.md` § Self-hosting as falsification](../de-opinionation.md). The kanon repo's state is what those probes fire against.
- **When the substrate ships a new capability, the kanon repo must adopt it before the release is cut.** "We built it but we don't use it" is a red flag.
- **Substrate features that cannot be exercised by the kanon repo's own state are speculative.** The substrate refuses to ship them until self-host can falsify them.
- **The self-hosting paradox is preserved**: the kit requires itself to develop itself, but commit 1 cannot follow a method that doesn't yet exist. ADR-0002's three-commit bootstrap remains the resolution.

## Exceptions / Tensions

- Some kit-author files (the substrate's Python source, pyproject metadata, the reference-aspect bundle's manifests) have no analogue in a peer consumer's tree. Those are kit-author-internal artifacts; they don't participate in the consumer-facing self-hosting check. The kanon repo's *consumer-facing* state (`.kanon/config.yaml`, `AGENTS.md`, scaffolded protocols) is what `kanon verify` exercises against, and that state is peer-consumer-symmetric.
- Major substrate refactors may temporarily break self-hosting between commits. Those commits should be bounded and named, analogous to the bootstrap phase.
- The kit-author also publishes `kanon-reference`. That co-authorship is a fact about who maintains the project, not a privilege the substrate grants. A future split (separate maintainers, separate repos) would reduce the appearance of privilege without changing the substrate's behaviour.

## Source

User requirement during v0.1 planning ("the kanon should be developed using kanon!"). Formalised as a principle because it shapes many downstream decisions (the check_kit_consistency validator, the tier-3-is-the-repo design, the three-commit bootstrap ADR).

## Tier

This principle is **kit-author-internal** (per [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md)). It governs how kanon develops kanon; it is not part of the substrate's published protocol. Publishers do not need to honour it; the substrate does not enforce it on consumer repos. Body amendments are kit-author concerns and do not require dialect supersession.

## Historical Note

Pre-amendment body asserted that "the repo runs `sdd` at depth 3 and `worktrees` at depth 2" as a kit-special configuration with byte-equality between the repo's `docs/` tree and the kit-shipped templates. That kit-shape framing is preserved at commit `ded4e77`. The amendment that landed under [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md) replaced the kit-special framing with peer-consumer framing: the kanon repo opts in via a publisher recipe; the substrate has no privileged path; self-hosting becomes the substrate's primary falsification probe rather than a kit-shape demonstration.
