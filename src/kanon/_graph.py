"""Cross-link graph load — typed nodes and edges over the repository.

The graph models the seven slug namespaces declared in
``docs/specs/spec-graph-rename.md``: principle, persona, spec, aspect,
capability, inv-anchor, adr. Phase-1 ships node discovery plus the four
edge kinds the orphan and rename commands rely on:

- ``realizes``    — spec → principle      (spec frontmatter ``realizes:``)
- ``serves``      — spec → vision/spec    (spec frontmatter ``serves:``)
- ``stressed_by`` — spec → persona        (spec frontmatter ``stressed_by:``)
- ``stresses``    — persona → spec/principle (persona frontmatter ``stresses:``)
- ``requires``    — aspect → aspect/cap   (per-aspect sub-manifest ``requires:``)
- ``serves_plan`` — plan → spec           (plan frontmatter ``serves:`` or
                                           prose ``](specs/<slug>.md)``)
- ``inv_ref``     — spec → spec           (INV-* anchor reference whose slug
                                           prefix names another spec)

The module is read-only: every public function returns plain dataclasses
and never mutates the working tree. Orphan-policy filtering (live-status
exclusion, ``orphan-exempt:`` opt-out) is the caller's responsibility —
this module exposes raw edges and inbound indices in two flavors
(``inbound_all`` and ``inbound_live``) so the policy lives at the
consumer site, not the graph site.

Per ``docs/specs/spec-graph-orphans.md`` (INV-8: shared graph-load
primitive) and ``docs/specs/spec-graph-rename.md`` (INV-3: ops-manifest
target file enumeration).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

NAMESPACE_PRINCIPLE = "principle"
NAMESPACE_PERSONA = "persona"
NAMESPACE_SPEC = "spec"
NAMESPACE_ASPECT = "aspect"
NAMESPACE_CAPABILITY = "capability"
NAMESPACE_VISION = "vision"
NAMESPACE_PLAN = "plan"  # edge-source-only namespace (plans aren't orphan-candidates)

KNOWN_NAMESPACES: frozenset[str] = frozenset({
    NAMESPACE_PRINCIPLE,
    NAMESPACE_PERSONA,
    NAMESPACE_SPEC,
    NAMESPACE_ASPECT,
    NAMESPACE_CAPABILITY,
    NAMESPACE_VISION,
    NAMESPACE_PLAN,
})

LIVE_STATUSES: frozenset[str] = frozenset({
    "accepted",
    "accepted (lite)",
    "provisional",
    "draft",
})
"""Statuses that contribute inbound edges per orphans-spec INV-3.

Excluded: ``deferred``, ``superseded`` (and any unrecognised value).
A node with no ``status:`` field is treated as live (e.g., ``vision.md``,
aspect entries — they aren't lifecycle-tracked the way specs are).
"""

EDGE_REALIZES = "realizes"
EDGE_SERVES = "serves"
EDGE_STRESSED_BY = "stressed_by"
EDGE_STRESSES = "stresses"
EDGE_REQUIRES = "requires"
EDGE_SERVES_PLAN = "serves_plan"
EDGE_INV_REF = "inv_ref"


@dataclass(frozen=True)
class Node:
    """A typed node in the cross-link graph.

    ``slug`` is the canonical identifier within the ``namespace`` (e.g.,
    ``P-prose-is-code`` for a principle, ``aspect-config`` for a spec,
    ``worktrees`` for an aspect). ``slug`` values are NOT globally unique
    across namespaces — always key by ``(namespace, slug)``.

    ``status`` is the frontmatter status string when present, ``None``
    otherwise. ``extra`` holds namespace-specific frontmatter fields that
    callers care about (``kind`` for principles, ``orphan-exempt`` /
    ``orphan-exempt-reason`` for any node opting out).
    """

    slug: str
    namespace: str
    path: Path
    status: str | None
    frontmatter: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def is_live(self) -> bool:
        """True iff this node contributes inbound edges per orphans-spec INV-3."""
        if self.status is None:
            return True
        return self.status in LIVE_STATUSES

    def is_orphan_exempt(self) -> bool:
        """True iff frontmatter sets ``orphan-exempt: true``."""
        return bool(self.frontmatter.get("orphan-exempt"))

    def orphan_exempt_reason(self) -> str | None:
        """Returns the ``orphan-exempt-reason:`` string when present."""
        reason = self.frontmatter.get("orphan-exempt-reason")
        return reason if isinstance(reason, str) else None


@dataclass(frozen=True)
class Edge:
    """A typed edge between two nodes (or a phantom plan source → spec).

    ``dst_namespace`` is ``None`` when the edge target's namespace cannot
    be inferred from the edge field alone (e.g., a ``stresses:`` slug
    could point at a spec or a principle). The graph builder resolves
    these post-hoc against the discovered node set.
    """

    src_slug: str
    src_namespace: str
    dst_slug: str
    dst_namespace: str | None
    kind: str
    src_path: Path | None = None


@dataclass(frozen=True)
class GraphData:
    """The fully-loaded graph: nodes, edges, and pre-computed indices.

    ``by_slug`` maps ``(namespace, slug)`` to its ``Node``.
    ``inbound_all`` and ``inbound_live`` map ``(namespace, slug)`` to
    the list of edges pointing at that node — the ``_live`` variant
    filters out edges whose source node fails ``is_live()``. Callers
    computing orphans use ``inbound_live``; callers wanting the raw
    structural picture use ``inbound_all``.
    """

    nodes: list[Node]
    edges: list[Edge]
    by_slug: dict[tuple[str, str], Node]
    inbound_all: dict[tuple[str, str], list[Edge]]
    inbound_live: dict[tuple[str, str], list[Edge]]


# ---------------------------------------------------------------------------
# Frontmatter parsing


_FRONTMATTER_BOUNDARY = "\n---\n"


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return ``(frontmatter_dict, body)`` from a markdown file's text.

    Returns an empty dict when the file lacks frontmatter or its YAML is
    malformed — graph load tolerates broken files (they simply contribute
    no edges); ``ci/check_foundations.py`` is the validator that turns
    malformed frontmatter into a CI error.
    """
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find(_FRONTMATTER_BOUNDARY, 4)
    if end < 0:
        return {}, text
    try:
        fm = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return {}, text
    body = text[end + len(_FRONTMATTER_BOUNDARY):]
    return fm if isinstance(fm, dict) else {}, body


def _read_md(path: Path) -> tuple[dict[str, Any], str]:
    try:
        return _split_frontmatter(path.read_text(encoding="utf-8"))
    except OSError:
        return {}, ""


def _slug_list(value: Any) -> list[str]:
    """Coerce a frontmatter list-of-slugs to a clean list of strings."""
    if not isinstance(value, list):
        return []
    return [s for s in value if isinstance(s, str) and s]


# ---------------------------------------------------------------------------
# Node discovery


def _iter_md(directory: Path) -> Iterable[Path]:
    if not directory.is_dir():
        return
    for p in sorted(directory.glob("*.md")):
        if p.name == "README.md" or p.name == "_template.md":
            continue
        yield p


def _discover_principles(foundations: Path) -> list[Node]:
    nodes: list[Node] = []
    principles_dir = foundations / "principles"
    for path in _iter_md(principles_dir):
        fm, _ = _read_md(path)
        slug = fm.get("id")
        if not isinstance(slug, str) or not slug:
            continue
        nodes.append(Node(
            slug=slug,
            namespace=NAMESPACE_PRINCIPLE,
            path=path,
            status=fm.get("status") if isinstance(fm.get("status"), str) else None,
            frontmatter=fm,
            extra={"kind": fm.get("kind")},
        ))
    return nodes


def _discover_personas(foundations: Path) -> list[Node]:
    nodes: list[Node] = []
    personas_dir = foundations / "personas"
    for path in _iter_md(personas_dir):
        fm, _ = _read_md(path)
        slug = fm.get("id")
        if not isinstance(slug, str) or not slug:
            continue
        nodes.append(Node(
            slug=slug,
            namespace=NAMESPACE_PERSONA,
            path=path,
            status=fm.get("status") if isinstance(fm.get("status"), str) else None,
            frontmatter=fm,
        ))
    return nodes


def _discover_specs(specs_dir: Path) -> list[Node]:
    nodes: list[Node] = []
    for path in _iter_md(specs_dir):
        fm, _ = _read_md(path)
        nodes.append(Node(
            slug=path.stem,
            namespace=NAMESPACE_SPEC,
            path=path,
            status=fm.get("status") if isinstance(fm.get("status"), str) else None,
            frontmatter=fm,
        ))
    return nodes


def _discover_vision(foundations: Path) -> list[Node]:
    vision = foundations / "vision.md"
    if not vision.is_file():
        return []
    fm, _ = _read_md(vision)
    return [Node(
        slug="vision",
        namespace=NAMESPACE_VISION,
        path=vision,
        status=fm.get("status") if isinstance(fm.get("status"), str) else None,
        frontmatter=fm,
    )]


def _discover_aspects_and_capabilities(
    kit_root: Path,
) -> tuple[list[Node], list[Node], dict[str, list[str]]]:
    """Read top-manifest + per-aspect manifests; return aspect nodes, capability
    nodes, and a ``requires`` map (aspect-slug -> list of raw predicate strings).
    """
    top_path = kit_root / "manifest.yaml"
    if not top_path.is_file():
        return [], [], {}
    try:
        top = yaml.safe_load(top_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return [], [], {}

    aspects_data = top.get("aspects") if isinstance(top, dict) else None
    if not isinstance(aspects_data, dict):
        return [], [], {}

    aspect_nodes: list[Node] = []
    capability_set: set[str] = set()
    capability_owner: dict[str, str] = {}  # capability -> owning-aspect path
    requires_map: dict[str, list[str]] = {}

    for aspect_slug, entry in sorted(aspects_data.items()):
        if not isinstance(aspect_slug, str) or not isinstance(entry, dict):
            continue
        sub_path = entry.get("path")
        sub_manifest_file = (
            kit_root / sub_path / "manifest.yaml" if isinstance(sub_path, str) else None
        )
        sub_fm: dict[str, Any] = {}
        if sub_manifest_file is not None and sub_manifest_file.is_file():
            try:
                sub_fm = yaml.safe_load(sub_manifest_file.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                sub_fm = {}
        if not isinstance(sub_fm, dict):
            sub_fm = {}

        provides = entry.get("provides")
        if isinstance(provides, list):
            for cap in provides:
                if isinstance(cap, str) and cap:
                    capability_set.add(cap)
                    capability_owner.setdefault(cap, aspect_slug)

        requires = entry.get("requires")
        if isinstance(requires, list):
            requires_map[aspect_slug] = [r for r in requires if isinstance(r, str)]
        else:
            requires_map[aspect_slug] = []

        aspect_nodes.append(Node(
            slug=aspect_slug,
            namespace=NAMESPACE_ASPECT,
            path=sub_manifest_file or top_path,
            status=None,  # aspects aren't lifecycle-tracked
            frontmatter={"top": entry, "sub": sub_fm},
            extra={"provides": list(provides) if isinstance(provides, list) else []},
        ))

    capability_nodes = [
        Node(
            slug=cap,
            namespace=NAMESPACE_CAPABILITY,
            path=kit_root / "manifest.yaml",
            status=None,
            frontmatter={},
            extra={"owner": capability_owner.get(cap)},
        )
        for cap in sorted(capability_set)
    ]
    return aspect_nodes, capability_nodes, requires_map


# ---------------------------------------------------------------------------
# Edge extraction


def _spec_edges(spec_node: Node) -> list[Edge]:
    fm = spec_node.frontmatter
    edges: list[Edge] = []
    src = spec_node.slug
    src_path = spec_node.path
    for dst in _slug_list(fm.get("realizes")):
        edges.append(Edge(src, NAMESPACE_SPEC, dst, NAMESPACE_PRINCIPLE,
                          EDGE_REALIZES, src_path))
    for dst in _slug_list(fm.get("serves")):
        # `serves:` may name vision, another foundation, or another spec —
        # leave dst_namespace unresolved and let _resolve_dst classify.
        edges.append(Edge(src, NAMESPACE_SPEC, dst, None, EDGE_SERVES, src_path))
    for dst in _slug_list(fm.get("stressed_by")):
        edges.append(Edge(src, NAMESPACE_SPEC, dst, NAMESPACE_PERSONA,
                          EDGE_STRESSED_BY, src_path))
    return edges


def _persona_edges(persona_node: Node) -> list[Edge]:
    fm = persona_node.frontmatter
    edges: list[Edge] = []
    src = persona_node.slug
    src_path = persona_node.path
    for dst in _slug_list(fm.get("stresses")):
        # may point at spec OR principle — resolve later
        edges.append(Edge(src, NAMESPACE_PERSONA, dst, None, EDGE_STRESSES, src_path))
    return edges


_REQUIRES_CAPABILITY_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def _aspect_requires_edges(
    aspect_slug: str, predicates: list[str], aspect_path: Path,
) -> list[Edge]:
    """Per ADR-0026: ``requires:`` is a mixed list of depth-predicates
    (3 tokens, e.g. ``"sdd >= 1"``) and capability-presence predicates
    (1 token, e.g. ``"planning-discipline"``). Depth-predicates contribute
    aspect→aspect edges; capability-presence predicates contribute
    aspect→capability edges.
    """
    edges: list[Edge] = []
    for raw in predicates:
        tokens = raw.split()
        if len(tokens) == 3:
            edges.append(Edge(aspect_slug, NAMESPACE_ASPECT, tokens[0],
                              NAMESPACE_ASPECT, EDGE_REQUIRES, aspect_path))
        elif len(tokens) == 1 and _REQUIRES_CAPABILITY_RE.match(tokens[0]):
            edges.append(Edge(aspect_slug, NAMESPACE_ASPECT, tokens[0],
                              NAMESPACE_CAPABILITY, EDGE_REQUIRES, aspect_path))
        # Other shapes (zero / two / four+ tokens, or invalid 1-token) are
        # ignored here; ci/check_kit_consistency.py is the validator.
    return edges


_PROSE_SPEC_LINK_RE = re.compile(r"\]\(\.\./specs/([a-z0-9][a-z0-9-]*)\.md(?:#[^)\s]*)?\)")
_PROSE_SPEC_LINK_PLAINS_RE = re.compile(r"\]\(specs/([a-z0-9][a-z0-9-]*)\.md(?:#[^)\s]*)?\)")


def _plan_edges(plans_dir: Path) -> list[Edge]:
    """Plan→spec edges from plan frontmatter ``serves:`` and prose
    markdown links pointing at ``docs/specs/<slug>.md``.
    """
    edges: list[Edge] = []
    if not plans_dir.is_dir():
        return edges
    for path in _iter_md(plans_dir):
        fm, body = _read_md(path)
        plan_slug = path.stem
        # Frontmatter `serves:` may be a list or a single string (plans are
        # less rigid than specs).
        serves = fm.get("serves")
        if isinstance(serves, list):
            for raw in serves:
                spec_slug = _path_to_spec_slug(raw)
                if spec_slug:
                    edges.append(Edge(plan_slug, NAMESPACE_PLAN, spec_slug,
                                      NAMESPACE_SPEC, EDGE_SERVES_PLAN, path))
        elif isinstance(serves, str):
            spec_slug = _path_to_spec_slug(serves)
            if spec_slug:
                edges.append(Edge(plan_slug, NAMESPACE_PLAN, spec_slug,
                                  NAMESPACE_SPEC, EDGE_SERVES_PLAN, path))
        # Prose markdown links — both relative-from-plans and absolute-path forms.
        for match in _PROSE_SPEC_LINK_RE.finditer(body):
            edges.append(Edge(plan_slug, NAMESPACE_PLAN, match.group(1),
                              NAMESPACE_SPEC, EDGE_SERVES_PLAN, path))
        for match in _PROSE_SPEC_LINK_PLAINS_RE.finditer(body):
            edges.append(Edge(plan_slug, NAMESPACE_PLAN, match.group(1),
                              NAMESPACE_SPEC, EDGE_SERVES_PLAN, path))
    return edges


def _path_to_spec_slug(value: str) -> str | None:
    """Accept ``aspect-config``, ``docs/specs/aspect-config.md``,
    ``../specs/aspect-config.md`` — return ``aspect-config``.
    """
    if not value:
        return None
    if value.endswith(".md"):
        value = value[:-3]
    return value.rsplit("/", 1)[-1] or None


_INV_ANCHOR_REF_RE = re.compile(r"INV-([a-z][a-z0-9-]*?)-[a-z][a-z0-9-]*")
_INV_ANCHOR_DEF_RE = re.compile(r"<!--\s*INV-[a-z][a-z0-9-]*-[a-z][a-z0-9-]*\s*-->")


def _spec_inv_ref_edges(spec_node: Node, spec_slugs: set[str]) -> list[Edge]:
    """A spec body that names ``INV-<other-spec>-...`` (outside its own
    anchor definitions) implies a structural reference. Self-references
    are ignored. We use the longest known-spec-slug prefix to match;
    if no spec slug is the prefix, the reference is dropped silently
    (it may be a typo — ``ci/check_invariant_ids.py`` validates that).
    """
    try:
        body = spec_node.path.read_text(encoding="utf-8")
    except OSError:
        return []
    edges: list[Edge] = []
    seen: set[str] = set()
    # Strip anchor-definition lines so the regex matches only references.
    body_no_defs = _INV_ANCHOR_DEF_RE.sub("", body)
    for match in _INV_ANCHOR_REF_RE.finditer(body_no_defs):
        # Find the longest spec-slug that is a prefix of the captured tail.
        # The regex's lazy quantifier captured the SHORTEST prefix segment,
        # so re-derive: take everything between INV- and the final -<short>.
        full = match.group(0)
        rest = full[4:]  # strip "INV-"
        # Find the last "-" — that splits <slug>-<short>; the slug may
        # itself contain dashes.
        last_dash = rest.rfind("-")
        if last_dash < 0:
            continue
        candidate = rest[:last_dash]
        # Walk back through the candidate to find the longest known spec.
        target: str | None = None
        for i in range(len(candidate), 0, -1):
            piece = candidate[:i]
            if piece in spec_slugs:
                target = piece
                break
            # allow that the slug has multiple dashes by walking backward
            # over '-' boundaries
        if target is None or target == spec_node.slug:
            continue
        key = target
        if key in seen:
            continue
        seen.add(key)
        edges.append(Edge(spec_node.slug, NAMESPACE_SPEC, target,
                          NAMESPACE_SPEC, EDGE_INV_REF, spec_node.path))
    return edges


# ---------------------------------------------------------------------------
# Resolution and graph assembly


def _resolve_dst(edge: Edge, by_slug: dict[tuple[str, str], Node]) -> Edge:
    """Tighten an edge whose ``dst_namespace`` is ``None`` by trying each
    plausible namespace in deterministic order. Returns a new ``Edge``
    (since dataclasses are frozen). If nothing resolves, leaves
    ``dst_namespace`` as ``None`` and the edge becomes a dangling
    reference (the consumer treats it as not connecting any live node).
    """
    if edge.dst_namespace is not None:
        return edge
    candidates_by_kind: dict[str, list[str]] = {
        EDGE_SERVES: [NAMESPACE_VISION, NAMESPACE_SPEC, NAMESPACE_PRINCIPLE,
                      NAMESPACE_PERSONA],
        EDGE_STRESSES: [NAMESPACE_SPEC, NAMESPACE_PRINCIPLE],
    }
    for ns in candidates_by_kind.get(edge.kind, []):
        if (ns, edge.dst_slug) in by_slug:
            return Edge(
                edge.src_slug, edge.src_namespace, edge.dst_slug, ns,
                edge.kind, edge.src_path,
            )
    return edge


def build_graph(repo_root: Path) -> GraphData:
    """Load every node and edge in the cross-link graph rooted at *repo_root*.

    The function is deterministic: nodes within a namespace are sorted by
    slug, edges are emitted in the order their source files are visited.
    Two runs over the same tree produce identical ``GraphData``.

    No I/O happens after this returns — the result is a snapshot of the
    on-disk state at call time.
    """
    foundations = repo_root / "docs" / "foundations"
    specs_dir = repo_root / "docs" / "specs"
    plans_dir = repo_root / "docs" / "plans"
    kit_root = repo_root / "src" / "kanon" / "kit"

    principle_nodes = _discover_principles(foundations)
    persona_nodes = _discover_personas(foundations)
    spec_nodes = _discover_specs(specs_dir)
    vision_nodes = _discover_vision(foundations)
    aspect_nodes, capability_nodes, requires_map = (
        _discover_aspects_and_capabilities(kit_root)
    )

    nodes: list[Node] = (
        principle_nodes + persona_nodes + spec_nodes + vision_nodes
        + aspect_nodes + capability_nodes
    )
    by_slug: dict[tuple[str, str], Node] = {(n.namespace, n.slug): n for n in nodes}

    edges: list[Edge] = []
    for spec_node in spec_nodes:
        edges.extend(_spec_edges(spec_node))
    for persona_node in persona_nodes:
        edges.extend(_persona_edges(persona_node))
    for aspect_node in aspect_nodes:
        edges.extend(_aspect_requires_edges(
            aspect_node.slug,
            requires_map.get(aspect_node.slug, []),
            aspect_node.path,
        ))
    edges.extend(_plan_edges(plans_dir))

    spec_slug_set = {n.slug for n in spec_nodes}
    for spec_node in spec_nodes:
        edges.extend(_spec_inv_ref_edges(spec_node, spec_slug_set))

    edges = [_resolve_dst(e, by_slug) for e in edges]

    inbound_all: dict[tuple[str, str], list[Edge]] = {}
    inbound_live: dict[tuple[str, str], list[Edge]] = {}
    for edge in edges:
        if edge.dst_namespace is None:
            continue  # unresolved (e.g., persona stresses: foo where foo isn't a node)
        key = (edge.dst_namespace, edge.dst_slug)
        if key not in by_slug:
            continue  # dangling: target doesn't exist as a node (broken reference)
        inbound_all.setdefault(key, []).append(edge)
        src_node = by_slug.get((edge.src_namespace, edge.src_slug))
        # Plans are never first-class nodes but always count as live source
        # for orphan-detection purposes (per orphans-spec INV-2(a)).
        if edge.src_namespace == NAMESPACE_PLAN or (src_node and src_node.is_live()):
            inbound_live.setdefault(key, []).append(edge)

    return GraphData(
        nodes=nodes,
        edges=edges,
        by_slug=by_slug,
        inbound_all=inbound_all,
        inbound_live=inbound_live,
    )


# ---------------------------------------------------------------------------
# Orphan detection (`kanon graph orphans` core)


ORPHAN_CANDIDATE_NAMESPACES: tuple[str, ...] = (
    NAMESPACE_PRINCIPLE,
    NAMESPACE_PERSONA,
    NAMESPACE_SPEC,
    NAMESPACE_CAPABILITY,
)
"""Namespaces that participate in orphan reporting.

Per orphans-spec INV-1, vision is excluded (it's a singleton intent
node), aspects are excluded (they aren't required to be referenced from
elsewhere — they're top-level features), and plans aren't first-class
nodes. ADRs are excluded by spec out-of-scope rule.
"""


@dataclass(frozen=True)
class OrphanRecord:
    """Single orphan entry — one row in the `kanon graph orphans` report."""

    slug: str
    namespace: str
    exempt: bool
    reason: str | None


def compute_orphans(
    graph: GraphData,
    filter_namespace: str | None = None,
) -> dict[str, list[OrphanRecord]]:
    """Return orphans keyed by namespace, applying orphans-spec INV-2..INV-5.

    Per INV-3, only live source nodes contribute inbound edges — the
    ``inbound_live`` index already encodes that. Per INV-4, deferred
    specs are themselves never reported as orphans (their lack of
    inbound is by design — work hasn't started). Per INV-5, nodes with
    ``orphan-exempt: true`` are still listed but flagged exempt.

    The persona rule (INV-2) has a second clause: a persona is
    non-orphan when its own ``stresses:`` list points at any live spec
    or principle, even if no spec stresses it back. This is checked
    explicitly here since the inbound index alone does not capture it.
    """
    namespaces: tuple[str, ...] = (
        (filter_namespace,) if filter_namespace is not None
        else ORPHAN_CANDIDATE_NAMESPACES
    )
    result: dict[str, list[OrphanRecord]] = {ns: [] for ns in namespaces}

    persona_outbound_live = _persona_outbound_live(graph)
    capability_inbound = _capability_inbound_count(graph)

    for ns in namespaces:
        if ns not in ORPHAN_CANDIDATE_NAMESPACES:
            continue  # silently no-op for namespaces that aren't candidates
        for node in graph.nodes:
            if node.namespace != ns:
                continue
            # INV-3: deferred/superseded specs are excluded from the
            # orphan-candidate list (they aren't load-bearing yet).
            if not node.is_live():
                continue
            # INV-4: deferred-spec self-orphan rule is the same predicate
            # as INV-3 since `is_live()` rejects deferred status.
            inbound_count = len(graph.inbound_live.get((ns, node.slug), []))
            is_orphan: bool
            if ns == NAMESPACE_PERSONA:
                outbound = persona_outbound_live.get(node.slug, 0)
                is_orphan = inbound_count == 0 and outbound == 0
            elif ns == NAMESPACE_CAPABILITY:
                # Capability orphan = no `requires:` predicate names it.
                is_orphan = capability_inbound.get(node.slug, 0) == 0
            else:
                is_orphan = inbound_count == 0

            if not is_orphan:
                continue

            result[ns].append(OrphanRecord(
                slug=node.slug,
                namespace=ns,
                exempt=node.is_orphan_exempt(),
                reason=node.orphan_exempt_reason() if node.is_orphan_exempt() else None,
            ))

    # Stable ordering: alphabetical by slug within each namespace
    # (orphans-spec INV-7 last bullet).
    for rows in result.values():
        rows.sort(key=lambda r: r.slug)
    return result


def _persona_outbound_live(graph: GraphData) -> dict[str, int]:
    """Count of `stresses:` edges from each persona that resolve to a
    LIVE spec or principle. Personas whose outbound only points at
    deferred targets count as 0 (the spec deems them effectively
    unreferenced)."""
    out: dict[str, int] = {}
    for edge in graph.edges:
        if edge.kind != EDGE_STRESSES or edge.dst_namespace is None:
            continue
        target = graph.by_slug.get((edge.dst_namespace, edge.dst_slug))
        if target is None or not target.is_live():
            continue
        out[edge.src_slug] = out.get(edge.src_slug, 0) + 1
    return out


def _capability_inbound_count(graph: GraphData) -> dict[str, int]:
    """Count of capability-presence ``requires:`` edges pointing at each
    capability. The orphans-spec capability rule (INV-2 last bullet)
    asks whether ANY aspect's ``requires:`` list contains the capability
    as a 1-token predicate; the count is just the size of that set.
    """
    out: dict[str, int] = {}
    for edge in graph.edges:
        if edge.kind != EDGE_REQUIRES:
            continue
        if edge.dst_namespace != NAMESPACE_CAPABILITY:
            continue
        out[edge.dst_slug] = out.get(edge.dst_slug, 0) + 1
    return out
