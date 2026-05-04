"""kanon-release MANIFEST stub — Phase A.2.1 LOADER for the substrate's entry-point discovery.

Mirrors packages/kanon-aspects/src/kanon_aspects/aspects/kanon_release/manifest.yaml byte-for-byte in semantic content
(modulo YAML→Python conversion). The duplication is short-lived: Phase A.3 deletes the
YAML and the LOADER stubs become the canonical shape.
"""

from typing import Any

MANIFEST: dict[str, Any] = {
    "kanon-dialect": "2026-05-01",
    "stability": "experimental",
    "depth-range": [0, 2],
    "default-depth": 1,
    "description": "Release checklist, preflight, and CLI gate",
    "requires": [],
    "provides": ["release-discipline"],
    "files": [],
    "depth-0": {"files": [], "protocols": [], "sections": []},
    "depth-1": {
        "files": [],
        "protocols": ["release-checklist.md", "publishing-discipline.md"],
        "sections": ["protocols-index"],
    },
    "depth-2": {
        # Phase A.8: scaffolded ci/release-preflight.py +
        # .github/workflows/release.yml + preflight wiring retired (per ADR-0048
        # de-opinionation; substrate no longer ships consumer-side CI scripts
        # nor GitHub-Actions workflow files).
        "files": [],
        "protocols": [],
        "sections": [],
    },
}
