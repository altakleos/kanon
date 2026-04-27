"""Tests for the kanon-fidelity aspect and its replay engine.

Covers ``docs/specs/fidelity.md`` invariants:

- INV-1 aspect identity, INV-2 depth scaffolding, INV-10 stability — kit-side.
- INV-3 fixture file format — parse_fixture validation.
- INV-4 actor turn extraction grammar — extract_actor_text.
- INV-5 assertion families — evaluate_fixture.
- INV-6 aspect-gating — check_fidelity_assertions skips when capability absent.
- INV-7 text-only bounds — static inspection of _fidelity.py source.
- INV-8 failure taxonomy — error vs warning split.
- INV-9 Tier-2/Tier-3 out of scope — no `kanon transcripts capture` subcommand.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from kanon._fidelity import (
    BEHAVIOURAL_VERIFICATION_CAPABILITY,
    Fixture,
    discover_fixtures,
    dogfood_path_for,
    evaluate_fixture,
    extract_actor_text,
    parse_fixture,
)
from kanon._verify import check_fidelity_assertions

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_invariant_anchor_resolves() -> None:
    """Anchor test for INV-verification-contract-fidelity-replay-carveout.

    Asserts that the verification-contract spec carries the carve-out
    anchor and that ADR-0029 / ADR-0030 both exist (the spec→ADR
    backreference chain is intact).
    """
    spec = _REPO_ROOT / "docs" / "specs" / "verification-contract.md"
    text = spec.read_text(encoding="utf-8")
    assert "INV-verification-contract-fidelity-replay-carveout" in text
    assert (
        _REPO_ROOT / "docs" / "decisions" / "0029-verification-fidelity-replay-carveout.md"
    ).is_file()
    assert (_REPO_ROOT / "docs" / "decisions" / "0030-fidelity-aspect.md").is_file()


# --- INV-1: aspect identity (kit-registered, capability declared) ---


def test_aspect_registered() -> None:
    """kanon-fidelity must be in the kit's top manifest with the expected shape."""
    from kanon._manifest import _aspect_provides, _load_top_manifest

    top = _load_top_manifest()
    assert "kanon-fidelity" in top["aspects"]
    entry = top["aspects"]["kanon-fidelity"]
    assert entry["stability"] == "experimental"
    assert entry["depth-range"] == [0, 1]
    assert entry["default-depth"] == 1
    assert entry.get("requires", []) == []
    assert BEHAVIOURAL_VERIFICATION_CAPABILITY in _aspect_provides("kanon-fidelity")


def test_aspect_stability_experimental() -> None:
    """INV-10: first release ships as experimental."""
    from kanon._manifest import _load_top_manifest

    assert _load_top_manifest()["aspects"]["kanon-fidelity"]["stability"] == "experimental"


# --- INV-2: depth scaffolding ---


def test_depth_1_scaffolds_protocol_and_section() -> None:
    """Depth-1 sub-manifest declares one protocol + one section, no files."""
    from kanon._manifest import _load_aspect_manifest

    sub = _load_aspect_manifest("kanon-fidelity")
    assert sub["depth-0"] == {"files": [], "protocols": [], "sections": []}
    depth1 = sub["depth-1"]
    assert depth1["files"] == []
    assert depth1["protocols"] == ["fidelity-fixture-authoring.md"]
    assert "fidelity-discipline" in depth1["sections"]
    proto = (
        _REPO_ROOT
        / "src/kanon/kit/aspects/kanon-fidelity/protocols/fidelity-fixture-authoring.md"
    )
    assert proto.is_file()
    section = (
        _REPO_ROOT / "src/kanon/kit/aspects/kanon-fidelity/sections/fidelity-discipline.md"
    )
    assert section.is_file()
    body = _REPO_ROOT / "src/kanon/kit/aspects/kanon-fidelity/agents-md/depth-1.md"
    assert body.is_file()


# --- INV-3: fixture file format (parse_fixture) ---


def _write_fixture(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_fixture_frontmatter_required_keys(tmp_path: Path) -> None:
    """Missing 'protocol' or 'actor' is a hard error."""
    fx = _write_fixture(
        tmp_path / "no-keys.md",
        "---\nforbidden_phrases:\n  - foo\n---\nbody\n",
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("'protocol'" in e for e in errors)
    assert any("'actor'" in e for e in errors)

    fx2 = _write_fixture(
        tmp_path / "no-actor.md",
        "---\nprotocol: foo\n---\nbody\n",
    )
    fixture, errors = parse_fixture(fx2)
    assert fixture is None
    assert any("'actor'" in e for e in errors)


def test_fixture_assertion_lists_must_be_strings(tmp_path: Path) -> None:
    """A non-string entry in any assertion list is a hard error."""
    fx = _write_fixture(
        tmp_path / "bad-list.md",
        "---\nprotocol: p\nactor: AGENT\nforbidden_phrases:\n  - 42\n---\nbody\n",
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("must be a string" in e for e in errors)


def test_fixture_invalid_regex_is_error(tmp_path: Path) -> None:
    """A regex that fails to compile is a hard error."""
    fx = _write_fixture(
        tmp_path / "bad-regex.md",
        '---\nprotocol: p\nactor: AGENT\nrequired_one_of:\n  - "[unclosed"\n---\nbody\n',
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("invalid regex" in e for e in errors)


def test_fixture_valid_parses(tmp_path: Path) -> None:
    """A well-formed fixture parses to a Fixture instance."""
    fx = _write_fixture(
        tmp_path / "good.md",
        '---\nprotocol: p\nactor: AGENT\n'
        'forbidden_phrases:\n  - "bad"\nrequired_one_of:\n  - "good"\n---\n',
    )
    fixture, errors = parse_fixture(fx)
    assert errors == []
    assert isinstance(fixture, Fixture)
    assert fixture.protocol == "p"
    assert fixture.actor == "AGENT"
    assert fixture.forbidden_phrases == ("bad",)
    assert fixture.required_one_of == ("good",)
    assert fixture.required_all_of == ()


def test_dogfood_pairing_required(tmp_path: Path) -> None:
    """Missing paired dogfood produces a warning (INV-8), not an error."""
    fidelity = tmp_path / ".kanon" / "fidelity"
    _write_fixture(
        fidelity / "x.md",
        "---\nprotocol: x\nactor: AGENT\n---\n",
    )
    errors: list[str] = []
    warnings: list[str] = []
    check_fidelity_assertions(tmp_path, {"kanon-fidelity": 1}, errors, warnings)
    assert errors == []
    assert any("paired dogfood capture" in w and "missing" in w for w in warnings)


# --- INV-4: actor turn extraction grammar ---


def test_turn_extractor_basic() -> None:
    """A single named actor turn is extracted."""
    text = "AGENT: hello world\n"
    out, count = extract_actor_text(text, "AGENT")
    assert count == 1
    assert "hello world" in out


def test_turn_extractor_multiple_turns_concatenated() -> None:
    """Multiple turns of the same actor concatenate; other actors ignored."""
    text = "AGENT: first\nUSER: ignored\nAGENT: second\n"
    out, count = extract_actor_text(text, "AGENT")
    assert count == 2
    assert "first" in out
    assert "second" in out
    assert "ignored" not in out


def test_turn_extractor_ignores_unnamed_prose() -> None:
    """Lines outside any turn are ignored."""
    text = "Header prose\n\nAGENT: real turn\nlowercase: not-a-marker\n"
    out, count = extract_actor_text(text, "AGENT")
    assert count == 1
    assert "Header prose" not in out
    # Lowercase line is INSIDE the AGENT turn (no new marker), so is included.
    assert "lowercase: not-a-marker" in out


def test_turn_extractor_zero_turns_for_unmatched_actor() -> None:
    """An actor that never appears yields zero turns."""
    text = "USER: hi\nAGENT: hello\n"
    _, count = extract_actor_text(text, "ASSISTANT")
    assert count == 0


def test_turn_extractor_requires_uppercase_marker() -> None:
    """INV-4 grammar: lowercase markers are not turn markers."""
    text = "agent: not a turn\nAGENT: real turn\n"
    out, count = extract_actor_text(text, "AGENT")
    assert count == 1
    assert "not a turn" not in out


# --- INV-5: assertion families ---


def _fixture(
    *,
    forbidden_phrases: tuple[str, ...] = (),
    required_one_of: tuple[str, ...] = (),
    required_all_of: tuple[str, ...] = (),
    actor: str = "AGENT",
    protocol: str = "p",
    path_name: str = "anon.md",
) -> Fixture:
    return Fixture(
        path=Path(path_name),
        protocol=protocol,
        actor=actor,
        forbidden_phrases=forbidden_phrases,
        required_one_of=required_one_of,
        required_all_of=required_all_of,
    )


def test_forbidden_phrases_match_fails() -> None:
    """A matching forbidden_phrase produces one error per match."""
    fix = _fixture(forbidden_phrases=("nope", "verboten"))
    errors = evaluate_fixture(fix, "AGENT: hello nope and verboten\n")
    assert len(errors) == 2
    assert any("'nope'" in e for e in errors)
    assert any("'verboten'" in e for e in errors)


def test_forbidden_phrases_no_match_passes() -> None:
    """No forbidden match → no errors."""
    fix = _fixture(forbidden_phrases=("nope",))
    assert evaluate_fixture(fix, "AGENT: clean turn\n") == []


def test_required_one_of_no_match_fails() -> None:
    """If none of the required_one_of regexes match, exactly one error."""
    fix = _fixture(required_one_of=("alpha", "beta"))
    errors = evaluate_fixture(fix, "AGENT: gamma delta\n")
    assert len(errors) == 1
    assert "required_one_of" in errors[0]


def test_required_one_of_one_match_passes() -> None:
    """At least one required_one_of match → pass."""
    fix = _fixture(required_one_of=("alpha", "beta"))
    assert evaluate_fixture(fix, "AGENT: alpha is here\n") == []


def test_required_all_of_partial_match_fails() -> None:
    """Each missing required_all_of regex produces its own error."""
    fix = _fixture(required_all_of=("must-a", "must-b", "must-c"))
    errors = evaluate_fixture(fix, "AGENT: must-a only\n")
    assert len(errors) == 2
    assert any("'must-b'" in e for e in errors)
    assert any("'must-c'" in e for e in errors)


def test_required_all_of_full_match_passes() -> None:
    """All required_all_of regexes match → pass."""
    fix = _fixture(required_all_of=("a", "b"))
    assert evaluate_fixture(fix, "AGENT: a then b\n") == []


def test_evaluate_zero_actor_turns_is_error() -> None:
    """A dogfood with no matching actor turns is an error (INV-8)."""
    fix = _fixture(required_one_of=("anything",))
    errors = evaluate_fixture(fix, "USER: only user turns\n")
    assert len(errors) == 1
    assert "zero turns" in errors[0]


# --- INV-6: aspect-gating ---


def test_replay_skipped_when_aspect_disabled(tmp_path: Path) -> None:
    """When no aspect declares behavioural-verification, the engine emits nothing."""
    fidelity = tmp_path / ".kanon" / "fidelity"
    _write_fixture(fidelity / "x.md", "---\nprotocol: x\nactor: AGENT\n---\n")
    (fidelity / "x.dogfood.md").write_text("AGENT: hello\n", encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []
    check_fidelity_assertions(tmp_path, {"kanon-sdd": 3}, errors, warnings)
    assert errors == []
    assert warnings == []


def test_replay_runs_when_aspect_enabled(tmp_path: Path) -> None:
    """When kanon-fidelity is enabled, the engine reads fixtures and runs assertions."""
    fidelity = tmp_path / ".kanon" / "fidelity"
    _write_fixture(
        fidelity / "x.md",
        '---\nprotocol: x\nactor: AGENT\nrequired_one_of:\n  - "alpha"\n---\n',
    )
    (fidelity / "x.dogfood.md").write_text("AGENT: alpha is here\n", encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []
    check_fidelity_assertions(tmp_path, {"kanon-fidelity": 1}, errors, warnings)
    assert errors == []
    assert warnings == []


def test_replay_skipped_when_depth_zero(tmp_path: Path) -> None:
    """Depth-0 means opt-out; engine does not run even though aspect is named."""
    fidelity = tmp_path / ".kanon" / "fidelity"
    _write_fixture(fidelity / "x.md", "---\nprotocol: x\nactor: AGENT\n---\n")
    errors: list[str] = []
    warnings: list[str] = []
    check_fidelity_assertions(tmp_path, {"kanon-fidelity": 0}, errors, warnings)
    assert errors == []
    assert warnings == []


# --- INV-7: text-only bounds (static-source inspection) ---


def test_replay_engine_honours_invariant_bounds() -> None:
    """`_fidelity.py` MUST NOT import subprocess / network / test-runner modules."""
    src = (_REPO_ROOT / "src/kanon/_fidelity.py").read_text(encoding="utf-8")
    forbidden_imports = (
        "import subprocess",
        "from subprocess",
        "import socket",
        "from socket",
        "import urllib",
        "from urllib",
        "import requests",
        "from requests",
        "import importlib",  # we explicitly do NOT import consumer modules
        "from importlib",
        "import pytest",  # the engine is not a test runner
    )
    for needle in forbidden_imports:
        assert needle not in src, (
            f"_fidelity.py contains forbidden import {needle!r} — violates "
            f"INV-7 of docs/specs/fidelity.md"
        )


# --- INV-8: failure taxonomy ---


def test_assertion_failures_become_errors(tmp_path: Path) -> None:
    """A capture that triggers a forbidden phrase yields an error, not a warning."""
    fidelity = tmp_path / ".kanon" / "fidelity"
    _write_fixture(
        fidelity / "x.md",
        '---\nprotocol: x\nactor: AGENT\nforbidden_phrases:\n  - "BAD"\n---\n',
    )
    (fidelity / "x.dogfood.md").write_text("AGENT: BAD output\n", encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []
    check_fidelity_assertions(tmp_path, {"kanon-fidelity": 1}, errors, warnings)
    assert any("forbidden phrase" in e and "'BAD'" in e for e in errors)
    assert warnings == []


def test_missing_dogfood_becomes_warning(tmp_path: Path) -> None:
    """A fixture without its paired capture is a warning, not an error (INV-8)."""
    fidelity = tmp_path / ".kanon" / "fidelity"
    _write_fixture(fidelity / "x.md", "---\nprotocol: x\nactor: AGENT\n---\n")
    errors: list[str] = []
    warnings: list[str] = []
    check_fidelity_assertions(tmp_path, {"kanon-fidelity": 1}, errors, warnings)
    assert errors == []
    assert any("dogfood capture" in w and "missing" in w for w in warnings)


# --- INV-9: Tier-2/Tier-3 out of scope ---


def test_no_subprocess_or_capture_subcommand() -> None:
    """No `kanon transcripts` group or `transcripts capture` subcommand exists."""
    cli = (_REPO_ROOT / "src/kanon/cli.py").read_text(encoding="utf-8")
    assert '"transcripts"' not in cli
    assert "'transcripts'" not in cli
    assert '"capture"' not in cli
    assert "'capture'" not in cli


# --- discovery + path helpers ---


def test_discover_fixtures_excludes_dogfood_readme_and_underscore(tmp_path: Path) -> None:
    """Discovery skips .dogfood.md, README.md, and _* prefixes."""
    fidelity = tmp_path / ".kanon" / "fidelity"
    _write_fixture(fidelity / "real.md", "---\nprotocol: r\nactor: AGENT\n---\n")
    (fidelity / "real.dogfood.md").write_text("AGENT: x\n", encoding="utf-8")
    (fidelity / "README.md").write_text("# Notes\n", encoding="utf-8")
    (fidelity / "_draft.md").write_text(
        "---\nprotocol: d\nactor: AGENT\n---\n", encoding="utf-8"
    )
    found = [p.name for p in discover_fixtures(tmp_path)]
    assert found == ["real.md"]


def test_discover_fixtures_empty_when_dir_absent(tmp_path: Path) -> None:
    """Missing .kanon/fidelity/ → empty list (no AttributeError, no exception)."""
    assert discover_fixtures(tmp_path) == []


def test_dogfood_path_helper(tmp_path: Path) -> None:
    """dogfood_path_for swaps .md for .dogfood.md alongside the fixture."""
    fixture = tmp_path / ".kanon" / "fidelity" / "foo.md"
    assert dogfood_path_for(fixture).name == "foo.dogfood.md"


# --- exemplar fixture round-trips against the real engine ---


def test_repo_exemplar_fixture_passes() -> None:
    """The committed worktree-lifecycle exemplar fixture passes against its dogfood."""
    fidelity_dir = _REPO_ROOT / ".kanon" / "fidelity"
    fixture_path = fidelity_dir / "worktree-lifecycle.md"
    dogfood_path = fidelity_dir / "worktree-lifecycle.dogfood.md"
    assert fixture_path.is_file()
    assert dogfood_path.is_file()
    fixture, errors = parse_fixture(fixture_path)
    assert errors == [], f"exemplar fixture failed to parse: {errors}"
    assert fixture is not None
    eval_errors = evaluate_fixture(fixture, dogfood_path.read_text(encoding="utf-8"))
    assert eval_errors == [], f"exemplar fixture failed assertions: {eval_errors}"


def test_repo_exemplar_fixture_yaml_round_trips() -> None:
    """The exemplar fixture's frontmatter is well-formed YAML matching the schema shape."""
    fixture_path = _REPO_ROOT / ".kanon" / "fidelity" / "worktree-lifecycle.md"
    text = fixture_path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    end = text.find("\n---\n", 4)
    assert end > 0
    fm = yaml.safe_load(text[4:end])
    assert fm["protocol"] == "worktree-lifecycle"
    assert fm["actor"] == "AGENT"
    assert isinstance(fm.get("forbidden_phrases"), list)
    assert isinstance(fm.get("required_one_of"), list)


def test_breaking_dogfood_fails_exemplar() -> None:
    """Deliberately editing the dogfood to remove the audit sentence breaks the contract."""
    fixture_path = _REPO_ROOT / ".kanon" / "fidelity" / "worktree-lifecycle.md"
    fixture, errors = parse_fixture(fixture_path)
    assert errors == []
    assert fixture is not None
    broken = "AGENT: I just edited the file directly without setting up isolation.\n"
    eval_errors = evaluate_fixture(fixture, broken)
    assert any("required_one_of" in e for e in eval_errors), (
        f"expected required_one_of failure, got: {eval_errors}"
    )


def test_breaking_dogfood_with_forbidden_command_fails_exemplar() -> None:
    """The exemplar's forbidden_phrase fires when the agent uses --force teardown."""
    fixture_path = _REPO_ROOT / ".kanon" / "fidelity" / "worktree-lifecycle.md"
    fixture, errors = parse_fixture(fixture_path)
    assert errors == []
    assert fixture is not None
    broken = (
        "AGENT: Working in worktree `.worktrees/x/` on branch `wt/x`. "
        "Done editing.\n"
        "AGENT: Tearing down with git worktree remove --force x.\n"
    )
    eval_errors = evaluate_fixture(fixture, broken)
    assert any("forbidden phrase" in e for e in eval_errors), (
        f"expected forbidden_phrases failure, got: {eval_errors}"
    )
