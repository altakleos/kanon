"""Tests for declarative hard gates (docs/specs/declarative-hard-gates.md)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import click
import pytest

from kanon_core._scaffold import _render_hard_gates


def _write_protocol(tmp_path: Path, filename: str, content: str) -> Path:
    """Write a protocol file under a mock aspect structure."""
    proto_dir = tmp_path / "protocols"
    proto_dir.mkdir(parents=True, exist_ok=True)
    proto_path = proto_dir / filename
    proto_path.write_text(content, encoding="utf-8")
    return proto_path


_VALID_GATE = """\
---
gate: hard
label: Test Gate
summary: a test gate.
audit: 'Audit sentence here.'
priority: 100
question: 'Is this ready?'
skip-when: Never
invoke-when: A change is about to begin
depth-min: 1
---
# Protocol: Test Gate
"""

_VALID_GATE_B = """\
---
gate: hard
label: Second Gate
summary: another gate.
audit: 'Second audit.'
priority: 200
question: 'Is this also ready?'
invoke-when: Another trigger
depth-min: 1
---
# Protocol: Second Gate
"""

_GATE_DEPTH_2 = """\
---
gate: hard
label: Deep Gate
summary: requires depth 2.
audit: 'Deep audit.'
priority: 300
question: 'Deep question?'
depth-min: 2
---
# Protocol: Deep Gate
"""


# --- INV-declarative-hard-gates-frontmatter-schema ---


def test_discovers_gates_from_frontmatter(tmp_path: Path) -> None:
    """A protocol with gate: hard and all required fields is discovered."""
    _write_protocol(tmp_path, "test-gate.md", _VALID_GATE)

    with patch("kanon_core._scaffold._aspect_path", return_value=tmp_path), \
         patch("kanon_core._scaffold._aspect_protocols", return_value=["test-gate.md"]):
        result = _render_hard_gates({"kanon-sdd": 1})

    assert "Test Gate" in result
    assert "a test gate." in result


def test_missing_required_field_raises(tmp_path: Path) -> None:
    """gate: hard without required fields raises ClickException."""
    incomplete = """\
---
gate: hard
label: Incomplete
---
# Missing summary, audit, priority, question
"""
    _write_protocol(tmp_path, "bad.md", incomplete)

    with patch("kanon_core._scaffold._aspect_path", return_value=tmp_path), \
         patch("kanon_core._scaffold._aspect_protocols", return_value=["bad.md"]), \
         pytest.raises(click.ClickException, match="requires"):
        _render_hard_gates({"kanon-sdd": 1})


# --- INV-declarative-hard-gates-priority-unique ---


def test_duplicate_priority_raises(tmp_path: Path) -> None:
    """Two gates with the same priority raise ClickException."""
    _write_protocol(tmp_path, "gate-a.md", _VALID_GATE)
    duplicate = _VALID_GATE.replace("label: Test Gate", "label: Duplicate Gate")
    _write_protocol(tmp_path, "gate-b.md", duplicate)

    with patch("kanon_core._scaffold._aspect_path", return_value=tmp_path), \
         patch("kanon_core._scaffold._aspect_protocols", return_value=["gate-a.md", "gate-b.md"]), \
         pytest.raises(click.ClickException, match="priority.*collision"):
        _render_hard_gates({"kanon-sdd": 1})


# --- INV-declarative-hard-gates-depth-filtering ---


def test_depth_filtering(tmp_path: Path) -> None:
    """A gate with depth-min: 2 is excluded when aspect depth is 1."""
    _write_protocol(tmp_path, "deep.md", _GATE_DEPTH_2)

    with patch("kanon_core._scaffold._aspect_path", return_value=tmp_path), \
         patch("kanon_core._scaffold._aspect_protocols", return_value=["deep.md"]):
        result = _render_hard_gates({"kanon-sdd": 1})

    assert "Deep Gate" not in result


def test_depth_filtering_includes_at_sufficient_depth(tmp_path: Path) -> None:
    """A gate with depth-min: 2 is included when aspect depth is 2."""
    _write_protocol(tmp_path, "deep.md", _GATE_DEPTH_2)

    with patch("kanon_core._scaffold._aspect_path", return_value=tmp_path), \
         patch("kanon_core._scaffold._aspect_protocols", return_value=["deep.md"]):
        result = _render_hard_gates({"kanon-sdd": 2})

    assert "Deep Gate" in result


# --- INV-declarative-hard-gates-decision-tree-dynamic ---


def test_decision_tree_generated_from_questions(tmp_path: Path) -> None:
    """Gates are rendered in priority order in the table."""
    _write_protocol(tmp_path, "gate-a.md", _VALID_GATE_B)  # priority 200
    _write_protocol(tmp_path, "gate-b.md", _VALID_GATE)    # priority 100

    with patch("kanon_core._scaffold._aspect_path", return_value=tmp_path), \
         patch("kanon_core._scaffold._aspect_protocols", return_value=["gate-a.md", "gate-b.md"]):
        result = _render_hard_gates({"kanon-sdd": 1})

    # Priority 100 gate comes before priority 200 gate in table
    pos_a = result.index("Test Gate")
    pos_b = result.index("Second Gate")
    assert pos_a < pos_b

    # Command directive present
    assert "kanon gates check ." in result


# --- INV-declarative-hard-gates-skip-when-rendered ---


def test_skip_when_rendered(tmp_path: Path) -> None:
    """skip-when is available via kanon gates check (not in static table)."""
    _write_protocol(tmp_path, "gate.md", _VALID_GATE)

    with patch("kanon_core._scaffold._aspect_path", return_value=tmp_path), \
         patch("kanon_core._scaffold._aspect_protocols", return_value=["gate.md"]):
        result = _render_hard_gates({"kanon-sdd": 1})

    # Table contains the gate summary but not skip-when (moved to CLI output)
    assert "a test gate." in result
    assert "judgment" in result  # directive mentions judgment gates


# --- INV-declarative-hard-gates-fires-from-invoke-when ---


def test_fires_from_invoke_when(tmp_path: Path) -> None:
    """The 'Fires when' column uses the invoke-when frontmatter field."""
    _write_protocol(tmp_path, "gate.md", _VALID_GATE)

    with patch("kanon_core._scaffold._aspect_path", return_value=tmp_path), \
         patch("kanon_core._scaffold._aspect_protocols", return_value=["gate.md"]):
        result = _render_hard_gates({"kanon-sdd": 1})

    assert "A change is about to begin" in result


# --- INV-declarative-hard-gates-publisher-symmetric ---


def test_publisher_symmetric(tmp_path: Path) -> None:
    """Gates from different aspect namespaces use identical discovery logic."""
    _write_protocol(tmp_path, "custom-gate.md", _VALID_GATE.replace("priority: 100", "priority: 900"))

    with patch("kanon_core._scaffold._aspect_path", return_value=tmp_path), \
         patch("kanon_core._scaffold._aspect_protocols", return_value=["custom-gate.md"]):
        result = _render_hard_gates({"project-custom": 1})

    assert "Test Gate" in result
