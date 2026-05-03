"""Fidelity-fixture replay engine for ``kanon verify``.

Realises the verification-contract carve-out (INV-10, ratified by ADR-0029)
that authorises lexical replay of ``.kanon/fidelity/<protocol>.dogfood.md``
capture files when an aspect declaring the ``behavioural-verification``
capability (per ADR-0026) is enabled.

The engine is text-only by INV-7 of ``docs/specs/fidelity.md``: it MUST NOT
call :mod:`subprocess`, MUST NOT import consumer Python modules, MUST NOT
invoke a test runner, MUST NOT call out to an LLM model or any network
endpoint. It reads only files committed under the consumer's
``.kanon/fidelity/`` directory.

See :doc:`docs/specs/fidelity.md` for the full invariant surface.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from kernel._manifest import _parse_frontmatter

# The capability flag that gates the carve-out per ADR-0026 / spec INV-6.
BEHAVIOURAL_VERIFICATION_CAPABILITY = "behavioural-verification"

# Turn marker grammar (spec INV-4): an uppercase identifier followed by
# colon and at least one space or tab, anchored at column zero.
_TURN_MARKER_RE = re.compile(r"^([A-Z][A-Z0-9_]*):[ \t]+", re.MULTILINE)
_BRACKET_TURN_MARKER_RE = re.compile(r"^\[([A-Z][A-Z0-9_]*)\][ \t]+", re.MULTILINE)

_TURN_FORMATS: dict[str, re.Pattern[str]] = {
    "colon": _TURN_MARKER_RE,
    "bracket": _BRACKET_TURN_MARKER_RE,
}

# Recognised assertion-family keys (spec INV-5).
_FORBIDDEN_KEY = "forbidden_phrases"
_REQUIRED_ONE_OF_KEY = "required_one_of"
_REQUIRED_ALL_OF_KEY = "required_all_of"


@dataclass(frozen=True)
class WordShareBand:
    min: float | None
    max: float | None


@dataclass(frozen=True)
class PatternDensityEntry:
    patterns: tuple[str, ...]
    strip_code_fences: bool
    min: float | None
    max: float | None


@dataclass(frozen=True)
class Fixture:
    """Parsed fidelity fixture (spec INV-3)."""

    path: Path
    protocol: str
    actor: str
    turn_format: str  # "colon" or "bracket"
    forbidden_phrases: tuple[str, ...]
    required_one_of: tuple[str, ...]
    required_all_of: tuple[str, ...]
    word_share: WordShareBand | None
    pattern_density: tuple[PatternDensityEntry, ...]


def _string_list(value: object, label: str, path_name: str) -> tuple[tuple[str, ...], list[str]]:
    """Validate that *value* is a list of strings; return (tuple, errors)."""
    if value is None:
        return (), []
    if not isinstance(value, list):
        return (), [
            f"fidelity: {path_name}: {label} must be a list (got {type(value).__name__})"
        ]
    errors: list[str] = []
    items: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            errors.append(
                f"fidelity: {path_name}: {label} entry must be a string (got {type(entry).__name__})"
            )
        else:
            items.append(entry)
    return tuple(items), errors


def _validate_regex_patterns(
    label: str, patterns: list[str] | tuple[str, ...], filename: str,
) -> list[str]:
    """Return errors for patterns that fail to compile as regex."""
    errors: list[str] = []
    for pattern in patterns:
        try:
            re.compile(pattern)
        except re.error as exc:
            errors.append(
                f"fidelity: {filename}: invalid regex in {label}: "
                f"{pattern!r} ({exc})"
            )
    return errors


def _parse_min_max_band(
    raw: object, key_prefix: str, filename: str,
) -> tuple[float | None, float | None, list[str]]:
    """Parse a {min, max} numeric band. Return (min, max, errors)."""
    errors: list[str] = []
    if not isinstance(raw, dict):
        return None, None, [f"fidelity: {filename}: {key_prefix} must be a mapping"]
    v_min = raw.get("min")
    v_max = raw.get("max")
    if v_min is not None and not isinstance(v_min, (int, float)):
        errors.append(f"fidelity: {filename}: {key_prefix}.min must be a number")
    elif v_max is not None and not isinstance(v_max, (int, float)):
        errors.append(f"fidelity: {filename}: {key_prefix}.max must be a number")
    elif v_min is not None and v_max is not None and v_min > v_max:
        errors.append(f"fidelity: {filename}: {key_prefix}.min ({v_min}) > max ({v_max})")
    if errors:
        return None, None, errors
    return (
        float(v_min) if v_min is not None else None,
        float(v_max) if v_max is not None else None,
        [],
    )


def _parse_pattern_density_entries(
    raw: object, filename: str,
) -> tuple[list[PatternDensityEntry], list[str]]:
    """Parse the pattern_density list. Return (entries, errors)."""
    if not isinstance(raw, list):
        return [], [f"fidelity: {filename}: pattern_density must be a list"]
    entries: list[PatternDensityEntry] = []
    errors: list[str] = []
    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            errors.append(f"fidelity: {filename}: pattern_density[{idx}] must be a mapping")
            continue
        p_single = entry.get("pattern")
        p_list = entry.get("patterns", [])
        if p_single and isinstance(p_single, str):
            p_list = [p_single] + (p_list if isinstance(p_list, list) else [])
        elif not isinstance(p_list, list):
            errors.append(f"fidelity: {filename}: pattern_density[{idx}].patterns must be a list")
            continue
        if not p_list:
            errors.append(f"fidelity: {filename}: pattern_density[{idx}] must declare pattern or patterns")
            continue
        strip_cf = bool(entry.get("strip_code_fences", False))
        pd_min, pd_max, band_errors = _parse_min_max_band(
            {"min": entry.get("min"), "max": entry.get("max")},
            f"pattern_density[{idx}]", filename,
        )
        if band_errors:
            errors.extend(band_errors)
            continue
        regex_errors = _validate_regex_patterns(
            f"pattern_density[{idx}]", [p for p in p_list if isinstance(p, str)], filename,
        )
        if regex_errors:
            errors.extend(regex_errors)
            continue
        # Validate all patterns are strings
        if any(not isinstance(p, str) for p in p_list):
            errors.append(f"fidelity: {filename}: pattern_density[{idx}] pattern must be a string")
            continue
        entries.append(PatternDensityEntry(
            patterns=tuple(p_list),
            strip_code_fences=strip_cf,
            min=pd_min,
            max=pd_max,
        ))
    return entries, errors


def parse_fixture(path: Path) -> tuple[Fixture | None, list[str]]:
    """Parse a fidelity fixture file. Return (Fixture | None, errors).

    Per spec INV-3 and INV-8: missing required keys (`protocol`, `actor`),
    malformed lists, and regex compilation errors are *errors* (the function
    returns ``(None, errors)``). On success the returned Fixture is fully
    validated (regexes already compile).
    """
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [f"fidelity: {path.name}: cannot read fixture: {exc}"]

    fm = _parse_frontmatter(text)
    if not fm:
        return None, [
            f"fidelity: {path.name}: missing or malformed YAML frontmatter"
        ]

    protocol_raw = fm.get("protocol")
    actor_raw = fm.get("actor")
    protocol = protocol_raw if isinstance(protocol_raw, str) and protocol_raw else None
    actor = actor_raw if isinstance(actor_raw, str) and actor_raw else None
    if protocol is None:
        errors.append(
            f"fidelity: {path.name}: missing required frontmatter key 'protocol' "
            f"(must be a non-empty string)"
        )
    if actor is None:
        errors.append(
            f"fidelity: {path.name}: missing required frontmatter key 'actor' "
            f"(must be a non-empty string)"
        )

    forbidden, list_errors = _string_list(
        fm.get(_FORBIDDEN_KEY), _FORBIDDEN_KEY, path.name
    )
    errors.extend(list_errors)
    one_of, list_errors = _string_list(
        fm.get(_REQUIRED_ONE_OF_KEY), _REQUIRED_ONE_OF_KEY, path.name
    )
    errors.extend(list_errors)
    all_of, list_errors = _string_list(
        fm.get(_REQUIRED_ALL_OF_KEY), _REQUIRED_ALL_OF_KEY, path.name
    )
    errors.extend(list_errors)

    if errors:
        return None, errors

    # Eager regex-compilation check (spec INV-5 last sentence).
    for label, patterns in (
        (_FORBIDDEN_KEY, forbidden),
        (_REQUIRED_ONE_OF_KEY, one_of),
        (_REQUIRED_ALL_OF_KEY, all_of),
    ):
        errors.extend(_validate_regex_patterns(label, patterns, path.name))

    if errors:
        return None, errors

    # Turn format (default: colon)
    turn_format_raw = fm.get("turn_format", "colon")
    if turn_format_raw not in _TURN_FORMATS:
        errors.append(
            f"fidelity: {path.name}: turn_format must be 'colon' or 'bracket' "
            f"(got {turn_format_raw!r})"
        )
        return None, errors

    # word_share band
    word_share_band: WordShareBand | None = None
    ws_raw = fm.get("word_share")
    if ws_raw is not None:
        ws_min, ws_max, ws_errors = _parse_min_max_band(ws_raw, "word_share", path.name)
        errors.extend(ws_errors)
        if not ws_errors:
            word_share_band = WordShareBand(min=ws_min, max=ws_max)

    # pattern_density entries
    pd_entries: list[PatternDensityEntry] = []
    pd_raw = fm.get("pattern_density")
    if pd_raw is not None:
        pd_entries, pd_errors = _parse_pattern_density_entries(pd_raw, path.name)
        errors.extend(pd_errors)

    if errors:
        return None, errors

    # Required-key validation above guarantees both are non-None when we
    # reach this branch; assert narrows the type for mypy.
    assert protocol is not None
    assert actor is not None
    return (
        Fixture(
            path=path,
            protocol=protocol,
            actor=actor,
            turn_format=turn_format_raw,
            forbidden_phrases=forbidden,
            required_one_of=one_of,
            required_all_of=all_of,
            word_share=word_share_band,
            pattern_density=tuple(pd_entries),
        ),
        [],
    )


_CODE_FENCE_RE = re.compile(r"^```[^\n]*\n.*?^```", re.MULTILINE | re.DOTALL)
_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text)


def _count_words(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _extract_all_turns(dogfood_text: str, turn_re: re.Pattern[str]) -> list[str]:
    """Extract ALL turns (all actors) from dogfood text, content-only."""
    matches = list(turn_re.finditer(dogfood_text))
    if not matches:
        return []
    turns: list[str] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(dogfood_text)
        turns.append(dogfood_text[start:end].rstrip("\n"))
    return turns


def extract_actor_text(dogfood_text: str, actor: str, turn_format: str = "colon") -> tuple[str, int]:
    """Extract joined turns whose actor matches; return (joined_text, turn_count).

    Per spec INV-4: a turn marker is a line at column zero matching
    ``^([A-Z][A-Z0-9_]*):[ \\t]+``. A turn extends from its marker line
    (inclusive) to the next marker line or end-of-file. The fixture's
    ``actor`` value is matched case-sensitively against the captured
    identifier; matching turns are joined with ``\\n``. Lines outside any
    turn are ignored.
    """
    turn_re = _TURN_FORMATS.get(turn_format, _TURN_MARKER_RE)
    matches = list(turn_re.finditer(dogfood_text))
    if not matches:
        return "", 0
    turns: list[str] = []
    for i, match in enumerate(matches):
        if match.group(1) != actor:
            continue
        # Start after the marker so the turn text is content-only (the
        # marker prefix is metadata, not part of the actor's speech).
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(dogfood_text)
        turn = dogfood_text[start:end].rstrip("\n")
        turns.append(turn)
    return "\n".join(turns), len(turns)


def evaluate_fixture(fixture: Fixture, dogfood_text: str) -> list[str]:
    """Evaluate *fixture* against *dogfood_text*. Return errors (empty on pass).

    Per spec INV-5: each assertion family is evaluated independently.
    `forbidden_phrases` produces one error per matching regex.
    `required_one_of` produces one error if no regex matches.
    `required_all_of` produces one error per missing regex.
    """
    errors: list[str] = []
    actor_text, turn_count = extract_actor_text(dogfood_text, fixture.actor, fixture.turn_format)
    if turn_count == 0:
        errors.append(
            f"fidelity: {fixture.path.name}: dogfood has zero turns matching "
            f"actor {fixture.actor!r}; fixture asserts on no input"
        )
        return errors

    for pattern in fixture.forbidden_phrases:
        if re.search(pattern, actor_text, re.MULTILINE):
            errors.append(
                f"fidelity: {fixture.path.name}: forbidden phrase matched: "
                f"{pattern!r}"
            )

    if fixture.required_one_of and not any(
        re.search(p, actor_text, re.MULTILINE) for p in fixture.required_one_of
    ):
        errors.append(
            f"fidelity: {fixture.path.name}: no regex in required_one_of "
            f"matched: {list(fixture.required_one_of)!r}"
        )

    for pattern in fixture.required_all_of:
        if not re.search(pattern, actor_text, re.MULTILINE):
            errors.append(
                f"fidelity: {fixture.path.name}: required_all_of regex did "
                f"not match: {pattern!r}"
            )

    # Quantitative families (ADR-0033)
    if fixture.word_share is not None:
        turn_re = _TURN_FORMATS.get(fixture.turn_format, _TURN_MARKER_RE)
        all_turns = _extract_all_turns(dogfood_text, turn_re)
        total_words = sum(_count_words(t) for t in all_turns)
        actor_words = _count_words(actor_text)
        ratio = actor_words / total_words if total_words > 0 else 0.0
        if fixture.word_share.min is not None and ratio < fixture.word_share.min:
            errors.append(
                f"fidelity: {fixture.path.name}: word_share {ratio:.3f} "
                f"below min {fixture.word_share.min}"
            )
        if fixture.word_share.max is not None and ratio > fixture.word_share.max:
            errors.append(
                f"fidelity: {fixture.path.name}: word_share {ratio:.3f} "
                f"above max {fixture.word_share.max}"
            )

    for i, pd in enumerate(fixture.pattern_density):
        text_for_density = actor_text
        if pd.strip_code_fences:
            text_for_density = _strip_code_fences(text_for_density)
        match_count = sum(len(re.findall(p, text_for_density)) for p in pd.patterns)
        density = match_count / turn_count if turn_count > 0 else 0.0
        if pd.min is not None and density < pd.min:
            errors.append(
                f"fidelity: {fixture.path.name}: pattern_density[{i}] "
                f"{density:.3f} below min {pd.min}"
            )
        if pd.max is not None and density > pd.max:
            errors.append(
                f"fidelity: {fixture.path.name}: pattern_density[{i}] "
                f"{density:.3f} above max {pd.max}"
            )

    return errors


def discover_fixtures(target: Path) -> list[Path]:
    """Return paths of fixture files under ``<target>/.kanon/fidelity/``.

    Excludes ``.dogfood.md`` capture files, files starting with ``_``, and
    ``README.md``. Returns empty list when the directory does not exist.
    """
    fidelity_dir = target / ".kanon" / "fidelity"
    if not fidelity_dir.is_dir():
        return []
    return sorted(
        p
        for p in fidelity_dir.glob("*.md")
        if not p.name.endswith(".dogfood.md")
        and not p.name.startswith("_")
        and p.name != "README.md"
    )


def dogfood_path_for(fixture_path: Path) -> Path:
    """Return the expected ``.dogfood.md`` capture path for a fixture file."""
    return fixture_path.with_name(fixture_path.stem + ".dogfood.md")


def _spec_sha(path: Path) -> str:
    """Return ``sha256:<hex>`` of raw file bytes."""
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _accepted_or_draft_specs(specs_dir: Path) -> list[Path]:
    """Return sorted spec paths with status accepted or draft."""
    result: list[Path] = []
    if not specs_dir.is_dir():
        return result
    for p in sorted(specs_dir.glob("*.md")):
        if p.name.startswith("_") or p.name == "README.md":
            continue
        fm = _parse_frontmatter(p.read_text(encoding="utf-8"))
        if fm.get("status") in ("accepted", "draft"):
            result.append(p)
    return result


def _fixture_shas(spec_path: Path, target: Path) -> dict[str, str]:
    """Extract unique fixture file paths from invariant_coverage and compute their SHAs."""
    fm = _parse_frontmatter(spec_path.read_text(encoding="utf-8"))
    coverage = fm.get("invariant_coverage")
    if not coverage or not isinstance(coverage, dict):
        return {}
    paths: set[str] = set()
    for targets in coverage.values():
        if not isinstance(targets, list):
            continue
        for t in targets:
            # Strip ::test_func suffix to get the file path
            paths.add(t.split("::")[0])
    result: dict[str, str] = {}
    for fp in sorted(paths):
        full = target / fp
        if full.is_file():
            result[fp] = _spec_sha(full)
    return result
