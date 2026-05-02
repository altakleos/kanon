"""kanon-deps MANIFEST stub — Phase A.2.1 LOADER for the substrate's entry-point discovery.

Mirrors src/kanon_reference/aspects/kanon_deps/manifest.yaml byte-for-byte in semantic content
(modulo YAML→Python conversion). The duplication is short-lived: Phase A.3 deletes the
YAML and the LOADER stubs become the canonical shape.
"""

from typing import Any

MANIFEST: dict[str, Any] = {
    "kanon-dialect": "2026-05-01",
    "stability": "experimental",
    "depth-range": [0, 2],
    "default-depth": 1,
    "description": "Dependency hygiene and CI scanner",
    "requires": [],
    "provides": ["dependency-hygiene"],
    "files": [],
    "depth-0": {"files": [], "protocols": [], "sections": []},
    "depth-1": {
        "files": [],
        "protocols": ["dependency-hygiene.md"],
        "sections": ["protocols-index"],
    },
    "depth-2": {
        # Phase A.8: scaffolded ci/check_deps.py + preflight wiring retired
        # (per ADR-0048 de-opinionation; substrate no longer ships consumer-side
        # CI scripts).
        "files": [],
        "protocols": [],
        "sections": [],
    },
}
