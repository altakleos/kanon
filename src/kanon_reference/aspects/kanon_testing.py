"""kanon-testing MANIFEST stub — Phase A.2.1 LOADER for the substrate's entry-point discovery.

Mirrors src/kanon/kit/aspects/kanon-testing/manifest.yaml byte-for-byte in semantic content
(modulo YAML→Python conversion). The duplication is short-lived: Phase A.3 deletes the
YAML and the LOADER stubs become the canonical shape.
"""

from typing import Any

MANIFEST: dict[str, Any] = {
    "kanon-dialect": "2026-05-01",
    "stability": "experimental",
    "depth-range": [0, 3],
    "default-depth": 1,
    "description": "Test discipline, AC-first TDD, error diagnosis",
    "requires": [],
    "suggests": ["kanon-sdd >= 1"],
    "provides": ["test-discipline"],
    "files": [],
    "depth-0": {"files": [], "protocols": [], "sections": []},
    "depth-1": {
        "files": [],
        "protocols": ["test-discipline.md", "error-diagnosis.md"],
        "sections": ["protocols-index"],
        # Phase A.4: preflight block retired — it depended on the removed
        # config-schema variables (${test_cmd}, ${lint_cmd}, etc.).
    },
    "depth-2": {
        "files": [],
        "protocols": ["ac-first-tdd.md"],
        "sections": [],
        "validators": ["kanon._validators.test_import_check"],
    },
    "depth-3": {
        # Phase A.8: scaffolded ci/check_test_quality.py retired
        # (per ADR-0048 de-opinionation).
        "files": [],
        "protocols": [],
        "sections": [],
    },
    # Phase A.4: config-schema retired (per ADR-0048 de-opinionation;
    # the substrate no longer reads test_cmd / lint_cmd / typecheck_cmd /
    # format_cmd / coverage_floor from kanon-testing's user-config block).
}
