"""Tests for the prose-as-code protocol layer (docs/specs/protocols.md).

Under the aspect-model layout (ADR-0012), protocols live under each aspect's
namespace: kit side at kernel/kit/aspects/<aspect>/protocols/*.md, consumer
side at .kanon/protocols/<aspect>/*.md. Frontmatter uses `depth-min:`.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
# Per substrate-content-move sub-plan: kanon-* aspect data lives under
# packages/kanon-aspects/src/kanon_aspects/aspects/<slug>/.
_SDD_BASE = _REPO_ROOT / "packages" / "kanon-aspects" / "src" / "kanon_aspects" / "aspects" / "kanon_sdd"
_SDD_PROTOCOLS = _SDD_BASE / "protocols"
_SDD_MANIFEST = _SDD_BASE / "manifest.yaml"
_REPO_SDD_PROTOCOLS = _REPO_ROOT / ".kanon" / "protocols" / "kanon-sdd"

_REQUIRED_FRONTMATTER_KEYS = ("status", "date", "depth-min", "invoke-when")


def _parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name}: missing opening frontmatter fence"
    end = text.find("\n---\n", 4)
    assert end > 0, f"{path.name}: missing closing frontmatter fence"
    data = yaml.safe_load(text[4:end])
    assert isinstance(data, dict), f"{path.name}: frontmatter is not a YAML mapping"
    return data


def _sdd_manifest() -> dict:
    return yaml.safe_load(_SDD_MANIFEST.read_text(encoding="utf-8"))


def _all_sdd_protocol_files() -> list[Path]:
    return sorted(_SDD_PROTOCOLS.glob("*.md"))


def test_sdd_protocols_directory_exists() -> None:
    assert _SDD_PROTOCOLS.is_dir()
    assert _all_sdd_protocol_files(), "expected at least one protocol under aspects/kanon_sdd/protocols/"


@pytest.mark.parametrize("proto", _all_sdd_protocol_files(), ids=lambda p: p.name)
def test_protocol_has_required_frontmatter_keys(proto: Path) -> None:
    fm = _parse_frontmatter(proto)
    for key in _REQUIRED_FRONTMATTER_KEYS:
        assert key in fm, f"{proto.name}: frontmatter missing required key {key!r}"


@pytest.mark.parametrize("proto", _all_sdd_protocol_files(), ids=lambda p: p.name)
def test_protocol_status_is_accepted_value(proto: Path) -> None:
    fm = _parse_frontmatter(proto)
    assert fm["status"] in {"draft", "accepted", "deferred", "provisional", "superseded"}


@pytest.mark.parametrize("proto", _all_sdd_protocol_files(), ids=lambda p: p.name)
def test_protocol_date_is_iso(proto: Path) -> None:
    fm = _parse_frontmatter(proto)
    assert isinstance(fm["date"], date), f"{proto.name}: date must be ISO 8601"


@pytest.mark.parametrize("proto", _all_sdd_protocol_files(), ids=lambda p: p.name)
def test_protocol_depth_min_matches_sub_manifest(proto: Path) -> None:
    """Frontmatter `depth-min` must equal the depth the protocol is declared under."""
    fm = _parse_frontmatter(proto)
    sub = _sdd_manifest()
    declared_depth: int | None = None
    for d in range(4):
        if proto.name in (sub.get(f"depth-{d}", {}).get("protocols", []) or []):
            declared_depth = d
            break
    assert declared_depth is not None, (
        f"{proto.name}: not declared in aspects/kanon_sdd/manifest.yaml"
    )
    assert fm["depth-min"] == declared_depth, (
        f"{proto.name}: frontmatter depth-min={fm['depth-min']} "
        f"but sub-manifest declares under depth-{declared_depth}"
    )


@pytest.mark.parametrize("proto", _all_sdd_protocol_files(), ids=lambda p: p.name)
def test_protocol_invoke_when_is_nonempty(proto: Path) -> None:
    fm = _parse_frontmatter(proto)
    assert str(fm["invoke-when"]).strip(), f"{proto.name}: invoke-when must be non-empty"


@pytest.mark.parametrize("proto", _all_sdd_protocol_files(), ids=lambda p: p.name)
def test_protocol_byte_equals_repo_canonical(proto: Path) -> None:
    """Spec invariant 1 (updated for aspect namespace): kit mirror byte-identical
    to .kanon/protocols/kanon-sdd/<name>.md.
    """
    repo_copy = _REPO_SDD_PROTOCOLS / proto.name
    assert repo_copy.is_file(), f"repo canonical missing: .kanon/protocols/kanon-sdd/{proto.name}"
    assert proto.read_bytes() == repo_copy.read_bytes()
