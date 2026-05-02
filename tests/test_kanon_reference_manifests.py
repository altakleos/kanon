"""Phase A.2.1: kanon_reference LOADER MANIFEST equivalence with the YAML source-of-truth.

Each LOADER stub at ``src/kanon_reference/aspects/kanon_<id>.py`` carries a
``MANIFEST: dict[str, Any]`` literal that mirrors the corresponding
``src/kanon/kit/aspects/kanon-<id>/manifest.yaml`` byte-for-byte (modulo YAML→Python
conversion). This contract prevents drift while both sources coexist; Phase A.3
deletes the YAML and the LOADER stubs become canonical.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
KIT_ASPECTS = REPO_ROOT / "src" / "kanon" / "kit" / "aspects"

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


@pytest.mark.parametrize("aspect_id", ASPECT_IDS)
def test_loader_manifest_matches_yaml(aspect_id: str) -> None:
    """LOADER MANIFEST must equal the YAML manifest parsed via yaml.safe_load."""
    yaml_path = KIT_ASPECTS / aspect_id / "manifest.yaml"
    assert yaml_path.is_file(), f"missing source-of-truth: {yaml_path}"
    yaml_data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    module_name = f"kanon_reference.aspects.{aspect_id.replace('-', '_')}"
    module = importlib.import_module(module_name)
    manifest = getattr(module, "MANIFEST", None)
    assert manifest is not None, f"{module_name}: no MANIFEST attribute"

    assert manifest == yaml_data, (
        f"{aspect_id}: MANIFEST ({module_name}) drifted from YAML ({yaml_path}).\n"
        f"YAML: {yaml_data!r}\nMANIFEST: {manifest!r}"
    )
