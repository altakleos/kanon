"""Plan T9 + AC7: publisher-symmetry CI gate.

Asserts `scripts/check_kit_consistency.py`'s algorithm is publisher-blind:
when pointed at the synthetic `tests/fixtures/acme-test-aspects/` overlay
(an `acme-test`-namespaced bundle, structurally analogous to any real
`acme-<vendor>-aspects` distribution per ADR-0040), the gate produces
**zero structural errors**. Any future regression that hardcodes `kanon-`
or `kanon-aspects` in a gate code path turns this CI step red.

The overlay's structure mirrors the kit's own:

- `pyproject.toml` with `[project.entry-points."kanon.aspects"]` listing
  `acme-test-foo` (the public discovery contract per ADR-0040).
- `aspects/acme_test_foo/manifest.yaml` per-aspect, canonical per ADR-0055.
- `kit/harnesses.yaml` so the gate's harnesses check has data.

Per panel R2 unanimous vote (Q2): operationally ratifies
`P-publisher-symmetry §Implications` ("CI gates the symmetry empirically")
on every commit, not as a manual post-merge check.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import REPO_ROOT as _REPO_ROOT  # noqa: E402

_FIXTURE_ROOT = _REPO_ROOT / "tests" / "fixtures" / "acme-test-aspects"


@pytest.fixture(scope="module")
def ckc(load_ci_script):
    return load_ci_script("check_kit_consistency.py")


def test_acme_overlay_passes_publisher_symmetric_gate(
    ckc, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The kit-consistency gate's algorithm is publisher-blind.

    Pointed at the synthetic `acme-test`-namespaced overlay (with the
    namespace prefix monkeypatched to match), the gate's checks must
    produce zero errors — the same outcome as against the kit's own
    `kanon-` bundle. If they don't, the gate has accumulated a
    `kanon-` privilege, violating `P-publisher-symmetry`.
    """
    assert _FIXTURE_ROOT.is_dir(), (
        f"missing publisher-symmetry fixture at "
        f"{_FIXTURE_ROOT.relative_to(_REPO_ROOT)}"
    )

    monkeypatch.setattr(ckc, "_REPO_ROOT", _FIXTURE_ROOT)
    monkeypatch.setattr(ckc, "_KIT", _FIXTURE_ROOT / "kit")
    monkeypatch.setattr(
        ckc, "_ASPECTS_PKG_ROOT", _FIXTURE_ROOT,
    )
    monkeypatch.setattr(ckc, "_KIT_NAMESPACE", "acme-test")

    errors = ckc.run_checks()
    assert errors == [], (
        "publisher-symmetry CI gate failed against the acme-test overlay. "
        "This means the kit-consistency gate has accumulated a hidden "
        "`kanon-` privilege somewhere — find the offending hardcode "
        "and parameterize it (per plan T9). Errors:\n  "
        + "\n  ".join(errors)
    )


def test_acme_overlay_uses_acme_namespace_in_pyproject() -> None:
    """Sanity: the overlay actually uses the `acme-test` namespace.

    Catches a maintenance regression where the fixture is accidentally
    rewritten to `kanon-` slugs (which would silently weaken the
    symmetry assertion above to a tautology).
    """
    pyproject_text = (_FIXTURE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "acme-test-foo" in pyproject_text, (
        "fixture's pyproject must declare an acme-test-namespaced slug; "
        "otherwise test_acme_overlay_passes_publisher_symmetric_gate "
        "is testing a kanon-on-kanon tautology."
    )
    assert "kanon-" not in pyproject_text or "kanon.aspects" in pyproject_text, (
        "fixture must not declare kanon- slugs (only the entry-point group "
        "name 'kanon.aspects' contains 'kanon')."
    )
