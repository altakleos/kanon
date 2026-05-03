"""Phase A.2.2: kanon_reference LOADER MANIFEST equivalence with the YAML source-of-truth.

Each LOADER stub at ``src/kanon_reference/aspects/kanon_<id>.py`` carries a
``MANIFEST: dict[str, Any]`` literal that mirrors the **union** of:

- the registry-level fields from ``kernel/kit/manifest.yaml``'s
  ``aspects.<id>:`` entry (``stability``, ``depth-range``, ``default-depth``,
  ``description``, ``requires``, ``provides``, optional ``suggests``); and
- the content fields from ``kernel/kit/aspects/<id>/manifest.yaml`` (``files``,
  ``depth-N``, optional ``byte-equality``, ``config-schema``, etc.).

The ``path:`` field from the top manifest is NOT included in the LOADER —
the substrate synthesizes it from the slug at registry-load time per Phase A.2.2.

This contract prevents drift while both YAML sources coexist; Phase A.3 deletes
the YAMLs and the LOADER stubs become canonical.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
KIT_ROOT = REPO_ROOT / "kernel" / "kit"
# Per substrate-content-move sub-plan: aspect data moved to
# src/kanon_reference/aspects/<slug>/. Top manifest stays at kit/.
KIT_ASPECTS = REPO_ROOT / "src" / "kanon_reference" / "aspects"

ASPECT_IDS = (
    "kanon-deps",
    "kanon-fidelity",
    "kanon-release",
    "kanon-sdd",
    "kanon-security",
    "kanon-testing",
    "kanon-worktrees",
)


@pytest.fixture(scope="module", autouse=True)
def _ensure_kanon_reference_importable():
    """Add ``src/`` to sys.path so the LOADER modules import without an installed wheel."""
    src = str(REPO_ROOT / "src")
    inserted = src not in sys.path
    if inserted:
        sys.path.insert(0, src)
    yield
    if inserted:
        sys.path.remove(src)


@pytest.fixture(scope="module")
def _top_manifest() -> dict:
    """The kit-global YAML manifest at kernel/kit/manifest.yaml."""
    return yaml.safe_load((KIT_ROOT / "manifest.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("aspect_id", ASPECT_IDS)
def test_loader_manifest_matches_union(aspect_id: str, _top_manifest: dict) -> None:
    """LOADER MANIFEST must equal {top-entry without path, **sub-manifest}."""
    sub_path = KIT_ASPECTS / aspect_id.replace("-", "_") / "manifest.yaml"
    assert sub_path.is_file(), f"missing sub-manifest source-of-truth: {sub_path}"
    sub_manifest = yaml.safe_load(sub_path.read_text(encoding="utf-8"))

    top_entry = dict(_top_manifest["aspects"][aspect_id])
    top_entry.pop("path", None)  # path: is synthesized by the substrate (Phase A.2.2)

    expected = {**top_entry, **sub_manifest}

    module_name = f"kanon_reference.aspects.{aspect_id.replace('-', '_')}.loader"
    module = importlib.import_module(module_name)
    manifest = getattr(module, "MANIFEST", None)
    assert manifest is not None, f"{module_name}: no MANIFEST attribute"

    assert manifest == expected, (
        f"{aspect_id}: MANIFEST ({module_name}) drifted from union of top "
        f"({KIT_ROOT}/manifest.yaml) + sub ({sub_path}).\n"
        f"expected: {expected!r}\nactual:   {manifest!r}"
    )


@pytest.mark.parametrize("aspect_id", ASPECT_IDS)
def test_loader_manifest_has_no_path_field(aspect_id: str) -> None:
    """LOADER MANIFEST must NOT contain a `path:` field — substrate synthesizes it."""
    module_name = f"kanon_reference.aspects.{aspect_id.replace('-', '_')}.loader"
    module = importlib.import_module(module_name)
    assert "path" not in module.MANIFEST, (
        f"{module_name}.MANIFEST: must not contain 'path:' field "
        f"(substrate synthesizes per Phase A.2.2 / ADR-0040)."
    )
