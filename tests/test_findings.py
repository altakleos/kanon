"""Tests for kanon_core._findings module."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from kanon_core._findings import Finding


def test_finding_is_frozen() -> None:
    f = Finding(severity="error", kind="missing", source_slug="s", source_namespace="ns", message="msg")
    with pytest.raises(FrozenInstanceError):
        f.severity = "warning"  # type: ignore[misc]


def test_finding_fields_accessible() -> None:
    f = Finding(
        severity="warning",
        kind="drift",
        source_slug="slug1",
        source_namespace="ns1",
        message="oops",
        affected_slug="slug2",
        affected_namespace="ns2",
        chain=("a", "b"),
    )
    assert f.severity == "warning"
    assert f.kind == "drift"
    assert f.source_slug == "slug1"
    assert f.source_namespace == "ns1"
    assert f.message == "oops"
    assert f.affected_slug == "slug2"
    assert f.affected_namespace == "ns2"
    assert f.chain == ("a", "b")


def test_node_handler_protocol() -> None:
    """A callable matching NodeHandler signature works."""
    findings: list[Finding] = []

    def handler(node: object, target: Path, findings: list[Finding]) -> None:
        findings.append(
            Finding(severity="error", kind="test", source_slug="s", source_namespace="ns", message="hi")
        )

    handler(object(), Path("."), findings)
    assert len(findings) == 1


def test_edge_handler_protocol() -> None:
    """A callable matching EdgeHandler signature works."""
    findings: list[Finding] = []

    def handler(edge: object, src_node: object, dst_node: object, target: Path, findings: list[Finding]) -> None:
        findings.append(
            Finding(severity="warning", kind="edge", source_slug="e", source_namespace="ns", message="edge")
        )

    handler(object(), object(), object(), Path("."), findings)
    assert len(findings) == 1
