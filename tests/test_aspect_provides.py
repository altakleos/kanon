"""Tests for the `provides:` capability registry and generalised `requires:`.

Covers all 10 invariants in `docs/specs/aspect-provides.md`:

- INV-1: provides field shape + validation
- INV-2: requires accepts both depth predicates and capability presence
- INV-3: capability name format (no underscores)
- INV-4: resolution against proposed aspect-set
- INV-5: removal check (capability + depth)
- INV-6: aspect info surfaces Provides
- INV-7: CI validation hard-fails on dangling capability
- INV-8: multiple suppliers permitted
- INV-9: every shipped aspect declares its capability
- INV-10: no silent meaning change for existing predicates
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import click
import pytest
import yaml
from click.testing import CliRunner

from kanon._cli_helpers import (
    _check_removal_dependents,
    _check_requires,
    _classify_predicate,
)
from kanon._manifest import (
    _aspect_provides,
    _capability_suppliers,
    _load_top_manifest,
    _validate_provides_field,
)
from kanon.cli import (
    main,
)

# --- INV-aspect-provides-provides-field ---


def test_provides_field_round_trips() -> None:
    """`_aspect_provides('kanon-sdd')` returns the declared list."""
    assert _aspect_provides("kanon-sdd") == ["planning-discipline", "spec-discipline"]


def test_provides_empty_list_is_valid(tmp_path: Path) -> None:
    _validate_provides_field(tmp_path / "fake.yaml", "test", [])


def test_provides_non_list_rejected(tmp_path: Path) -> None:
    with pytest.raises(click.ClickException) as exc:
        _validate_provides_field(tmp_path / "fake.yaml", "test", "not-a-list")
    assert "must be a list" in str(exc.value.message)


def test_provides_invalid_capability_name_rejected(tmp_path: Path) -> None:
    with pytest.raises(click.ClickException) as exc:
        _validate_provides_field(tmp_path / "fake.yaml", "test", ["Invalid_Cap"])
    assert "is invalid" in str(exc.value.message)


# --- INV-aspect-provides-requires-generalised + INV-classify ---


def test_classify_depth_predicate_three_tokens() -> None:
    assert _classify_predicate("sdd >= 1") == ("depth", "kanon-sdd", ">=", 1)


def test_classify_capability_one_token() -> None:
    assert _classify_predicate("planning-discipline") == ("capability", "planning-discipline")


def test_classify_rejects_two_tokens() -> None:
    with pytest.raises(click.ClickException) as exc:
        _classify_predicate("two tokens")
    assert "got 2 tokens" in str(exc.value.message)


def test_classify_rejects_four_tokens() -> None:
    with pytest.raises(click.ClickException) as exc:
        _classify_predicate("a >= 1 extra")
    assert "got 4 tokens" in str(exc.value.message)


def test_classify_rejects_uppercase_capability() -> None:
    with pytest.raises(click.ClickException) as exc:
        _classify_predicate("Bad-Cap")
    assert "must be a capability name" in str(exc.value.message)


def test_classify_rejects_unknown_operator() -> None:
    with pytest.raises(click.ClickException) as exc:
        _classify_predicate("sdd ~ 1")
    assert "unknown operator" in str(exc.value.message)


def test_classify_rejects_non_integer_depth() -> None:
    with pytest.raises(click.ClickException) as exc:
        _classify_predicate("sdd >= one")
    assert "is not an integer" in str(exc.value.message)


# --- INV-aspect-provides-resolution ---


def test_check_requires_capability_satisfied() -> None:
    """A capability-presence predicate is OK when at least one supplier is enabled."""
    top = _load_top_manifest()
    # synthesise a fake consumer aspect that requires planning-discipline
    fake_top = {"aspects": {**top["aspects"], "fake": {"requires": ["planning-discipline"]}}}
    result = _check_requires("fake", {"kanon-sdd": 1}, fake_top)
    assert result is None


def test_check_requires_capability_unsatisfied() -> None:
    """A capability-presence predicate fails when no supplier is enabled."""
    top = _load_top_manifest()
    fake_top = {"aspects": {**top["aspects"], "fake": {"requires": ["planning-discipline"]}}}
    result = _check_requires("fake", {}, fake_top)  # nothing enabled
    assert result is not None
    assert "planning-discipline" in result
    assert "no enabled aspect provides it" in result


def test_check_requires_capability_unsatisfied_when_supplier_at_depth_zero() -> None:
    top = _load_top_manifest()
    fake_top = {"aspects": {**top["aspects"], "fake": {"requires": ["planning-discipline"]}}}
    result = _check_requires("fake", {"kanon-sdd": 0}, fake_top)  # depth 0 = not enabled
    assert result is not None


def test_check_requires_depth_predicate_unchanged() -> None:
    """worktrees now suggests (not requires) sdd — no error when sdd is absent."""
    top = _load_top_manifest()
    # worktrees suggests "sdd >= 1" — satisfied with sdd at 1
    assert _check_requires("kanon-worktrees", {"kanon-sdd": 1, "kanon-worktrees": 1}, top) is None
    # No error when sdd is absent — it's a suggests, not requires
    assert _check_requires("kanon-worktrees", {"kanon-worktrees": 1}, top) is None


def test_check_requires_mixed_depth_and_capability() -> None:
    """An aspect declaring both forms in `requires:` evaluates each independently."""
    top = _load_top_manifest()
    fake_top = {
        "aspects": {
            **top["aspects"],
            "fake": {"requires": ["sdd >= 1", "planning-discipline"]},
        }
    }
    # both satisfied
    assert _check_requires("fake", {"kanon-sdd": 1}, fake_top) is None
    # depth fails first → depth error returned
    err = _check_requires("fake", {}, fake_top)
    assert err is not None


# --- INV-aspect-provides-removal-check ---


def test_removal_not_blocked_by_suggests_dependent() -> None:
    top = _load_top_manifest()
    # Removing sdd while worktrees still enabled — worktrees only suggests sdd, not requires
    err = _check_removal_dependents("kanon-sdd", {"kanon-worktrees": 1}, top)
    assert err is None


def test_removal_blocked_when_only_supplier_being_removed() -> None:
    top = _load_top_manifest()
    fake_top = {
        "aspects": {
            **top["aspects"],
            "consumer": {
                "depth": 1,
                "requires": ["planning-discipline"],
                "provides": [],
            },
        }
    }
    err = _check_removal_dependents("kanon-sdd", {"consumer": 1}, fake_top)
    assert err is not None
    assert "planning-discipline" in err


def test_removal_allowed_when_alternative_supplier_remains() -> None:
    """If two aspects supply the same capability, removing one is OK."""
    top = _load_top_manifest()
    fake_top = {
        "aspects": {
            **top["aspects"],
            "alt": {"provides": ["planning-discipline"]},
            "consumer": {"requires": ["planning-discipline"]},
        }
    }
    # `alt` (depth 1) still supplies planning-discipline after sdd removal
    err = _check_removal_dependents("kanon-sdd", {"alt": 1, "consumer": 1}, fake_top)
    assert err is None


# --- INV-aspect-provides-info-surfaces ---


def test_aspect_info_surfaces_provides_for_sdd() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["aspect", "info", "kanon-sdd"])
    assert result.exit_code == 0, result.output
    assert "Provides:" in result.output
    assert "planning-discipline" in result.output
    assert "spec-discipline" in result.output


def test_aspect_info_provides_none_when_aspect_has_no_provides(tmp_path: Path) -> None:
    """An aspect with no `provides:` field shows `Provides: (none)`.

    All currently-shipped aspects declare provides per INV-9; this test patches
    `_aspect_provides` to simulate an aspect without a declaration.
    """
    runner = CliRunner()
    with patch("kanon.cli._aspect_provides", return_value=[]):
        result = runner.invoke(main, ["aspect", "info", "kanon-sdd"])
    assert result.exit_code == 0, result.output
    assert "Provides:      (none)" in result.output


# --- INV-aspect-provides-ci-validates-completeness ---


def test_ci_check_requires_resolution_passes_on_live_kit() -> None:
    """The kit's existing `requires:` predicates all resolve."""
    import importlib.util

    spec_path = Path(__file__).resolve().parents[1] / "ci" / "check_kit_consistency.py"
    spec_mod = importlib.util.spec_from_file_location("check_kit_consistency", spec_path)
    assert spec_mod is not None and spec_mod.loader is not None
    mod = importlib.util.module_from_spec(spec_mod)
    spec_mod.loader.exec_module(mod)

    errors: list[str] = []
    mod._check_requires_resolution(errors)
    assert errors == [], f"Live kit fails capability resolution: {errors}"


def test_ci_check_requires_resolution_flags_dangling_capability(tmp_path: Path) -> None:
    """Synthesise a manifest with a capability that no aspect provides; verify rejection.

    Patches `_load_top_manifest` (the CI script's own helper, not kanon._manifest)
    to return a manifest with a dangling capability-presence predicate.
    """
    import importlib.util

    spec_path = Path(__file__).resolve().parents[1] / "ci" / "check_kit_consistency.py"
    spec_mod = importlib.util.spec_from_file_location("check_kit_consistency", spec_path)
    assert spec_mod is not None and spec_mod.loader is not None
    mod = importlib.util.module_from_spec(spec_mod)
    spec_mod.loader.exec_module(mod)

    fake_top = {
        "aspects": {
            "alpha": {
                "provides": ["existing-capability"],
                "requires": ["nonexistent-capability"],
            }
        }
    }
    with patch.object(mod, "_load_top_manifest", return_value=(fake_top, None)):
        errors: list[str] = []
        mod._check_requires_resolution(errors)
    assert errors
    assert any("nonexistent-capability" in e for e in errors)


# --- INV-aspect-provides-multiple-suppliers ---


def test_multiple_suppliers_recognised() -> None:
    top = _load_top_manifest()
    fake_top = {
        "aspects": {
            **top["aspects"],
            "alt-sdd": {"provides": ["planning-discipline"]},
        }
    }
    suppliers = _capability_suppliers(fake_top, "planning-discipline")
    assert "kanon-sdd" in suppliers
    assert "alt-sdd" in suppliers


# --- INV-aspect-provides-all-aspects-declare ---


@pytest.mark.parametrize(
    "aspect,expected",
    [
        ("kanon-sdd", ["planning-discipline", "spec-discipline"]),
        ("kanon-worktrees", ["worktree-isolation"]),
        ("kanon-release", ["release-discipline"]),
        ("kanon-testing", ["test-discipline"]),
        ("kanon-security", ["security-discipline"]),
        ("kanon-deps", ["dependency-hygiene"]),
    ],
)
def test_every_shipped_aspect_declares_capability(
    aspect: str, expected: list[str]
) -> None:
    """INV-9: spec-mandated capability table matches the live kit."""
    assert _aspect_provides(aspect) == expected


def test_kit_manifest_yaml_matches_loader() -> None:
    """The kit manifest YAML and `_load_top_manifest` agree on `provides:` entries."""
    import kanon

    manifest_path = Path(kanon.__file__).parent / "kit" / "manifest.yaml"
    on_disk = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    loaded = _load_top_manifest()
    for name, entry in on_disk["aspects"].items():
        disk_provides = entry.get("provides", []) or []
        loaded_provides = loaded["aspects"][name].get("provides", []) or []
        assert disk_provides == loaded_provides, f"mismatch on {name}"


# --- INV-aspect-provides-no-silent-meaning-change ---


def test_existing_kit_requires_predicates_classify_as_depth() -> None:
    """Every `requires:` predicate currently in the live kit must classify as a
    depth predicate, never as a capability. Guards against accidentally
    introducing a 1-token entry that would silently change meaning under the
    generalised parser."""
    top = _load_top_manifest()
    for name, entry in top["aspects"].items():
        for predicate in entry.get("requires", []) or []:
            classified = _classify_predicate(predicate)
            assert classified[0] == "depth", (
                f"aspect {name!r}: predicate {predicate!r} classifies as {classified[0]!r}; "
                f"expected 'depth'. Migration of existing predicates to capability form is "
                f"out of scope for this spec."
            )
    # After scaffold-v2, no kit aspect has a hard `requires:` predicate.
    # This test validates that if any exist, they classify as 'depth'.
    # Currently none exist, so seen_any is False — that's correct.


# --- ADR-0028: bare-name sugar (T12) ---


def test_normalise_aspect_name_bare_sugars_to_kanon() -> None:
    """A bare aspect name resolves to the `kanon-` namespace by default."""
    from kanon._manifest import _normalise_aspect_name
    assert _normalise_aspect_name("sdd") == "kanon-sdd"
    assert _normalise_aspect_name("worktrees") == "kanon-worktrees"
    assert _normalise_aspect_name("graph-rename") == "kanon-graph-rename"


def test_normalise_aspect_name_namespaced_passes_through() -> None:
    """A name already in canonical form is returned unchanged."""
    from kanon._manifest import _normalise_aspect_name
    assert _normalise_aspect_name("kanon-sdd") == "kanon-sdd"
    assert _normalise_aspect_name("kanon-worktrees") == "kanon-worktrees"
    assert _normalise_aspect_name("project-auth-policy") == "project-auth-policy"


def test_normalise_aspect_name_invalid_rejected() -> None:
    """Anything that fails both regexes (e.g., uppercase, leading dash) is rejected."""
    import click
    import pytest

    from kanon._manifest import _normalise_aspect_name
    with pytest.raises(click.ClickException, match="Invalid aspect name"):
        _normalise_aspect_name("SDD")
    with pytest.raises(click.ClickException, match="Invalid aspect name"):
        _normalise_aspect_name("-sdd")
    with pytest.raises(click.ClickException, match="Invalid aspect name"):
        _normalise_aspect_name("")


def test_split_aspect_name() -> None:
    """`_split_aspect_name` returns (namespace, local) where local may contain dashes."""
    from kanon._manifest import _split_aspect_name
    assert _split_aspect_name("kanon-sdd") == ("kanon", "sdd")
    assert _split_aspect_name("kanon-graph-rename") == ("kanon", "graph-rename")
    assert _split_aspect_name("project-auth-policy") == ("project", "auth-policy")


def test_classify_predicate_bare_aspect_name_sugars() -> None:
    """A 3-token depth predicate with a bare aspect name sugars to `kanon-` form."""
    from kanon._cli_helpers import _classify_predicate
    classified = _classify_predicate("sdd >= 1")
    assert classified == ("depth", "kanon-sdd", ">=", 1)


def test_classify_predicate_namespaced_aspect_name_unchanged() -> None:
    """A 3-token depth predicate with a namespaced aspect name passes through."""
    from kanon._cli_helpers import _classify_predicate
    classified = _classify_predicate("kanon-sdd >= 1")
    assert classified == ("depth", "kanon-sdd", ">=", 1)


def test_classify_predicate_capability_unaffected_by_namespace_grammar() -> None:
    """A 1-token capability predicate is not subject to aspect-name sugar."""
    from kanon._cli_helpers import _classify_predicate
    classified = _classify_predicate("planning-discipline")
    assert classified == ("capability", "planning-discipline")
