"""Composition algebra — topo-sort, cycle detection, replaces resolution.

Phase A.6d implementation per ADR-0041 §Decision 3 (composition algebra),
design `docs/design/dialect-grammar.md` §"Composition resolution algorithm",
spec `docs/specs/dialect-grammar.md` (INV-dialect-grammar-composition-acyclic,
INV-dialect-grammar-replaces-substitution).

When multiple contracts target the same ``surface:``, the kernel orders them via
topological sort over ``before:`` / ``after:`` edges. ``replaces:`` substitutes
one contract for another. Cycles fail loudly with explicit cycle-path reporting.

Wiring into substrate runtime (composition at replay time) deferred — coupled
with the absence of real contracts. The algebra is exercised via direct tests.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContractRef:
    """A composable contract reference.

    ``contract_id`` is the canonical ``<aspect-slug>/<contract-slug>``.
    ``before`` / ``after`` / ``replaces`` are tuples of contract_ids this
    contract orders against (forward, backward, substitution respectively).
    """

    contract_id: str
    surface: str
    before: tuple[str, ...] = ()
    after: tuple[str, ...] = ()
    replaces: tuple[str, ...] = ()


@dataclass
class CompositionError:
    """One finding from compose().

    ``code`` is one of:

    - ``composition-cycle``: a hard error; the substrate refuses to load.
    - ``ambiguous-composition``: a warning; two contracts on the same surface
      have no relationship; the substrate proceeds with alphabetical
      tie-break but informs the consumer their composition is under-specified.
    """

    code: str
    surface: str
    detail: str


def _resolve_replaces(
    candidates: list[ContractRef], findings: list[CompositionError], surface: str
) -> list[ContractRef]:
    """Drop contracts that some other candidate replaces.

    Detects replaces-cycles (A replaces B, B replaces A) as
    composition-cycle errors. Returns the surviving (non-replaced) contracts.
    """
    by_id: dict[str, ContractRef] = {c.contract_id: c for c in candidates}
    # Build the replaces graph: replacer → set(replaced ids) for cycle check.
    replaces_graph: dict[str, set[str]] = {
        c.contract_id: set(c.replaces) for c in candidates
    }
    # DFS for cycles in the replaces graph.
    state: dict[str, int] = {}  # 0=unvisited, 1=visiting, 2=done

    def dfs(node: str, path: list[str]) -> list[str] | None:
        if state.get(node) == 1:
            cycle_start = path.index(node)
            return path[cycle_start:] + [node]
        if state.get(node) == 2:
            return None
        state[node] = 1
        path.append(node)
        for nxt in sorted(replaces_graph.get(node, set())):
            if nxt in by_id:
                cycle = dfs(nxt, path)
                if cycle is not None:
                    return cycle
        state[node] = 2
        path.pop()
        return None

    for node in sorted(by_id):
        cycle = dfs(node, [])
        if cycle is not None:
            # Per docs/specs/dialect-grammar.md INV 6: replaces-graph cycles
            # surface as `code: replacement-cycle`. Distinct from the
            # before/after composition cycle below (`code: composition-cycle`)
            # so publishers can pattern-match the two failure modes.
            findings.append(
                CompositionError(
                    code="replacement-cycle",
                    surface=surface,
                    detail=(
                        "replaces cycle: "
                        + " --replaces--> ".join(cycle)
                    ),
                )
            )
            return []  # broken composition; bail
    # Drop the replaced contracts.
    replaced_ids: set[str] = set()
    for c in candidates:
        for r in c.replaces:
            if r in by_id:
                replaced_ids.add(r)
    return [c for c in candidates if c.contract_id not in replaced_ids]


def _topological_sort(
    nodes: list[str],
    edges: dict[str, set[str]],
    findings: list[CompositionError],
    surface: str,
) -> list[str] | None:
    """Kahn's algorithm with stable alphabetical tie-break.

    edges[u] = {v, w, ...} means u executes BEFORE v and BEFORE w.
    Returns the topological ordering, or None if a cycle exists.
    """
    # Compute in-degrees.
    indeg: dict[str, int] = {n: 0 for n in nodes}
    for u in nodes:
        for v in edges.get(u, set()):
            if v in indeg:
                indeg[v] += 1
    # Initial roots (in-degree 0), sorted alphabetically for determinism.
    roots = sorted([n for n in nodes if indeg[n] == 0])
    ordering: list[str] = []
    while roots:
        # Stable tie-break: alphabetical pop.
        roots.sort()
        n = roots.pop(0)
        ordering.append(n)
        for v in sorted(edges.get(n, set())):
            if v not in indeg:
                continue
            indeg[v] -= 1
            if indeg[v] == 0:
                roots.append(v)
    if len(ordering) != len(nodes):
        # Cycle exists; identify it via DFS for reporting.
        unvisited = set(nodes) - set(ordering)
        cycle_path = _find_cycle(unvisited, edges)
        findings.append(
            CompositionError(
                code="composition-cycle",
                surface=surface,
                detail=(
                    "before/after cycle: "
                    + " --before--> ".join(cycle_path)
                    if cycle_path
                    else f"cycle among {sorted(unvisited)!r}"
                ),
            )
        )
        return None
    return ordering


def _find_cycle(nodes: set[str], edges: dict[str, set[str]]) -> list[str]:
    """DFS to find ANY cycle in the subgraph; returns cycle path."""
    state: dict[str, int] = {}

    def dfs(node: str, path: list[str]) -> list[str] | None:
        if state.get(node) == 1:
            cycle_start = path.index(node)
            return path[cycle_start:] + [node]
        if state.get(node) == 2:
            return None
        state[node] = 1
        path.append(node)
        for nxt in sorted(edges.get(node, set())):
            if nxt in nodes:
                cycle = dfs(nxt, path)
                if cycle is not None:
                    return cycle
        state[node] = 2
        path.pop()
        return None

    for n in sorted(nodes):
        result = dfs(n, [])
        if result is not None:
            return result
    return []


def compose(
    contracts: list[ContractRef], surface: str
) -> tuple[list[ContractRef], list[CompositionError]]:
    """Compose contracts targeting *surface* into topological order.

    Per design steps:
      1. Filter to contracts targeting `surface`.
      2. Resolve `replaces:` substitution.
      3. Build directed graph from `before:` / `after:` edges.
      4. Topological sort (Kahn's, alphabetical tie-break).
      5. On cycle, return CompositionError with cycle-path detail.
      6. When two contracts have no relationship, emit
         ambiguous-composition warning.

    Returns (ordering, findings). `findings` includes both fatal errors
    (composition-cycle) and warnings (ambiguous-composition).
    """
    findings: list[CompositionError] = []

    # Step 1: filter.
    candidates = [c for c in contracts if c.surface == surface]
    if not candidates:
        return ([], findings)

    # Step 2: resolve replaces.
    active = _resolve_replaces(candidates, findings, surface)
    if not active:
        return ([], findings)
    by_id = {c.contract_id: c for c in active}

    # Step 3: build edges. edges[u] = set of vs where u -> v ("u before v").
    edges: dict[str, set[str]] = {c.contract_id: set() for c in active}
    for c in active:
        for target in c.before:
            if target in by_id:
                edges[c.contract_id].add(target)  # c BEFORE target
        for target in c.after:
            if target in by_id:
                edges[target].add(c.contract_id)  # target BEFORE c

    # Step 4: topological sort.
    nodes = list(by_id.keys())
    ordering = _topological_sort(nodes, edges, findings, surface)
    if ordering is None:
        return ([], findings)

    # Step 6: ambiguity check. Two contracts are AMBIGUOUSLY ordered if
    # neither has a path to the other. Emit a warning naming the unrelated
    # pair; the alphabetical tie-break above provides a stable order.
    if len(active) > 1:
        # Build reachability (transitive closure of edges) per node.
        reach: dict[str, set[str]] = {n: set() for n in nodes}
        for n in nodes:
            stack = list(edges.get(n, set()))
            while stack:
                m = stack.pop()
                if m in reach[n]:
                    continue
                reach[n].add(m)
                stack.extend(edges.get(m, set()))
        # Find unrelated pairs.
        unrelated: list[tuple[str, str]] = []
        for i, a in enumerate(nodes):
            for b in nodes[i + 1 :]:
                if b not in reach[a] and a not in reach[b]:
                    unrelated.append((a, b))
        if unrelated:
            pairs_str = ", ".join(f"{a} ↔ {b}" for a, b in sorted(unrelated))
            findings.append(
                CompositionError(
                    code="ambiguous-composition",
                    surface=surface,
                    detail=(
                        f"unrelated contracts on surface (alphabetical "
                        f"fallback applied): {pairs_str}"
                    ),
                )
            )

    return ([by_id[cid] for cid in ordering], findings)
