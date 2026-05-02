"""kanon-fidelity MANIFEST stub — Phase A.2.1 LOADER for the substrate's entry-point discovery.

Mirrors src/kanon_reference/aspects/kanon_fidelity/manifest.yaml byte-for-byte in semantic content
(modulo YAML→Python conversion). The duplication is short-lived: Phase A.3 deletes the
YAML and the LOADER stubs become the canonical shape.
"""

from typing import Any

MANIFEST: dict[str, Any] = {
    "kanon-dialect": "2026-05-01",
    "stability": "experimental",
    "depth-range": [0, 1],
    "default-depth": 1,
    "description": "Behavioural conformance via lexical assertions",
    "requires": [],
    "provides": ["behavioural-verification"],
    "files": [],
    "depth-0": {"files": [], "protocols": [], "sections": []},
    "depth-1": {
        "files": [],
        "protocols": ["fidelity-fixture-authoring.md", "fidelity-discipline.md"],
        "sections": None,
    },
}
