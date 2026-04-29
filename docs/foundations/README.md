# Foundations

Cross-cutting source material this project commits to. Feature artifacts (specs, ADRs, plans) cite foundations rather than pass through them. Foundations are not a processing stage; nothing flows into or out of them in a normal feature's life cycle. They are the corpus the stack assumes.

## Sub-namespaces

Three sub-namespaces under `docs/foundations/`:

- **Vision** (`vision.md`) — a single narrative document describing the product's identity, mission, and non-goals. Read first by every contributor and every LLM-agent session.
- **Principles** (`principles/<slug>.md`) — cross-cutting stances the project commits to, one per file. Distinguished by a `kind:` frontmatter field: `pedagogical` (project-specific design stances that shape product behaviour), `technical` (how artifacts are built), or `product` (broader-than-any-one-spec user promises). TOGAF-flavoured shape: Statement / Rationale / Implications / Exceptions and Tensions / Source. When a stance could sit in two categories, prefer `pedagogical` over `product`, and `technical` over `pedagogical` — the more specific tag wins.
- **Personas** (`personas/<slug>.md`) — design-stressing user scenarios. Distinct from specs: specs describe product guarantees; personas describe users whose presence stress-tests those guarantees. Each persona carries an `owner:` and a `stresses:` list pointing at the specs and principles it exercises.

## Linkage to the layer stack

Feature specs link upward to foundations via optional frontmatter:

- `serves: [<slug>, ...]` — vision or product principles this spec realises.
- `realizes: [<P-slug>, ...]` — technical or pedagogical principles this spec embodies.
- `stressed_by: [<persona-slug>, ...]` — personas that exercise this spec.

Personas link downward via `stresses: [<spec-slug>, <P-slug>, ...]` pointing at the artifacts they stress-test.

These links are machine-verifiable. Projects should ship a validator that asserts every slug resolves to an existing foundation file of the correct type; broken references are a release-blocking error, not a warning. The validator's concrete form is a project-instantiation choice.

The validator hard-fails on broken slugs and invalid `kind:` values. It warns (non-blocking) when an accepted principle is not referenced by any spec — scheduled to promote to hard-fail once backreference wiring has settled.

## Lifecycle and migration

Foundations are mutable but superseded-with-trail — never deleted. When a principle is superseded, the old file carries a `superseded-by:` frontmatter field and remains in place for archaeology. Moving an invariant from a feature spec up to a principle (or down from a principle to a feature spec) requires an ADR-lite with explicit Before-state / After-state / Why sections.

## Optional-but-prescribed

Foundations is a recognised artifact class in this method but is not required. A project with no cross-cutting product philosophy (a single-feature CLI, a data-transformation utility) may leave `docs/foundations/` empty or use only `principles/` for technical stances (e.g., "UTF-8 everywhere"). The extension is available when a project has cross-cutting concerns to name; projects without them pay no cost.

> Foundations content authored in Phase B. Commit 1 ships empty subdirectories + this index and `vision.md`.
