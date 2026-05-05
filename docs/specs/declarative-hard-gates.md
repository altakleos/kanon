---
status: accepted
date: 2026-05-04
fixtures:
  - tests/test_declarative_gates.py
invariant_coverage:
  INV-declarative-hard-gates-frontmatter-schema:
    - tests/test_declarative_gates.py::test_discovers_gates_from_frontmatter
  INV-declarative-hard-gates-priority-unique:
    - tests/test_declarative_gates.py::test_duplicate_priority_raises
  INV-declarative-hard-gates-depth-filtering:
    - tests/test_declarative_gates.py::test_depth_filtering
    - tests/test_declarative_gates.py::test_depth_filtering_includes_at_sufficient_depth
  INV-declarative-hard-gates-decision-tree-dynamic:
    - tests/test_declarative_gates.py::test_decision_tree_generated_from_questions
  INV-declarative-hard-gates-skip-when-rendered:
    - tests/test_declarative_gates.py::test_skip_when_rendered
  INV-declarative-hard-gates-fires-from-invoke-when:
    - tests/test_declarative_gates.py::test_fires_from_invoke_when
  INV-declarative-hard-gates-publisher-symmetric:
    - tests/test_declarative_gates.py::test_publisher_symmetric
---
# Spec: Declarative Hard Gates

## Intent

Hard gates are declared in protocol frontmatter rather than a static Python list, enabling publisher-symmetric gate declaration by any aspect (kit, project, or third-party).

## Invariants

<!-- INV-declarative-hard-gates-frontmatter-schema -->
- **INV-declarative-hard-gates-frontmatter-schema**: A protocol declares itself as a hard gate by including all of: `gate: hard`, `label:`, `summary:`, `audit:`, `priority:` (integer), `question:`. Missing any required field when `gate: hard` is present is a scaffold-time error.
<!-- INV-declarative-hard-gates-priority-unique -->
- **INV-declarative-hard-gates-priority-unique**: No two active hard gates may share the same `priority` value. Collision is a scaffold-time error. Convention: kit aspects use 1–999, consumer/third-party aspects use 1000+.
<!-- INV-declarative-hard-gates-depth-filtering -->
- **INV-declarative-hard-gates-depth-filtering**: A gate only renders when its aspect is enabled AND the aspect's configured depth >= the protocol's `depth-min`.
<!-- INV-declarative-hard-gates-decision-tree-dynamic -->
- **INV-declarative-hard-gates-decision-tree-dynamic**: The "Before every source-modifying tool call" checklist is generated from active gates' `question` fields, sorted by `priority`, bookended by the trivial-check (first) and audit-sentence (last).
<!-- INV-declarative-hard-gates-skip-when-rendered -->
- **INV-declarative-hard-gates-skip-when-rendered**: If a gate declares `skip-when:`, it is rendered as an indented "Skip if:" line below the gate's question in the decision tree.
<!-- INV-declarative-hard-gates-fires-from-invoke-when -->
- **INV-declarative-hard-gates-fires-from-invoke-when**: The "Fires when" column in the hard-gates table uses the protocol's `invoke-when:` frontmatter field (single source of truth).
<!-- INV-declarative-hard-gates-publisher-symmetric -->
- **INV-declarative-hard-gates-publisher-symmetric**: Kit (`kanon-*`), consumer (`project-*`), and third-party aspects declare gates via identical frontmatter fields with no code-path distinction.

## Rationale

The previous design stored gate metadata in a static `_HARD_GATES` Python list in `kanon-core`. This violated publisher symmetry (only kit aspects could declare gates), duplicated data already present in protocol frontmatter (`invoke-when`, `depth-min`), and required a code change + release cycle to add or modify gates.

Moving to frontmatter:
- Eliminates the privileged registry
- Makes gate declaration a content change, not a code change
- Enables project-aspects and third-party aspects to declare hard gates
- Keeps all gate metadata co-located with the protocol body

## Out of Scope

- Gate composition algebra (a project gate replacing a kit gate via `replaces:`). Deferred to v1.0.
- Machine-readable gate evaluation by `kanon preflight`. Deferred until fidelity infrastructure matures.
- Conditional gate suppression via config (`enabled: false`). Deferred — needs guardrails.
- Per-gate CI enforcement (hard CI checks for each gate). Separate spec: `process-gates.md`.

## Decisions

- [ADR-0062](../decisions/0062-declarative-hard-gates.md): Move gate declarations from Python code to protocol frontmatter.
