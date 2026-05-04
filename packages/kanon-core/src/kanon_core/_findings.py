"""Structured verification findings for DAG-driven verification (ADR-0061)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol


@dataclass(frozen=True)
class Finding:
    """A single verification finding with impact-chain context."""
    severity: Literal["error", "warning"]
    kind: str
    source_slug: str
    source_namespace: str
    message: str
    affected_slug: str | None = None
    affected_namespace: str | None = None
    chain: tuple[str, ...] = ()


class NodeHandler(Protocol):
    """Handler for node-level property checks."""
    def __call__(
        self, node: object, target: Path, findings: list[Finding],
    ) -> None: ...


class EdgeHandler(Protocol):
    """Handler for edge-level relationship checks."""
    def __call__(
        self, edge: object, src_node: object, dst_node: object,
        target: Path, findings: list[Finding],
    ) -> None: ...
