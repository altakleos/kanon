"""Phase A.5 completion: bare-name CLI sugar removed.

Per ADR-0048 publisher-symmetry, the bare-name shorthand (`sdd` → `kanon-sdd`)
privileged the `kanon-` namespace at the CLI surface — `acme-fintech` users had
no equivalent shorthand. ``_normalise_aspect_name`` now raises ClickException
when given a bare name.
"""

from __future__ import annotations

import click
import pytest

from kanon_core._manifest import _normalise_aspect_name


def test_bare_name_raises_click_exception() -> None:
    with pytest.raises(click.ClickException, match="no longer accepted"):
        _normalise_aspect_name("sdd")


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


def test_bare_name_error_mentions_full_name() -> None:
    """The error message includes the full canonical name."""
    with pytest.raises(click.ClickException, match="'kanon-worktrees'"):
        _normalise_aspect_name("worktrees")


def test_bare_name_error_mentions_adr() -> None:
    """The error text cites the ADR so users have a direct reference."""
    with pytest.raises(click.ClickException, match="ADR-0048"):
        _normalise_aspect_name("worktrees")
