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

import re
from dataclasses import dataclass
from pathlib import Path

from kanon._manifest import _parse_frontmatter

# The capability flag that gates the carve-out per ADR-0026 / spec INV-6.
BEHAVIOURAL_VERIFICATION_CAPABILITY = "behavioural-verification"

# Turn marker grammar (spec INV-4): an uppercase identifier followed by
# colon and at least one space or tab, anchored at column zero.
_TURN_MARKER_RE = re.compile(r"^([A-Z][A-Z0-9_]*):[ \t]+", re.MULTILINE)

# Recognised assertion-family keys (spec INV-5).
_FORBIDDEN_KEY = "forbidden_phrases"
_REQUIRED_ONE_OF_KEY = "required_one_of"
_REQUIRED_ALL_OF_KEY = "required_all_of"


@dataclass(frozen=True)
class Fixture:
    """Parsed fidelity fixture (spec INV-3)."""

    path: Path
    protocol: str
    actor: str
    forbidden_phrases: tuple[str, ...]
    required_one_of: tuple[str, ...]
    required_all_of: tuple[str, ...]


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
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                errors.append(
                    f"fidelity: {path.name}: invalid regex in {label}: "
                    f"{pattern!r} ({exc})"
                )

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
            forbidden_phrases=forbidden,
            required_one_of=one_of,
            required_all_of=all_of,
        ),
        [],
    )


def extract_actor_text(dogfood_text: str, actor: str) -> tuple[str, int]:
    """Extract joined turns whose actor matches; return (joined_text, turn_count).

    Per spec INV-4: a turn marker is a line at column zero matching
    ``^([A-Z][A-Z0-9_]*):[ \\t]+``. A turn extends from its marker line
    (inclusive) to the next marker line or end-of-file. The fixture's
    ``actor`` value is matched case-sensitively against the captured
    identifier; matching turns are joined with ``\\n``. Lines outside any
    turn are ignored.
    """
    matches = list(_TURN_MARKER_RE.finditer(dogfood_text))
    if not matches:
        return "", 0
    turns: list[str] = []
    for i, match in enumerate(matches):
        if match.group(1) != actor:
            continue
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(dogfood_text)
        # Strip a trailing newline so the joined text doesn't accumulate
        # double-blank lines between turns; the assertion engine works on
        # the joined string as a single search target.
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
    actor_text, turn_count = extract_actor_text(dogfood_text, fixture.actor)
    if turn_count == 0:
        errors.append(
            f"fidelity: {fixture.path.name}: dogfood has zero turns matching "
            f"actor {fixture.actor!r}; fixture asserts on no input"
        )
        return errors

    for pattern in fixture.forbidden_phrases:
        if re.search(pattern, actor_text):
            errors.append(
                f"fidelity: {fixture.path.name}: forbidden phrase matched: "
                f"{pattern!r}"
            )

    if fixture.required_one_of and not any(
        re.search(p, actor_text) for p in fixture.required_one_of
    ):
        errors.append(
            f"fidelity: {fixture.path.name}: no regex in required_one_of "
            f"matched: {list(fixture.required_one_of)!r}"
        )

    for pattern in fixture.required_all_of:
        if not re.search(pattern, actor_text):
            errors.append(
                f"fidelity: {fixture.path.name}: required_all_of regex did "
                f"not match: {pattern!r}"
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
