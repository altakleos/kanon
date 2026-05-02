"""kanon-release MANIFEST stub — Phase A.2.1 LOADER for the substrate's entry-point discovery.

Mirrors src/kanon/kit/aspects/kanon-release/manifest.yaml byte-for-byte in semantic content
(modulo YAML→Python conversion). The duplication is short-lived: Phase A.3 deletes the
YAML and the LOADER stubs become the canonical shape.
"""

from typing import Any

MANIFEST: dict[str, Any] = {
    "files": [],
    "depth-0": {"files": [], "protocols": [], "sections": []},
    "depth-1": {
        "files": [],
        "protocols": ["release-checklist.md", "publishing-discipline.md"],
        "sections": ["protocols-index"],
    },
    "depth-2": {
        "files": ["ci/release-preflight.py", ".github/workflows/release.yml"],
        "protocols": [],
        "sections": [],
        "preflight": {
            "release": [
                {
                    "run": "python ci/release-preflight.py --tag $TAG",
                    "label": "release-preflight",
                },
            ],
        },
    },
}
