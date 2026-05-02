"""kanon-worktrees MANIFEST stub — Phase A.2.1 LOADER for the substrate's entry-point discovery.

Mirrors src/kanon/kit/aspects/kanon-worktrees/manifest.yaml byte-for-byte in semantic content
(modulo YAML→Python conversion). The duplication is short-lived: Phase A.3 deletes the
YAML and the LOADER stubs become the canonical shape.
"""

from typing import Any

MANIFEST: dict[str, Any] = {
    "kanon-dialect": "2026-05-01",
    "stability": "experimental",
    "depth-range": [0, 2],
    "default-depth": 1,
    "description": "Worktree isolation for parallel work",
    "requires": [],
    "suggests": ["kanon-sdd >= 1"],
    "provides": ["worktree-isolation"],
    "files": [],
    "depth-0": {"files": [], "protocols": [], "sections": []},
    "depth-1": {
        "files": [],
        "protocols": ["worktree-lifecycle.md", "branch-hygiene.md"],
        "sections": ["protocols-index"],
    },
    "depth-2": {
        "files": [
            "scripts/worktree-setup.sh",
            "scripts/worktree-teardown.sh",
            "scripts/worktree-status.sh",
        ],
        "protocols": [],
        "sections": [],
    },
}
