---
status: accepted
date: 2026-05-04
---
# ADR-0062: Declarative Hard Gates via Protocol Frontmatter

## Context

Hard gates enforce that LLM agents emit audit-trail sentences before source-modifying tool calls. They survive context-window compaction because they're rendered in the AGENTS.md boot section.

Prior to this decision, gates were declared in a static `_HARD_GATES` Python list in `kanon-core/_scaffold.py`. This had three problems:

1. **Publisher symmetry violation**: Only kit aspects could declare hard gates. Project-aspects and third-party aspects had no mechanism.
2. **Data duplication**: The Python list duplicated `invoke-when` and `depth-min` already present in protocol frontmatter.
3. **Release coupling**: Adding or modifying a gate required a code change to `kanon-core` plus a release cycle.

Additionally, the decision-tree prose ("Before every source-modifying tool call, answer these questions") was static and only mentioned `plan-before-build`, even when `spec-before-design` and `design-before-plan` were active.

## Decision

A protocol declares itself as a hard gate by including these fields in its YAML frontmatter:

```yaml
gate: hard
label: <display name>
summary: <one-line description>
audit: <audit-trail sentence template>
priority: <integer, controls rendering order>
question: <decision-tree question>
skip-when: <conditions under which the gate should not fire>
```

`_render_hard_gates()` discovers gates by iterating all active protocols, filtering on `gate: hard`, and sorting by `priority`. The decision tree is generated dynamically from each gate's `question` field.

Priority convention: kit aspects reserve 1–999, consumer/third-party aspects use 1000+.

## Alternatives Considered

1. **Gates in manifest.yaml** — Splits gate metadata across two files (manifest + protocol). Rejected: frontmatter keeps everything co-located.
2. **Separate gates.yaml per aspect** — Extra file, extra indirection. Rejected: no advantage over frontmatter.
3. **Keep static list, just fix the decision tree** — Doesn't achieve publisher symmetry, still requires code changes. Rejected.
4. **Template-based decision tree (Jinja)** — Over-engineered for a simple string builder. Rejected.

## Consequences

- Any aspect can now declare hard gates via frontmatter — publisher symmetry restored.
- Adding a gate is a content change (edit a .md file), not a code change.
- The decision tree adapts automatically to active gates and depths.
- `skip-when:` conditions are visible post-compaction without reading the full protocol.
- The `_HardGate` TypedDict and `_HARD_GATES` list are eliminated from `kanon-core`.

## Config Impact

None. No changes to `.kanon/config.yaml` schema. Gate declaration is purely in protocol frontmatter.

## References

- [Spec: Declarative Hard Gates](../specs/declarative-hard-gates.md)
- [ADR-0034](0034-hard-gates-table.md): Original hard-gates table design
- [ADR-0056](0056-sdd-protocol-gaps.md): design-before-plan protocol addition
