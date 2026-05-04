"""DAG handler registrations — adapts existing validators to the DAG engine (ADR-0061)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from kanon_core._dag_verify import register_edge_handler, register_node_handler
from kanon_core._findings import Finding

# -- Adapter: wraps a legacy check() validator as a node handler --

def _legacy_node_adapter(check_fn: Any, node: Any, target: Path, findings: list[Finding]) -> None:
    """Run a legacy check(target, errors, warnings) and convert output to Findings."""
    errors: list[str] = []
    warnings: list[str] = []
    check_fn(target, errors, warnings)
    for msg in errors:
        findings.append(Finding(
            severity="error", kind="legacy",
            source_slug=node.slug, source_namespace=node.namespace,
            message=msg,
        ))
    for msg in warnings:
        findings.append(Finding(
            severity="warning", kind="legacy",
            source_slug=node.slug, source_namespace=node.namespace,
            message=msg,
        ))


# -- Node handlers (property checks on individual artifacts) --

def handle_plan_completion(node: Any, target: Path, findings: list[Finding]) -> None:
    """Check plan checkbox completion."""
    from kanon_core._validators.plan_completion import check
    _legacy_node_adapter(check, node, target, findings)


def handle_index_consistency(node: Any, target: Path, findings: list[Finding]) -> None:
    """Check index README for duplicate entries."""
    from kanon_core._validators.index_consistency import check
    _legacy_node_adapter(check, node, target, findings)


def handle_link_check(node: Any, target: Path, findings: list[Finding]) -> None:
    """Validate relative markdown links."""
    from kanon_core._validators.link_check import check
    _legacy_node_adapter(check, node, target, findings)


def handle_adr_immutability(node: Any, target: Path, findings: list[Finding]) -> None:
    """Check ADR body immutability."""
    from kanon_core._validators.adr_immutability import check
    _legacy_node_adapter(check, node, target, findings)


# -- Edge handlers (relationship checks between artifacts) --

def handle_vision_coherence(edge: Any, src_node: Any, dst_node: Any, target: Path, findings: list[Finding]) -> None:
    """Check vision→principle coherence."""
    from kanon_core._validators.foundations_coherence import check
    errors: list[str] = []
    warnings: list[str] = []
    check(target, errors, warnings)
    for msg in errors:
        findings.append(Finding(
            severity="error", kind="vision-coherence",
            source_slug=src_node.slug, source_namespace=src_node.namespace,
            affected_slug=dst_node.slug if dst_node else None,
            affected_namespace=dst_node.namespace if dst_node else None,
            message=msg,
        ))
    for msg in warnings:
        findings.append(Finding(
            severity="warning", kind="vision-coherence",
            source_slug=src_node.slug, source_namespace=src_node.namespace,
            affected_slug=dst_node.slug if dst_node else None,
            affected_namespace=dst_node.namespace if dst_node else None,
            message=msg,
        ))


def handle_reference_live(edge: Any, src_node: Any, dst_node: Any, target: Path, findings: list[Finding]) -> None:
    """Check that realizes:/stressed_by: targets are not superseded."""
    from kanon_core._validators.foundations_impact import check
    errors: list[str] = []
    warnings: list[str] = []
    check(target, errors, warnings)
    for msg in warnings:
        findings.append(Finding(
            severity="warning", kind="stale-reference",
            source_slug=src_node.slug, source_namespace=src_node.namespace,
            affected_slug=dst_node.slug if dst_node else None,
            affected_namespace=dst_node.namespace if dst_node else None,
            message=msg,
        ))


def handle_design_exists(edge: Any, src_node: Any, dst_node: Any, target: Path, findings: list[Finding]) -> None:
    """Check that accepted specs have companion design docs."""
    from kanon_core._validators.spec_design_parity import check
    errors: list[str] = []
    warnings: list[str] = []
    check(target, errors, warnings)
    for msg in warnings:
        findings.append(Finding(
            severity="warning", kind="missing-design",
            source_slug=src_node.slug, source_namespace=src_node.namespace,
            message=msg,
        ))


# -- Registration --

def register_all_handlers() -> None:
    """Register all built-in handlers with the DAG engine."""
    # Node handlers
    register_node_handler("plan", handle_plan_completion)
    register_node_handler("spec", handle_link_check)
    register_node_handler("principle", handle_link_check)
    register_node_handler("persona", handle_link_check)
    register_node_handler("spec", handle_index_consistency)
    register_node_handler("spec", handle_adr_immutability)

    # Edge handlers
    register_edge_handler("derived_from", handle_vision_coherence)
    register_edge_handler("realizes", handle_reference_live)
    register_edge_handler("stressed_by", handle_reference_live)
    register_edge_handler("realizes", handle_design_exists)

