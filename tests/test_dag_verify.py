"""Tests for DAG-driven verification engine (ADR-0061)."""
from __future__ import annotations

from pathlib import Path

import pytest

from kanon_core._change_detection import compute_node_hash, detect_changes, load_hash_store, save_hash_store
from kanon_core._dag_verify import (
    _EDGE_HANDLERS,
    _NODE_HANDLERS,
    _build_chains,
    _downstream_walk,
    format_findings,
    register_edge_handler,
    register_node_handler,
    run_dag_verify,
)
from kanon_core._findings import Finding
from kanon_core._graph import Edge, GraphData, Node
from kanon_core._handlers import (
    _legacy_node_adapter,
    handle_design_exists,
    handle_reference_live,
    handle_vision_coherence,
    register_all_handlers,
)

# -- Finding dataclass --

def test_finding_creation():
    f = Finding(severity="error", kind="test", source_slug="s", source_namespace="spec", message="msg")
    assert f.severity == "error"
    assert f.affected_slug is None
    assert f.chain == ()


def test_finding_is_frozen():
    f = Finding(severity="error", kind="test", source_slug="s", source_namespace="spec", message="msg")
    with pytest.raises(AttributeError):
        f.severity = "warning"  # type: ignore[misc]


# -- Change detection --

def test_compute_node_hash(tmp_path):
    p = tmp_path / "test.md"
    p.write_text("hello")
    h = compute_node_hash(p)
    assert isinstance(h, str) and len(h) == 64


def test_hash_store_round_trip(tmp_path):
    kanon_dir = tmp_path / ".kanon"
    kanon_dir.mkdir()
    save_hash_store(kanon_dir, {"spec/cli": "abc123"})
    assert load_hash_store(kanon_dir) == {"spec/cli": "abc123"}


def test_load_hash_store_missing(tmp_path):
    assert load_hash_store(tmp_path / ".kanon") == {}


def test_detect_changes_changed(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("v1")
    node = Node(slug="a", namespace="spec", path=Path("a.md"), status=None)
    store: dict[str, str] = {}
    changed = detect_changes([node], tmp_path, store)
    assert ("spec", "a") in changed
    assert "spec/a" in store


def test_detect_changes_unchanged(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("v1")
    node = Node(slug="a", namespace="spec", path=Path("a.md"), status=None)
    store: dict[str, str] = {"spec/a": compute_node_hash(p)}
    changed = detect_changes([node], tmp_path, store)
    assert changed == set()


# -- DAG engine --

@pytest.fixture(autouse=True)
def _clear_handlers():
    """Reset global handler tables between tests."""
    _NODE_HANDLERS.clear()
    _EDGE_HANDLERS.clear()
    yield
    _NODE_HANDLERS.clear()
    _EDGE_HANDLERS.clear()


def test_register_node_handler():
    def handler(node, target, findings):
        pass
    register_node_handler("spec", handler)
    assert handler in _NODE_HANDLERS["spec"]


def test_register_edge_handler():
    def handler(edge, src, dst, target, findings):
        pass
    register_edge_handler("realizes", handler)
    assert handler in _EDGE_HANDLERS["realizes"]


def test_run_dag_verify_simple(tmp_path):
    """A single node with a registered handler produces findings."""
    p = tmp_path / "a.md"
    p.write_text("content")
    node = Node(slug="a", namespace="spec", path=Path("a.md"), status=None)
    graph = GraphData(
        nodes=[node], edges=[],
        by_slug={("spec", "a"): node},
        inbound_all={}, inbound_live={},
    )

    def handler(n, target, findings):
        findings.append(Finding(
            severity="error", kind="t",
            source_slug=n.slug, source_namespace=n.namespace, message="bad",
        ))

    register_node_handler("spec", handler)
    findings = run_dag_verify(tmp_path, graph, full=True)
    assert len(findings) == 1 and findings[0].message == "bad"


# -- Legacy adapter --

def test_legacy_node_adapter():
    def legacy_check(target, errors, warnings):
        errors.append("e1")
        warnings.append("w1")

    node = Node(slug="x", namespace="spec", path=Path("x.md"), status=None)
    findings: list[Finding] = []
    _legacy_node_adapter(legacy_check, node, Path("."), findings)
    assert len(findings) == 2
    assert findings[0].severity == "error" and findings[0].message == "e1"
    assert findings[1].severity == "warning" and findings[1].message == "w1"


# -- format_findings --

def test_format_findings_splits_by_severity():
    findings = [
        Finding(severity="error", kind="a", source_slug="s", source_namespace="spec", message="err1"),
        Finding(severity="warning", kind="b", source_slug="s", source_namespace="spec", message="warn1"),
        Finding(severity="error", kind="c", source_slug="s", source_namespace="spec", message="err2"),
    ]
    errors, warnings = format_findings(findings)
    assert errors == ["err1", "err2"]
    assert warnings == ["warn1"]


# -- _findings.py: optional fields & equality --

def test_finding_all_optional_fields():
    f = Finding(severity="warning", kind="k", source_slug="s", source_namespace="spec",
                message="m", affected_slug="a", affected_namespace="design", chain=("spec/s",))
    assert f.affected_slug == "a" and f.affected_namespace == "design" and f.chain == ("spec/s",)


def test_finding_equality():
    args = dict(severity="error", kind="k", source_slug="s", source_namespace="spec", message="m")
    assert Finding(**args) == Finding(**args)
    assert Finding(**args) != Finding(**{**args, "message": "other"})


# -- _change_detection.py: edge cases --

def test_detect_changes_no_path(tmp_path):
    node = Node(slug="a", namespace="spec", path=None, status=None)
    assert detect_changes([node], tmp_path, {}) == set()


def test_detect_changes_missing_file(tmp_path):
    node = Node(slug="a", namespace="spec", path=Path("gone.md"), status=None)
    assert detect_changes([node], tmp_path, {}) == set()


def test_save_hash_store_creates_parent(tmp_path):
    deep = tmp_path / "a" / "b" / ".kanon"
    save_hash_store(deep, {"k": "v"})
    assert load_hash_store(deep) == {"k": "v"}


# -- _dag_verify.py: downstream walk & build_chains --


def _make_graph(nodes, edges):
    by_slug = {(n.namespace, n.slug): n for n in nodes}
    inbound_all: dict[tuple[str, str], list] = {}
    for e in edges:
        key = (e.dst_namespace, e.dst_slug) if e.dst_namespace else None
        if key:
            inbound_all.setdefault(key, []).append(e)
    return GraphData(nodes=nodes, edges=edges, by_slug=by_slug,
                     inbound_all=inbound_all, inbound_live={})


def test_downstream_walk_no_seeds():
    g = _make_graph([], [])
    assert _downstream_walk(set(), g) == []


def test_downstream_walk_multiple_seeds():
    n1 = Node(slug="a", namespace="spec", path=Path("a.md"), status=None)
    n2 = Node(slug="b", namespace="spec", path=Path("b.md"), status=None)
    g = _make_graph([n1, n2], [])
    result = _downstream_walk({("spec", "a"), ("spec", "b")}, g)
    assert set(result) == {("spec", "a"), ("spec", "b")}


def test_build_chains_groups_by_root():
    f1 = Finding(severity="error", kind="k", source_slug="a", source_namespace="spec",
                 message="m1", chain=("spec/root",))
    f2 = Finding(severity="error", kind="k", source_slug="b", source_namespace="spec",
                 message="m2", chain=("spec/root",))
    standalone_f = Finding(severity="warning", kind="k", source_slug="c",
                           source_namespace="spec", message="m3")
    chains, standalone = _build_chains([f1, f2, standalone_f], _make_graph([], []))
    assert len(chains) == 1 and len(chains[0]) == 2
    assert standalone == [standalone_f]


# -- run_dag_verify: incremental & empty --

def test_run_dag_verify_incremental_no_changes(tmp_path):
    """Incremental mode with unchanged files returns empty."""
    p = tmp_path / "a.md"
    p.write_text("v1")
    kanon_dir = tmp_path / ".kanon"
    kanon_dir.mkdir()
    node = Node(slug="a", namespace="spec", path=Path("a.md"), status=None)
    # Pre-populate hash store so nothing is changed
    save_hash_store(kanon_dir, {"spec/a": compute_node_hash(p)})
    graph = GraphData(nodes=[node], edges=[], by_slug={("spec", "a"): node},
                      inbound_all={}, inbound_live={})
    register_node_handler("spec", lambda n, t, f: f.append(
        Finding(severity="error", kind="t", source_slug=n.slug,
                source_namespace=n.namespace, message="should not fire")))
    assert run_dag_verify(tmp_path, graph, full=False) == []


def test_run_dag_verify_no_nodes():
    """Empty graph returns empty findings."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        graph = GraphData(nodes=[], edges=[], by_slug={}, inbound_all={}, inbound_live={})
        assert run_dag_verify(Path(td), graph, full=True) == []


# -- _handlers.py: register_all_handlers & edge adapters --


def test_register_all_handlers_populates_tables():
    register_all_handlers()
    assert len(_NODE_HANDLERS) > 0
    assert len(_EDGE_HANDLERS) > 0
    assert "derived_from" in _EDGE_HANDLERS
    assert "realizes" in _EDGE_HANDLERS


def test_handle_vision_coherence_adapter(monkeypatch):
    """Edge handler produces findings with affected_slug set."""
    monkeypatch.setattr("kanon_core._handlers.handle_vision_coherence.__module__",
                        "kanon_core._handlers", raising=False)
    import kanon_core._validators.foundations_coherence as mod
    monkeypatch.setattr(mod, "check", lambda t, e, w: e.append("coherence fail"))
    src = Node(slug="v", namespace="spec", path=Path("v.md"), status=None)
    dst = Node(slug="p", namespace="principle", path=Path("p.md"), status=None)
    edge = Edge(src_slug="v", src_namespace="spec", dst_slug="p", dst_namespace="principle", kind="derived_from")
    findings: list[Finding] = []
    handle_vision_coherence(edge, src, dst, Path("."), findings)
    assert len(findings) == 1
    assert findings[0].affected_slug == "p" and findings[0].kind == "vision-coherence"


def test_handle_reference_live_adapter(monkeypatch):
    import kanon_core._validators.foundations_impact as mod
    monkeypatch.setattr(mod, "check", lambda t, e, w: w.append("stale ref"))
    src = Node(slug="s", namespace="spec", path=Path("s.md"), status=None)
    dst = Node(slug="d", namespace="design", path=Path("d.md"), status=None)
    edge = Edge(src_slug="s", src_namespace="spec", dst_slug="d", dst_namespace="design", kind="realizes")
    findings: list[Finding] = []
    handle_reference_live(edge, src, dst, Path("."), findings)
    assert findings[0].kind == "stale-reference" and findings[0].affected_slug == "d"


def test_handle_design_exists_adapter(monkeypatch):
    import kanon_core._validators.spec_design_parity as mod
    monkeypatch.setattr(mod, "check", lambda t, e, w: w.append("no design"))
    src = Node(slug="s", namespace="spec", path=Path("s.md"), status=None)
    edge = Edge(src_slug="s", src_namespace="spec", dst_slug="d", dst_namespace="design", kind="realizes")
    findings: list[Finding] = []
    handle_design_exists(edge, src, None, Path("."), findings)
    assert findings[0].kind == "missing-design" and findings[0].affected_slug is None
