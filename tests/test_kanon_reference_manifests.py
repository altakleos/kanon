"""ADR-0055: verify each kanon-* aspect's LOADER MANIFEST (entry-point) is a
self-contained dict with all required registry + content keys.

The LOADER now reads sibling manifest.yaml via importlib.resources; this test
confirms the round-trip produces a valid unified manifest.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

ASPECT_IDS = (
    "kanon-deps",
    "kanon-fidelity",
    "kanon-release",
    "kanon-sdd",
    "kanon-security",
    "kanon-testing",
    "kanon-worktrees",
)

REQUIRED_KEYS = {"stability", "depth-range", "default-depth", "description", "kanon-dialect"}


@pytest.fixture(scope="module", autouse=True)
def _ensure_kanon_aspects_importable():
    """Add ``packages/kanon-aspects/src/`` to sys.path so the LOADER modules import without an installed wheel."""
    src = str(REPO_ROOT / "packages" / "kanon-aspects" / "src")
    inserted = src not in sys.path
    if inserted:
        sys.path.insert(0, src)
    yield
    if inserted:
        sys.path.remove(src)


@pytest.mark.parametrize("aspect_id", ASPECT_IDS)
def test_loader_manifest_has_required_keys(aspect_id: str) -> None:
    """LOADER MANIFEST must contain all required registry + at least one depth-N key."""
    module_name = f"kanon_aspects.aspects.{aspect_id.replace('-', '_')}.loader"
    # Force reimport to pick up YAML changes in this worktree.
    if module_name in sys.modules:
        del sys.modules[module_name]
    module = importlib.import_module(module_name)
    manifest = getattr(module, "MANIFEST", None)
    assert manifest is not None, f"{module_name}: no MANIFEST attribute"
    assert isinstance(manifest, dict), f"{module_name}: MANIFEST must be a dict"

    missing = REQUIRED_KEYS - set(manifest)
    assert not missing, f"{module_name}: MANIFEST missing required keys: {sorted(missing)}"

    # Must have at least depth-0
    depth_keys = [k for k in manifest if k.startswith("depth-")]
    assert depth_keys, f"{module_name}: MANIFEST has no depth-N entries"


@pytest.mark.parametrize("aspect_id", ASPECT_IDS)
def test_loader_manifest_has_no_path_field(aspect_id: str) -> None:
    """LOADER MANIFEST must NOT contain a `path:` field — substrate synthesizes it."""
    module_name = f"kanon_aspects.aspects.{aspect_id.replace('-', '_')}.loader"
    if module_name in sys.modules:
        del sys.modules[module_name]
    module = importlib.import_module(module_name)
    assert "path" not in module.MANIFEST, (
        f"{module_name}.MANIFEST: must not contain 'path:' field "
        f"(substrate synthesizes per Phase A.2.2 / ADR-0040)."
    )
