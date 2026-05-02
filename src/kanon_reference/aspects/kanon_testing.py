"""kanon-testing MANIFEST stub — Phase A.2.1 LOADER for the substrate's entry-point discovery.

Mirrors src/kanon/kit/aspects/kanon-testing/manifest.yaml byte-for-byte in semantic content
(modulo YAML→Python conversion). The duplication is short-lived: Phase A.3 deletes the
YAML and the LOADER stubs become the canonical shape.
"""

from typing import Any

MANIFEST: dict[str, Any] = {
    "files": [],
    "depth-0": {"files": [], "protocols": [], "sections": []},
    "depth-1": {
        "files": [],
        "protocols": ["test-discipline.md", "error-diagnosis.md"],
        "sections": ["protocols-index"],
        "preflight": {
            "commit": [
                {"run": "${lint_cmd}", "label": "lint"},
                {"run": "${format_cmd}", "label": "format"},
            ],
            "push": [
                {"run": "${test_cmd}", "label": "tests"},
                {"run": "${typecheck_cmd}", "label": "typecheck"},
            ],
        },
    },
    "depth-2": {
        "files": [],
        "protocols": ["ac-first-tdd.md"],
        "sections": [],
        "validators": ["kanon._validators.test_import_check"],
    },
    "depth-3": {
        "files": ["ci/check_test_quality.py"],
        "protocols": [],
        "sections": [],
    },
    "config-schema": {
        "coverage_floor": {
            "type": "integer",
            "default": 80,
            "description": (
                "Advisory minimum total test-coverage percentage. The kit declares "
                "this value but does not auto-wire it into a test runner; consumers "
                "feed it into their own CI (e.g., `pytest --cov-fail-under`) to "
                "enforce the threshold."
            ),
        },
        "test_cmd": {
            "type": "string",
            "default": "",
            "description": "Test suite command (e.g., pytest -q, npm test, cargo test).",
        },
        "lint_cmd": {
            "type": "string",
            "default": "",
            "description": "Lint command (e.g., ruff check ., eslint ., cargo clippy).",
        },
        "typecheck_cmd": {
            "type": "string",
            "default": "",
            "description": "Type check command (e.g., mypy src/, tsc --noEmit).",
        },
        "format_cmd": {
            "type": "string",
            "default": "",
            "description": "Format check command (e.g., ruff format --check ., prettier --check .).",
        },
    },
}
