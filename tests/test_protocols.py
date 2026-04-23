"""Tests for the prose-as-code protocol layer (docs/specs/protocols.md)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_KIT_PROTOCOLS = _REPO_ROOT / "src" / "kanon" / "kit" / "protocols"
_REPO_PROTOCOLS = _REPO_ROOT / ".kanon" / "protocols"
_MANIFEST = _REPO_ROOT / "src" / "kanon" / "kit" / "manifest.yaml"

_REQUIRED_FRONTMATTER_KEYS = ("status", "date", "tier-min", "invoke-when")


def _parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name}: missing opening frontmatter fence"
    end = text.find("\n---\n", 4)
    assert end > 0, f"{path.name}: missing closing frontmatter fence"
    data = yaml.safe_load(text[4:end])
    assert isinstance(data, dict), f"{path.name}: frontmatter is not a YAML mapping"
    return data


def _manifest() -> dict:
    return yaml.safe_load(_MANIFEST.read_text(encoding="utf-8"))


def _all_protocol_files() -> list[Path]:
    return sorted(_KIT_PROTOCOLS.glob("*.md"))


def test_kit_protocols_directory_exists() -> None:
    assert _KIT_PROTOCOLS.is_dir()
    assert _all_protocol_files(), "expected at least one protocol in kit/protocols/"


@pytest.mark.parametrize("proto", _all_protocol_files(), ids=lambda p: p.name)
def test_protocol_has_required_frontmatter_keys(proto: Path) -> None:
    fm = _parse_frontmatter(proto)
    for key in _REQUIRED_FRONTMATTER_KEYS:
        assert key in fm, f"{proto.name}: frontmatter missing required key {key!r}"


@pytest.mark.parametrize("proto", _all_protocol_files(), ids=lambda p: p.name)
def test_protocol_status_is_accepted_value(proto: Path) -> None:
    fm = _parse_frontmatter(proto)
    assert fm["status"] in {"draft", "accepted", "deferred", "provisional", "superseded"}


@pytest.mark.parametrize("proto", _all_protocol_files(), ids=lambda p: p.name)
def test_protocol_date_is_iso(proto: Path) -> None:
    fm = _parse_frontmatter(proto)
    # yaml.safe_load converts ISO dates to datetime.date.
    assert isinstance(fm["date"], date), f"{proto.name}: date must be ISO 8601"


@pytest.mark.parametrize("proto", _all_protocol_files(), ids=lambda p: p.name)
def test_protocol_tier_min_matches_manifest(proto: Path) -> None:
    """Frontmatter `tier-min` must equal the tier the protocol is declared under."""
    fm = _parse_frontmatter(proto)
    declared_tier: int | None = None
    for n in range(4):
        if proto.name in _manifest().get(f"tier-{n}", {}).get("protocols", []):
            declared_tier = n
            break
    assert declared_tier is not None, f"{proto.name}: not declared in manifest.yaml"
    assert fm["tier-min"] == declared_tier, (
        f"{proto.name}: frontmatter tier-min={fm['tier-min']} "
        f"but manifest declares under tier-{declared_tier}"
    )


@pytest.mark.parametrize("proto", _all_protocol_files(), ids=lambda p: p.name)
def test_protocol_invoke_when_is_nonempty(proto: Path) -> None:
    fm = _parse_frontmatter(proto)
    assert str(fm["invoke-when"]).strip(), f"{proto.name}: invoke-when must be non-empty"


@pytest.mark.parametrize("proto", _all_protocol_files(), ids=lambda p: p.name)
def test_protocol_byte_equals_repo_canonical(proto: Path) -> None:
    """Spec invariant 1: kit mirror byte-identical to repo-canonical .kanon/protocols/."""
    repo_copy = _REPO_PROTOCOLS / proto.name
    assert repo_copy.is_file(), f"repo canonical missing: .kanon/protocols/{proto.name}"
    assert proto.read_bytes() == repo_copy.read_bytes()
