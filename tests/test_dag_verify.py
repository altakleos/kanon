"""Tests for DAG-driven verification engine (ADR-0061)."""
from __future__ import annotations

from pathlib import Path

import pytest

from kanon_core._findings import Finding
from kanon_core._change_detection import compute_node_hash, detect_changes, load_hash_store, save_hash_store
from kanon_core._dag_verify import format_findings, run_dag_verify, _NODE_HANDLERS, _EDGE_HANDLERS, register_node_handler, register_edge_handler
from kanon_core._graph import GraphData, Node, Edge
from kanon_core._handlers import _legacy_node_adapter


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
    handler = lambda node, target, findings: None
    register_node_handler("spec", handler)
    assert handler in _NODE_HANDLERS["spec"]


def test_register_edge_handler():
    handler = lambda edge, src, dst, target, findings: None
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
        findings.append(Finding(severity="error", kind="t", source_slug=n.slug, source_namespace=n.namespace, message="bad"))

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
