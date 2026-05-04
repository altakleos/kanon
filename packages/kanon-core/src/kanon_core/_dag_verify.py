"""DAG-driven verification engine (ADR-0061).

Builds the artifact graph, detects changes, walks downstream from changed
nodes, and dispatches node/edge handlers to produce structured findings.
"""
from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path

from kanon_core._findings import Finding, NodeHandler, EdgeHandler
from kanon_core._graph import GraphData, Node, Edge, build_graph
from kanon_core._change_detection import (
    detect_changes, load_hash_store, save_hash_store,
)


# -- Dispatch tables (populated by register_* or directly) --

_NODE_HANDLERS: dict[str, list[NodeHandler]] = defaultdict(list)
_EDGE_HANDLERS: dict[str, list[EdgeHandler]] = defaultdict(list)


def register_node_handler(namespace: str, handler: NodeHandler) -> None:
    """Register a handler for nodes in the given namespace."""
    _NODE_HANDLERS[namespace].append(handler)


def register_edge_handler(edge_kind: str, handler: EdgeHandler) -> None:
    """Register a handler for edges of the given kind."""
    _EDGE_HANDLERS[edge_kind].append(handler)


def _downstream_walk(
    seeds: set[tuple[str, str]], graph: GraphData,
) -> list[tuple[str, str]]:
    """BFS walk downstream from seed nodes, returning visit order."""
    visited: set[tuple[str, str]] = set()
    order: list[tuple[str, str]] = []
    queue: deque[tuple[str, str]] = deque(seeds)
    while queue:
        key = queue.popleft()
        if key in visited:
            continue
        visited.add(key)
        order.append(key)
        # Walk downstream: find edges where this node is the destination
        # and add the source nodes (they depend on us)
        for edge in graph.inbound_all.get(key, []):
            src_key = (edge.src_namespace, edge.src_slug)
            if src_key not in visited:
                queue.append(src_key)
    return order


def _build_chains(
    findings: list[Finding], graph: GraphData,
) -> tuple[list[list[Finding]], list[Finding]]:
    """Group findings into impact chains and standalone findings."""
    chains: dict[str, list[Finding]] = defaultdict(list)
    standalone: list[Finding] = []
    for f in findings:
        if f.chain:
            chains[f.chain[0]].append(f)
        else:
            standalone.append(f)
    return [v for v in chains.values()], standalone


def run_dag_verify(
    target: Path, graph: GraphData, *, full: bool = False,
) -> list[Finding]:
    """Run DAG-driven verification.

    Args:
        target: Repository root.
        graph: Pre-built artifact graph.
        full: If True, verify all nodes (ignore hash store).

    Returns:
        List of structured findings.
    """
    kanon_dir = target / ".kanon"
    findings: list[Finding] = []

    # Change detection
    if full:
        seeds = {(n.namespace, n.slug) for n in graph.nodes}
    else:
        store = load_hash_store(kanon_dir)
        seeds = detect_changes(graph.nodes, target, store)
        save_hash_store(kanon_dir, store)

    if not seeds:
        return findings

    # Downstream walk
    visit_order = _downstream_walk(seeds, graph)

    # Build chain context for each visited node
    seed_set = seeds.copy()

    for ns, slug in visit_order:
        key = (ns, slug)
        node = graph.by_slug.get(key)
        if node is None:
            continue

        # Determine chain prefix
        chain = (f"{ns}/{slug}",)
        if key not in seed_set:
            # Find the edge that brought us here
            for edge in graph.inbound_all.get(key, []):
                src_key = (edge.src_namespace, edge.src_slug)
                if src_key in {(ns2, s2) for ns2, s2 in visit_order}:
                    chain = (f"{edge.dst_namespace}/{edge.dst_slug}",
                             f"{ns}/{slug}")
                    break

        # Dispatch node handlers
        for handler in _NODE_HANDLERS.get(ns, []):
            handler(node, target, findings)

        # Dispatch edge handlers for edges FROM this node
        for edge in graph.edges:
            if edge.src_namespace == ns and edge.src_slug == slug:
                dst_key = (edge.dst_namespace, edge.dst_slug) if edge.dst_namespace else None
                dst_node = graph.by_slug.get(dst_key) if dst_key else None
                for handler in _EDGE_HANDLERS.get(edge.kind, []):
                    handler(edge, node, dst_node, target, findings)

    return findings


def format_findings(findings: list[Finding]) -> tuple[list[str], list[str]]:
    """Format findings into legacy errors/warnings lists for backward compat."""
    errors: list[str] = []
    warnings: list[str] = []
    for f in findings:
        line = f.message
        if f.severity == "error":
            errors.append(line)
        else:
            warnings.append(line)
    return errors, warnings
