"""Hash-based change detection for DAG-driven verification (ADR-0061)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def compute_node_hash(path: Path) -> str:
    """SHA-256 of a file's content."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_hash_store(kanon_dir: Path) -> dict[str, str]:
    """Load stored hashes from .kanon/verify-hashes.json."""
    path = kanon_dir / "verify-hashes.json"
    if not path.is_file():
        return {}
    result: dict[str, str] = json.loads(path.read_text("utf-8"))
    return result


def save_hash_store(kanon_dir: Path, store: dict[str, str]) -> None:
    """Save hashes to .kanon/verify-hashes.json."""
    path = kanon_dir / "verify-hashes.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def detect_changes(
    nodes: list[Any], target: Path, store: dict[str, str],
) -> set[tuple[str, str]]:
    """Return set of (namespace, slug) for nodes whose content hash changed."""
    changed: set[tuple[str, str]] = set()
    for node in nodes:
        if node.path is None:
            continue
        abs_path = target / node.path
        if not abs_path.is_file():
            continue
        key = f"{node.namespace}/{node.slug}"
        current_hash = compute_node_hash(abs_path)
        if store.get(key) != current_hash:
            changed.add((node.namespace, node.slug))
        store[key] = current_hash
    return changed
