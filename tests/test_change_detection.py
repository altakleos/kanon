"""Tests for kanon_core._change_detection module."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from kanon_core._change_detection import (
    compute_node_hash,
    detect_changes,
    load_hash_store,
    save_hash_store,
)


def test_compute_node_hash_consistent(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_text("hello")
    assert compute_node_hash(f) == compute_node_hash(f)


def test_compute_node_hash_is_sha256(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_text("hello")
    h = compute_node_hash(f)
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)


def test_load_hash_store_missing(tmp_path: Path) -> None:
    assert load_hash_store(tmp_path) == {}


def test_load_hash_store_existing(tmp_path: Path) -> None:
    (tmp_path / "verify-hashes.json").write_text(json.dumps({"k": "v"}))
    assert load_hash_store(tmp_path) == {"k": "v"}


def test_save_hash_store_writes_json(tmp_path: Path) -> None:
    save_hash_store(tmp_path, {"a": "b"})
    data = json.loads((tmp_path / "verify-hashes.json").read_text())
    assert data == {"a": "b"}


def test_detect_changes_new_file(tmp_path: Path) -> None:
    (tmp_path / "f.md").write_text("content")
    node = SimpleNamespace(path="f.md", namespace="ns", slug="s")
    store: dict[str, str] = {}
    changed = detect_changes([node], tmp_path, store)
    assert ("ns", "s") in changed


def test_detect_changes_modified_file(tmp_path: Path) -> None:
    (tmp_path / "f.md").write_text("new content")
    node = SimpleNamespace(path="f.md", namespace="ns", slug="s")
    store = {"ns/s": "oldhash"}
    changed = detect_changes([node], tmp_path, store)
    assert ("ns", "s") in changed


def test_detect_changes_unchanged(tmp_path: Path) -> None:
    (tmp_path / "f.md").write_text("same")
    node = SimpleNamespace(path="f.md", namespace="ns", slug="s")
    store: dict[str, str] = {}
    # First pass populates store
    detect_changes([node], tmp_path, store)
    # Second pass — no change
    changed = detect_changes([node], tmp_path, store)
    assert changed == set()


def test_detect_changes_updates_store_in_place(tmp_path: Path) -> None:
    (tmp_path / "f.md").write_text("x")
    node = SimpleNamespace(path="f.md", namespace="ns", slug="s")
    store: dict[str, str] = {}
    detect_changes([node], tmp_path, store)
    assert "ns/s" in store
