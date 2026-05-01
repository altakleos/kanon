---
id: P-protocol-not-product
kind: technical
tier: public-protocol
status: accepted
date: 2026-05-01
---
# kanon ships a protocol, not a discipline product

## Statement

`kanon-substrate` ships a contract grammar and a replay engine. Reference aspects (`kanon-sdd`, `kanon-testing`, `kanon-worktrees`, `kanon-release`, `kanon-security`, `kanon-deps`, `kanon-fidelity`) are demonstrations of how to author against the grammar — they are not the substrate's product. The kernel grants no privilege, in code or in CLI, to aspects published under the `kanon-` namespace.

## Rationale

A kit privileges its own opinions; a substrate publishes a grammar over which any opinions compose. The two are different deliverables. The kit shape was a transitional artifact (per [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md) and [`de-opinionation.md`](../de-opinionation.md)); the substrate is the destination. This principle codifies the kernel-side discipline that keeps them distinct.

Without this principle, every minor convenience the kernel adds for `kanon-` aspects ("auto-detect testing config from pyproject.toml because that's what the reference testing aspect expects") becomes a privilege a third-party publisher cannot replicate. The capability registry's substitutability promise (per [ADR-0026](../../decisions/0026-aspect-provides-and-generalised-requires.md)) becomes honour-system-only. The protocol identity erodes through small concessions.

## Implications

- **No `defaults:` block.** The top-level manifest does not enumerate "the recommended set." Recipes (publisher-shipped target-tree YAML) are how a starter set propagates; the substrate has no opinion about which recipe.
- **No `kanon-`-namespace fast paths in resolver code.** Code paths that distinguish by namespace must be justified or refactored. CI checks (kit-author internal) verify this empirically.
- **No bare-name CLI sugar that resolves to `kanon-` exclusively.** Bare-name sugar from the kit-shape era is deprecated; future invocations require explicit publisher prefixes.
- **No kit-global `files:` field.** Aspects own all the files they scaffold; the substrate scaffolds nothing on its own behalf.
- **Reference aspects ship in a separate distribution.** `kanon-substrate` (kernel) and `kanon-reference` (the seven `kanon-` aspects as data) are independently installable; `kanon-kit` is a meta-alias for the convenience-install path. A consumer running only `kanon-substrate` gets a working substrate with zero opinions about discipline.
- **The substrate's test suite must pass with `kanon-reference` uninstalled.** Self-host is achieved by *the kanon repo opting into a publisher recipe*, not by the kernel auto-knowing about reference aspects.
- **Documentation language matches.** The substrate's prose calls reference aspects "demonstrations" and "reference implementations," never "the kit's aspects" or "the curated set."

## Exceptions / Tensions

- **Self-hosting demands demonstration adequacy.** The kanon repo opts into reference aspects to prove the substrate works end-to-end. This is not a privilege; it is a peer-consumer choice the substrate would honour identically for any other publisher. The repo's `.kanon/config.yaml` carries `provenance:` showing the recipe and publisher (`kanon-reference`), making the demonstration explicit.
- **`kanon-substrate` itself is shipped by the same author who ships `kanon-reference`.** That co-authorship is a fact about who maintains the project, not a privilege the substrate grants. A future split (separate maintainers, separate repos) would reduce the appearance of privilege without changing the substrate's behaviour.

## Source

Lead's framing during the protocol-commitment ratification across rounds 4–5 of panel review. Codified as a public-tier principle by [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md) at the moment the kit shape was retired and the substrate shape ratified. The principle is part of the substrate's published protocol commitments; it is versioned with the dialect and immutable post-acceptance.
