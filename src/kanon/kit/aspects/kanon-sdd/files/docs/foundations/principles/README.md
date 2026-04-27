# Principles

Cross-cutting stances this project commits to. One principle per file.

See [`../../development-process.md`](../../development-process.md) § Foundations for the `kind:` taxonomy (`pedagogical` / `technical` / `product`).

## About this directory

This directory belongs entirely to **your project**. Principles you write here are *your* cross-cutting stances; specs and ADRs in your tree reference them via frontmatter; `ci/check_foundations.py` (when shipped) validates the references resolve.

The kanon kit ships only this README as a starter template. **kanon's own kit-author principles** (`P-prose-is-code`, `P-tiers-insulate`, `P-self-hosted-bootstrap`, etc.) live inside the kanon source repository and are *not* copied into your tree by `kanon init` or `kanon upgrade`. They are kit-author internal stances that govern how kanon evolves; they are not yours to inherit, override, or reason about. The aspect-and-depth model that *is* kit-shipped already encodes the design intent those principles serve — you do not need to import them.

If you want kanon's principles as inspiration for your own, read them in the kanon repository (`docs/foundations/principles/` on github.com/altakleos/kanon). Do not symlink, copy, or vendor the files into your project — they reference kit-internal concerns (`kanon kit`, "self-hosted-bootstrap", etc.) that will be confusing or wrong in your context.

## Index

*(empty — add principles as the project's cross-cutting stances crystallise)*

## Template

Each principle file has TOGAF-flavoured sections: Statement / Rationale / Implications / Exceptions and Tensions / Source.

```markdown
---
id: P-<slug>
kind: technical | pedagogical | product
status: draft | accepted | superseded
date: YYYY-MM-DD
---
# <Title>

## Statement
## Rationale
## Implications
## Exceptions / Tensions
## Source
```
