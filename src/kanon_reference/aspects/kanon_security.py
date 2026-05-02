"""kanon-security MANIFEST stub — Phase A.2.1 LOADER for the substrate's entry-point discovery.

Mirrors src/kanon/kit/aspects/kanon-security/manifest.yaml byte-for-byte in semantic content
(modulo YAML→Python conversion). The duplication is short-lived: Phase A.3 deletes the
YAML and the LOADER stubs become the canonical shape.
"""

from typing import Any

MANIFEST: dict[str, Any] = {
    "stability": "experimental",
    "depth-range": [0, 2],
    "default-depth": 1,
    "description": "Secure-by-default protocols and CI scanner",
    "requires": [],
    "provides": ["security-discipline"],
    "files": [],
    "depth-0": {"files": [], "protocols": [], "sections": []},
    "depth-1": {
        "files": [],
        "protocols": ["secure-defaults.md"],
        "sections": ["protocols-index"],
    },
    "depth-2": {
        "files": ["ci/check_security_patterns.py"],
        "protocols": [],
        "sections": [],
        "preflight": {
            "push": [
                {"run": "python ci/check_security_patterns.py", "label": "security-scan"},
            ],
        },
    },
}
