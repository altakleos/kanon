"""Phase A.5: bare-name CLI sugar deprecation.

Per ADR-0048 publisher-symmetry, the bare-name shorthand (`sdd` → `kanon-sdd`)
privileges the `kanon-` namespace at the CLI surface — `acme-fintech` users have
no equivalent shorthand. ``_normalise_aspect_name`` now emits a deprecation
warning on stderr when sugaring a bare name; behaviour is otherwise preserved.
"""

from __future__ import annotations

import pytest

from kanon_core._manifest import _normalise_aspect_name


def test_bare_name_emits_deprecation_warning(
    capfd: pytest.CaptureFixture[str],
) -> None:
    result = _normalise_aspect_name("sdd")
    assert result == "kanon-sdd"
    captured = capfd.readouterr()
    assert "deprecated" in captured.err
    assert "'sdd'" in captured.err
    assert "'kanon-sdd'" in captured.err


def test_namespaced_kanon_name_emits_no_warning(
    capfd: pytest.CaptureFixture[str],
) -> None:
    result = _normalise_aspect_name("kanon-sdd")
    assert result == "kanon-sdd"
    captured = capfd.readouterr()
    assert captured.err == ""
    assert captured.out == ""


def test_namespaced_project_name_emits_no_warning(
    capfd: pytest.CaptureFixture[str],
) -> None:
    result = _normalise_aspect_name("project-myown")
    assert result == "project-myown"
    captured = capfd.readouterr()
    assert captured.err == ""


def test_bare_name_warning_mentions_adr(
    capfd: pytest.CaptureFixture[str],
) -> None:
    """The warning text cites the ADR so users have a direct reference."""
    _normalise_aspect_name("worktrees")
    captured = capfd.readouterr()
    assert "ADR-0048" in captured.err
