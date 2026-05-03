"""kanon-sdd MANIFEST stub — Phase A.2.1 LOADER for the substrate's entry-point discovery.

Mirrors src/kanon_reference/aspects/kanon_sdd/manifest.yaml byte-for-byte in semantic content
(modulo YAML→Python conversion). The duplication is short-lived: Phase A.3 deletes the
YAML and the LOADER stubs become the canonical shape.
"""

from typing import Any

MANIFEST: dict[str, Any] = {
    "kanon-dialect": "2026-05-01",
    "stability": "stable",
    "depth-range": [0, 3],
    "default-depth": 1,
    "description": "Spec-Driven Development: plans, specs, design docs",
    "requires": [],
    "provides": ["planning-discipline", "spec-discipline"],
    "byte-equality": [
        {"kit": "docs/sdd-method.md", "repo": "docs/sdd-method.md"},
        {"kit": "docs/decisions/_template.md", "repo": "docs/decisions/_template.md"},
        {"kit": "docs/plans/_template.md", "repo": "docs/plans/_template.md"},
        {"kit": "docs/specs/_template.md", "repo": "docs/specs/_template.md"},
        {"kit": "docs/design/_template.md", "repo": "docs/design/_template.md"},
    ],
    "files": [],
    "depth-0": {"files": [], "protocols": [], "sections": []},
    "depth-1": {
        "files": [
            "docs/sdd-method.md",
            "docs/decisions/README.md",
            "docs/decisions/_template.md",
            "docs/plans/README.md",
            "docs/plans/_template.md",
        ],
        "protocols": [
            "tier-up-advisor.md",
            "verify-triage.md",
            "completion-checklist.md",
            "scope-check.md",
            "plan-before-build.md",
        ],
        "sections": ["protocols-index"],
        "validators": [
            "kanon_core._validators.plan_completion",
            "kanon_core._validators.index_consistency",
        ],
    },
    "depth-2": {
        "files": ["docs/specs/README.md", "docs/specs/_template.md"],
        "protocols": ["spec-review.md", "spec-before-design.md"],
        "sections": None,
        "validators": [
            "kanon_core._validators.link_check",
            "kanon_core._validators.adr_immutability",
        ],
    },
    "depth-3": {
        "files": [
            "docs/design/README.md",
            "docs/design/_template.md",
            "docs/foundations/README.md",
            "docs/foundations/vision.md",
            "docs/foundations/principles/README.md",
            "docs/foundations/personas/README.md",
        ],
        "protocols": ["adr-immutability.md"],
        "sections": [],
        "validators": ["kanon_core._validators.spec_design_parity"],
    },
}
