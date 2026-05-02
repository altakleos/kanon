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
    PatternDensityEntry,
    WordShareBand,
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
    anchor and that ADR-0029 / ADR-0031 both exist (the spec→ADR
    backreference chain is intact). ADR-0031 was renumbered from 0030
    during the Track-1 rebase: PR-34 took the 0030 slot for the
    recovery-model ADR between Track 0 and Track 1.
    """
    spec = _REPO_ROOT / "docs" / "specs" / "verification-contract.md"
    text = spec.read_text(encoding="utf-8")
    assert "INV-verification-contract-fidelity-replay-carveout" in text
    assert (
        _REPO_ROOT / "docs" / "decisions" / "0029-verification-fidelity-replay-carveout.md"
    ).is_file()
    assert (_REPO_ROOT / "docs" / "decisions" / "0031-fidelity-aspect.md").is_file()


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
    """Depth-1 sub-manifest declares protocols (including fidelity-discipline), no files."""
    from kanon._manifest import _load_aspect_manifest

    sub = _load_aspect_manifest("kanon-fidelity")
    assert sub["depth-0"] == {"files": [], "protocols": [], "sections": []}
    depth1 = sub["depth-1"]
    assert depth1["files"] == []
    assert "fidelity-fixture-authoring.md" in depth1["protocols"]
    assert "fidelity-discipline.md" in depth1["protocols"]
    proto = (
        _REPO_ROOT
        / "src/kanon_reference/aspects/kanon_fidelity/protocols/fidelity-fixture-authoring.md"
    )
    assert proto.is_file()
    proto2 = (
        _REPO_ROOT
        / "src/kanon_reference/aspects/kanon_fidelity/protocols/fidelity-discipline.md"
    )
    assert proto2.is_file()


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
    turn_format: str = "colon",
    word_share: WordShareBand | None = None,
    pattern_density: tuple[PatternDensityEntry, ...] = (),
) -> Fixture:
    return Fixture(
        path=Path(path_name),
        protocol=protocol,
        actor=actor,
        turn_format=turn_format,
        forbidden_phrases=forbidden_phrases,
        required_one_of=required_one_of,
        required_all_of=required_all_of,
        word_share=word_share,
        pattern_density=pattern_density,
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


# --- _verify.py coverage: check_fidelity_lock error paths ---


def test_check_fidelity_lock_malformed_lock_returns_early(tmp_path: Path) -> None:
    """A fidelity.lock that is not a dict with 'entries' returns early."""
    from kanon._verify import check_fidelity_lock

    (tmp_path / ".kanon").mkdir(parents=True)
    (tmp_path / ".kanon" / "fidelity.lock").write_text("just a string\n")
    warnings: list[str] = []
    check_fidelity_lock(tmp_path, 2, warnings, lambda p: "sha", lambda d: [])
    assert warnings == []


def test_check_fidelity_lock_missing_fixture_warning(tmp_path: Path) -> None:
    """A fixture referenced in fidelity.lock that no longer exists produces a warning."""
    from kanon._verify import check_fidelity_lock

    (tmp_path / ".kanon").mkdir(parents=True)
    lock = {
        "entries": {
            "my-spec": {
                "spec_sha": "abc",
                "fixture_shas": {"tests/fixtures/gone.txt": "def"},
            }
        }
    }
    (tmp_path / ".kanon" / "fidelity.lock").write_text(
        yaml.dump(lock), encoding="utf-8"
    )
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    (tmp_path / "docs" / "specs" / "my-spec.md").write_text("content")
    warnings: list[str] = []
    check_fidelity_lock(
        tmp_path, 2, warnings,
        spec_sha_fn=lambda p: "abc",
        accepted_specs_fn=lambda d: [],
    )
    assert any("no longer exists" in w for w in warnings)


def test_check_fidelity_lock_untracked_spec_warning(tmp_path: Path) -> None:
    """A spec not tracked in fidelity.lock produces a warning."""
    from kanon._verify import check_fidelity_lock

    (tmp_path / ".kanon").mkdir(parents=True)
    (tmp_path / ".kanon" / "fidelity.lock").write_text(
        yaml.dump({"entries": {}}), encoding="utf-8"
    )
    specs_dir = tmp_path / "docs" / "specs"
    specs_dir.mkdir(parents=True)
    untracked = specs_dir / "untracked.md"
    untracked.write_text("content")
    warnings: list[str] = []
    check_fidelity_lock(
        tmp_path, 2, warnings,
        spec_sha_fn=lambda p: "sha",
        accepted_specs_fn=lambda d: [untracked],
    )
    assert any("not tracked in fidelity.lock" in w for w in warnings)


# --- _verify.py coverage: check_verified_by error paths ---


def test_check_verified_by_skips_non_accepted_specs(tmp_path: Path) -> None:
    """Specs with status != 'accepted' are skipped."""
    from kanon._verify import check_verified_by

    specs_dir = tmp_path / "docs" / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "draft.md").write_text(
        "---\nstatus: draft\n---\n<!-- INV-draft-foo-bar -->\n"
    )
    warnings: list[str] = []
    check_verified_by(tmp_path, 2, warnings)
    assert warnings == []


def test_check_verified_by_missing_invariant_coverage(tmp_path: Path) -> None:
    """An accepted spec with anchors but missing invariant_coverage produces a warning."""
    from kanon._verify import check_verified_by

    specs_dir = tmp_path / "docs" / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "feature.md").write_text(
        "---\nstatus: accepted\n---\n<!-- INV-feature-foo-bar -->\n"
    )
    warnings: list[str] = []
    check_verified_by(tmp_path, 2, warnings)
    assert any("missing invariant_coverage" in w for w in warnings)


# --- _verify.py coverage: run_project_validators error paths ---


def test_run_project_validators_manifest_load_failure(tmp_path: Path) -> None:
    """A project-aspect whose manifest fails to load records an error."""
    from unittest.mock import patch

    from kanon._verify import run_project_validators

    errors: list[str] = []
    warnings: list[str] = []
    with patch(
        "kanon._verify._aspect_validators",
        side_effect=Exception("manifest broken"),
    ):
        run_project_validators(
            tmp_path, {"project-broken": 1}, errors, warnings,
        )
    assert any("failed to load manifest" in e for e in errors)


def test_run_project_validators_non_callable_check(tmp_path: Path) -> None:
    """A validator module without a callable `check` records an error."""
    import types
    from unittest.mock import patch

    from kanon._verify import run_project_validators

    fake_module = types.ModuleType("fake_validator")
    fake_module.check = "not-callable"  # type: ignore[attr-defined]
    errors: list[str] = []
    warnings: list[str] = []
    with patch("kanon._verify._aspect_validators", return_value=["fake_validator"]), \
         patch("importlib.import_module", return_value=fake_module):
        run_project_validators(
            tmp_path, {"project-test": 1}, errors, warnings,
        )
    assert any("no callable `check" in e for e in errors)


def test_run_project_validators_check_exception(tmp_path: Path) -> None:
    """A validator whose check() raises records the exception as an error."""
    import types
    from unittest.mock import patch

    from kanon._verify import run_project_validators

    fake_module = types.ModuleType("fake_validator")

    def bad_check(target, errors, warnings):
        raise RuntimeError("boom")

    fake_module.check = bad_check  # type: ignore[attr-defined]
    errors: list[str] = []
    warnings: list[str] = []
    with patch("kanon._verify._aspect_validators", return_value=["fake_validator"]), \
         patch("importlib.import_module", return_value=fake_module):
        run_project_validators(
            tmp_path, {"project-test": 1}, errors, warnings,
        )
    assert any("raised RuntimeError" in e for e in errors)


def test_run_project_validators_import_failure(tmp_path: Path) -> None:
    """A validator module that fails to import records an error."""
    from unittest.mock import patch

    from kanon._verify import run_project_validators

    errors: list[str] = []
    warnings: list[str] = []
    with patch("kanon._verify._aspect_validators", return_value=["no.such.module"]), \
         patch("importlib.import_module", side_effect=ImportError("not found")):
        run_project_validators(
            tmp_path, {"project-test": 1}, errors, warnings,
        )
    assert any("import failed" in e for e in errors)


def test_run_project_validators_adds_target_to_sys_path(tmp_path: Path) -> None:
    """run_project_validators temporarily adds *target* to sys.path so that
    project validators using relative module paths (e.g. ``ci.validators.foo``)
    are importable without the caller setting PYTHONPATH."""
    import sys
    from unittest.mock import patch

    from kanon._verify import run_project_validators

    # Create a validator module inside the target directory.
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "val.py").write_text(
        "def check(target, errors, warnings):\n"
        "    errors.append('syspath-validator-ran')\n",
        encoding="utf-8",
    )

    # Ensure the target is NOT already on sys.path.
    target_str = str(tmp_path)
    assert target_str not in sys.path

    errors: list[str] = []
    warnings: list[str] = []
    with patch("kanon._verify._aspect_validators", return_value=["mypkg.val"]):
        run_project_validators(
            tmp_path, {"project-test": 1}, errors, warnings,
        )

    # The validator ran successfully — it was importable from target.
    assert "syspath-validator-ran" in errors
    # sys.path is cleaned up after the call.
    assert target_str not in sys.path


# --- _verify.py coverage: check_fidelity_assertions edge cases ---


def test_check_fidelity_assertions_no_fixtures_returns_early(tmp_path: Path) -> None:
    """When the fidelity dir exists but has no fixtures, no errors or warnings."""
    (tmp_path / ".kanon" / "fidelity").mkdir(parents=True)
    errors: list[str] = []
    warnings: list[str] = []
    check_fidelity_assertions(tmp_path, {"kanon-fidelity": 1}, errors, warnings)
    assert errors == []
    assert warnings == []


def test_check_fidelity_assertions_parse_error_propagated(tmp_path: Path) -> None:
    """A fixture with parse errors propagates them as errors."""
    fidelity = tmp_path / ".kanon" / "fidelity"
    _write_fixture(
        fidelity / "bad.md",
        "---\nforbidden_phrases:\n  - foo\n---\nbody\n",
    )
    errors: list[str] = []
    warnings: list[str] = []
    check_fidelity_assertions(tmp_path, {"kanon-fidelity": 1}, errors, warnings)
    assert len(errors) > 0
    assert any("'protocol'" in e or "'actor'" in e for e in errors)


# --- ADR-0033: quantitative families and turn-format extensibility ---


def test_bracket_turn_marker_extraction(tmp_path: Path) -> None:
    """Bracket turn markers [ACTOR] are extracted when turn_format=bracket."""
    from kanon._fidelity import extract_actor_text

    dogfood = (
        "[USER] Hello there.\n"
        "\n"
        "[AGENT] Working in worktree.\n"
        "\n"
        "[USER] Thanks.\n"
    )
    text, count = extract_actor_text(dogfood, "AGENT", turn_format="bracket")
    assert count == 1
    assert "Working in worktree" in text


def test_colon_default_when_turn_format_absent(tmp_path: Path) -> None:
    """When turn_format is not specified, colon grammar is used (backward compat)."""
    from kanon._fidelity import extract_actor_text

    dogfood = "AGENT: Hello world.\n"
    text, count = extract_actor_text(dogfood, "AGENT")
    assert count == 1
    assert "Hello world" in text


def test_bracket_format_ignores_colon_markers(tmp_path: Path) -> None:
    """Bracket format does not match colon-style markers."""
    from kanon._fidelity import extract_actor_text

    dogfood = "AGENT: Hello world.\n"
    text, count = extract_actor_text(dogfood, "AGENT", turn_format="bracket")
    assert count == 0
    assert text == ""


def test_word_share_within_band_passes(tmp_path: Path) -> None:
    """word_share within [min, max] produces no errors."""
    from kanon._fidelity import Fixture, WordShareBand, evaluate_fixture

    fixture = Fixture(
        path=tmp_path / "test.md",
        protocol="test",
        actor="AGENT",
        turn_format="colon",
        forbidden_phrases=(),
        required_one_of=(),
        required_all_of=(),
        word_share=WordShareBand(min=0.2, max=0.8),
        pattern_density=(),
    )
    # AGENT has ~50% of words
    dogfood = "USER: one two three\nAGENT: four five six\n"
    errors = evaluate_fixture(fixture, dogfood)
    assert not errors


def test_word_share_below_min_fails(tmp_path: Path) -> None:
    """word_share below min produces an error."""
    from kanon._fidelity import Fixture, WordShareBand, evaluate_fixture

    fixture = Fixture(
        path=tmp_path / "test.md",
        protocol="test",
        actor="AGENT",
        turn_format="colon",
        forbidden_phrases=(),
        required_one_of=(),
        required_all_of=(),
        word_share=WordShareBand(min=0.8, max=None),
        pattern_density=(),
    )
    # AGENT has ~50% of words, below min 0.8
    dogfood = "USER: one two three\nAGENT: four five six\n"
    errors = evaluate_fixture(fixture, dogfood)
    assert any("word_share" in e and "below min" in e for e in errors)


def test_word_share_above_max_fails(tmp_path: Path) -> None:
    """word_share above max produces an error."""
    from kanon._fidelity import Fixture, WordShareBand, evaluate_fixture

    fixture = Fixture(
        path=tmp_path / "test.md",
        protocol="test",
        actor="AGENT",
        turn_format="colon",
        forbidden_phrases=(),
        required_one_of=(),
        required_all_of=(),
        word_share=WordShareBand(min=None, max=0.2),
        pattern_density=(),
    )
    # AGENT has ~50% of words, above max 0.2
    dogfood = "USER: one two three\nAGENT: four five six\n"
    errors = evaluate_fixture(fixture, dogfood)
    assert any("word_share" in e and "above max" in e for e in errors)


def test_pattern_density_within_band_passes(tmp_path: Path) -> None:
    """pattern_density within band produces no errors."""
    from kanon._fidelity import Fixture, PatternDensityEntry, evaluate_fixture

    fixture = Fixture(
        path=tmp_path / "test.md",
        protocol="test",
        actor="AGENT",
        turn_format="colon",
        forbidden_phrases=(),
        required_one_of=(),
        required_all_of=(),
        word_share=None,
        pattern_density=(PatternDensityEntry(
            patterns=(r"\?",),
            strip_code_fences=False,
            min=0.5,
            max=2.0,
        ),),
    )
    # 1 turn, 1 question mark -> density 1.0, within [0.5, 2.0]
    dogfood = "AGENT: What do you think?\n"
    errors = evaluate_fixture(fixture, dogfood)
    assert not errors


def test_pattern_density_below_min_fails(tmp_path: Path) -> None:
    """pattern_density below min produces an error."""
    from kanon._fidelity import Fixture, PatternDensityEntry, evaluate_fixture

    fixture = Fixture(
        path=tmp_path / "test.md",
        protocol="test",
        actor="AGENT",
        turn_format="colon",
        forbidden_phrases=(),
        required_one_of=(),
        required_all_of=(),
        word_share=None,
        pattern_density=(PatternDensityEntry(
            patterns=(r"\?",),
            strip_code_fences=False,
            min=2.0,
            max=None,
        ),),
    )
    # 1 turn, 1 question mark -> density 1.0, below min 2.0
    dogfood = "AGENT: What do you think?\n"
    errors = evaluate_fixture(fixture, dogfood)
    assert any("pattern_density" in e and "below min" in e for e in errors)


def test_pattern_density_above_max_fails(tmp_path: Path) -> None:
    """pattern_density above max produces an error."""
    from kanon._fidelity import Fixture, PatternDensityEntry, evaluate_fixture

    fixture = Fixture(
        path=tmp_path / "test.md",
        protocol="test",
        actor="AGENT",
        turn_format="colon",
        forbidden_phrases=(),
        required_one_of=(),
        required_all_of=(),
        word_share=None,
        pattern_density=(PatternDensityEntry(
            patterns=(r"\?",),
            strip_code_fences=False,
            min=None,
            max=0.5,
        ),),
    )
    # 1 turn, 1 question mark -> density 1.0, above max 0.5
    dogfood = "AGENT: What do you think?\n"
    errors = evaluate_fixture(fixture, dogfood)
    assert any("pattern_density" in e and "above max" in e for e in errors)


def test_pattern_density_strip_code_fences(tmp_path: Path) -> None:
    """strip_code_fences removes fenced blocks before counting."""
    from kanon._fidelity import Fixture, PatternDensityEntry, evaluate_fixture

    fixture = Fixture(
        path=tmp_path / "test.md",
        protocol="test",
        actor="AGENT",
        turn_format="colon",
        forbidden_phrases=(),
        required_one_of=(),
        required_all_of=(),
        word_share=None,
        pattern_density=(PatternDensityEntry(
            patterns=(r"\?",),
            strip_code_fences=True,
            min=None,
            max=0.0,
        ),),
    )
    # The ? is inside a code fence, should be stripped
    dogfood = "AGENT: Here is code:\n```\nprint('hello?')\n```\nDone.\n"
    errors = evaluate_fixture(fixture, dogfood)
    assert not errors, f"Expected no errors but got: {errors}"


def test_pattern_density_multiple_patterns(tmp_path: Path) -> None:
    """Multiple patterns in one entry are unioned for counting."""
    from kanon._fidelity import Fixture, PatternDensityEntry, evaluate_fixture

    fixture = Fixture(
        path=tmp_path / "test.md",
        protocol="test",
        actor="AGENT",
        turn_format="colon",
        forbidden_phrases=(),
        required_one_of=(),
        required_all_of=(),
        word_share=None,
        pattern_density=(PatternDensityEntry(
            patterns=(r"(?i)let me explain", r"(?i)the answer is"),
            strip_code_fences=False,
            min=None,
            max=0.0,
        ),),
    )
    # 1 turn with "let me explain" -> density 1.0, above max 0.0
    dogfood = "AGENT: Let me explain how this works.\n"
    errors = evaluate_fixture(fixture, dogfood)
    assert any("pattern_density" in e and "above max" in e for e in errors)


def test_parse_fixture_with_turn_format_bracket(tmp_path: Path) -> None:
    """parse_fixture accepts turn_format: bracket."""
    from kanon._fidelity import parse_fixture

    fixture_path = tmp_path / "test.md"
    fixture_path.write_text(
        "---\n"
        "protocol: test\n"
        "actor: AGENT\n"
        "turn_format: bracket\n"
        "forbidden_phrases:\n"
        '  - "bad phrase"\n'
        "---\n"
        "# Test fixture\n",
        encoding="utf-8",
    )
    fixture, errors = parse_fixture(fixture_path)
    assert not errors, errors
    assert fixture is not None
    assert fixture.turn_format == "bracket"


def test_parse_fixture_invalid_turn_format(tmp_path: Path) -> None:
    """parse_fixture rejects unknown turn_format values."""
    from kanon._fidelity import parse_fixture

    fixture_path = tmp_path / "test.md"
    fixture_path.write_text(
        "---\n"
        "protocol: test\n"
        "actor: AGENT\n"
        "turn_format: xml\n"
        "---\n"
        "# Test fixture\n",
        encoding="utf-8",
    )
    fixture, errors = parse_fixture(fixture_path)
    assert fixture is None
    assert any("turn_format" in e for e in errors)


def test_parse_fixture_word_share_invalid_band(tmp_path: Path) -> None:
    """parse_fixture rejects word_share where min > max."""
    from kanon._fidelity import parse_fixture

    fixture_path = tmp_path / "test.md"
    fixture_path.write_text(
        "---\n"
        "protocol: test\n"
        "actor: AGENT\n"
        "word_share:\n"
        "  min: 0.9\n"
        "  max: 0.1\n"
        "---\n"
        "# Test fixture\n",
        encoding="utf-8",
    )
    fixture, errors = parse_fixture(fixture_path)
    assert fixture is None
    assert any("word_share" in e and "min" in e for e in errors)


def test_existing_fixture_backward_compat(tmp_path: Path) -> None:
    """Existing fixtures without new fields continue to work."""
    from kanon._fidelity import parse_fixture

    fixture_path = tmp_path / "test.md"
    fixture_path.write_text(
        "---\n"
        "protocol: worktree-lifecycle\n"
        "actor: AGENT\n"
        'forbidden_phrases:\n'
        '  - "git worktree remove --force"\n'
        "---\n"
        "# Test fixture\n",
        encoding="utf-8",
    )
    fixture, errors = parse_fixture(fixture_path)
    assert not errors, errors
    assert fixture is not None
    assert fixture.turn_format == "colon"
    assert fixture.word_share is None
    assert fixture.pattern_density == ()


# --- Coverage gap tests: parse_fixture validation branches ---


def test_parse_fixture_pattern_density_not_a_list(tmp_path: Path) -> None:
    """pattern_density that is not a list produces an error."""
    fx = _write_fixture(
        tmp_path / "pd-str.md",
        "---\nprotocol: test\nactor: AGENT\npattern_density: oops\n---\n# body\n",
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("pattern_density must be a list" in e for e in errors)


def test_parse_fixture_pattern_density_entry_not_a_dict(tmp_path: Path) -> None:
    """A bare string entry in pattern_density produces an error."""
    fx = _write_fixture(
        tmp_path / "pd-bare.md",
        "---\nprotocol: test\nactor: AGENT\npattern_density:\n  - bare_string\n---\n# body\n",
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("must be a mapping" in e for e in errors)


def test_parse_fixture_pattern_density_single_pattern_key(tmp_path: Path) -> None:
    """A single 'pattern' key (not 'patterns') is accepted."""
    fx = _write_fixture(
        tmp_path / "pd-single.md",
        "---\nprotocol: test\nactor: AGENT\npattern_density:\n  - pattern: foo\n---\n# body\n",
    )
    fixture, errors = parse_fixture(fx)
    assert not errors
    assert fixture is not None
    assert fixture.pattern_density[0].patterns == ("foo",)


def test_parse_fixture_pattern_density_patterns_not_a_list(tmp_path: Path) -> None:
    """patterns: 42 (not a list, no 'pattern' key) produces an error."""
    fx = _write_fixture(
        tmp_path / "pd-notlist.md",
        "---\nprotocol: test\nactor: AGENT\npattern_density:\n  - patterns: 42\n---\n# body\n",
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("patterns must be a list" in e for e in errors)


def test_parse_fixture_pattern_density_empty_patterns(tmp_path: Path) -> None:
    """Entry with neither 'pattern' nor 'patterns' produces an error."""
    fx = _write_fixture(
        tmp_path / "pd-empty.md",
        "---\nprotocol: test\nactor: AGENT\npattern_density:\n  - min: 1\n---\n# body\n",
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("must declare pattern or patterns" in e for e in errors)


def test_parse_fixture_pattern_density_min_not_a_number(tmp_path: Path) -> None:
    """pattern_density entry with non-numeric min produces an error."""
    fx = _write_fixture(
        tmp_path / "pd-minstr.md",
        '---\nprotocol: test\nactor: AGENT\npattern_density:\n  - pattern: foo\n    min: "high"\n---\n# body\n',
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("min must be a number" in e for e in errors)


def test_parse_fixture_pattern_density_max_not_a_number(tmp_path: Path) -> None:
    """pattern_density entry with non-numeric max produces an error."""
    fx = _write_fixture(
        tmp_path / "pd-maxstr.md",
        '---\nprotocol: test\nactor: AGENT\npattern_density:\n  - pattern: foo\n    max: "low"\n---\n# body\n',
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("max must be a number" in e for e in errors)


def test_parse_fixture_pattern_density_min_gt_max(tmp_path: Path) -> None:
    """pattern_density entry with min > max produces an error."""
    fx = _write_fixture(
        tmp_path / "pd-minmax.md",
        "---\nprotocol: test\nactor: AGENT\npattern_density:\n  - pattern: foo\n    min: 10\n    max: 1\n---\n# body\n",
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("min" in e and ">" in e and "max" in e for e in errors)


def test_parse_fixture_pattern_density_non_string_pattern(tmp_path: Path) -> None:
    """A non-string entry in patterns list produces an error."""
    fx = _write_fixture(
        tmp_path / "pd-nonstr.md",
        "---\nprotocol: test\nactor: AGENT\npattern_density:\n  - patterns:\n      - 42\n---\n# body\n",
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("pattern must be a string" in e for e in errors)


def test_parse_fixture_pattern_density_invalid_regex(tmp_path: Path) -> None:
    """An invalid regex in pattern_density produces an error."""
    fx = _write_fixture(
        tmp_path / "pd-badre.md",
        '---\nprotocol: test\nactor: AGENT\npattern_density:\n  - patterns:\n      - "["\n---\n# body\n',
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("invalid regex" in e for e in errors)


def test_parse_fixture_pattern_density_valid_entry(tmp_path: Path) -> None:
    """A fully valid pattern_density entry parses correctly."""
    body = (
        "---\nprotocol: test\nactor: AGENT\npattern_density:\n"
        "  - patterns:\n      - foo\n      - bar\n"
        "    min: 1\n    max: 5\n---\n# body\n"
    )
    fx = _write_fixture(tmp_path / "pd-valid.md", body)
    fixture, errors = parse_fixture(fx)
    assert not errors
    assert fixture is not None
    assert len(fixture.pattern_density) == 1
    assert fixture.pattern_density[0].patterns == ("foo", "bar")
    assert fixture.pattern_density[0].min == 1.0
    assert fixture.pattern_density[0].max == 5.0


def test_parse_fixture_word_share_not_a_dict(tmp_path: Path) -> None:
    """word_share that is not a mapping produces an error."""
    fx = _write_fixture(
        tmp_path / "ws-str.md",
        "---\nprotocol: test\nactor: AGENT\nword_share: oops\n---\n# body\n",
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("word_share must be a mapping" in e for e in errors)


def test_parse_fixture_word_share_min_not_a_number(tmp_path: Path) -> None:
    """word_share.min that is not a number produces an error."""
    fx = _write_fixture(
        tmp_path / "ws-minstr.md",
        '---\nprotocol: test\nactor: AGENT\nword_share:\n  min: "high"\n---\n# body\n',
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("word_share.min must be a number" in e for e in errors)


def test_parse_fixture_word_share_max_not_a_number(tmp_path: Path) -> None:
    """word_share.max that is not a number produces an error."""
    fx = _write_fixture(
        tmp_path / "ws-maxstr.md",
        '---\nprotocol: test\nactor: AGENT\nword_share:\n  max: "low"\n---\n# body\n',
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("word_share.max must be a number" in e for e in errors)


def test_parse_fixture_forbidden_phrases_not_a_list(tmp_path: Path) -> None:
    """forbidden_phrases that is not a list produces an error."""
    fx = _write_fixture(
        tmp_path / "fp-int.md",
        "---\nprotocol: test\nactor: AGENT\nforbidden_phrases: 42\n---\n# body\n",
    )
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("forbidden_phrases must be a list" in e for e in errors)


def test_parse_fixture_unreadable_file(tmp_path: Path) -> None:
    """An unreadable fixture file produces a 'cannot read fixture' error."""
    import os
    import sys

    if sys.platform == "win32":
        return  # chmod 000 is not effective on Windows
    fx = _write_fixture(tmp_path / "unreadable.md", "---\nprotocol: test\nactor: AGENT\n---\n")
    try:
        os.chmod(str(fx), 0o000)
        fixture, errors = parse_fixture(fx)
        assert fixture is None
        assert any("cannot read fixture" in e for e in errors)
    finally:
        os.chmod(str(fx), 0o644)


def test_parse_fixture_no_frontmatter(tmp_path: Path) -> None:
    """A file with no YAML frontmatter markers produces an error."""
    fx = _write_fixture(tmp_path / "nofm.md", "# No frontmatter here\nJust text.\n")
    fixture, errors = parse_fixture(fx)
    assert fixture is None
    assert any("missing or malformed YAML frontmatter" in e for e in errors)


def test_evaluate_fixture_no_turn_markers(tmp_path: Path) -> None:
    """Dogfood text with no turn markers does not crash; returns zero-turns error."""
    fixture = Fixture(
        path=tmp_path / "test.md",
        protocol="test",
        actor="AGENT",
        turn_format="colon",
        forbidden_phrases=(),
        required_one_of=(),
        required_all_of=(),
        word_share=None,
        pattern_density=(),
    )
    errors = evaluate_fixture(fixture, "some random text with no markers")
    assert any("zero turns" in e for e in errors)


def test_parse_fixture_word_share_valid(tmp_path: Path) -> None:
    """A valid word_share mapping parses into a WordShareBand on the fixture."""
    fx = _write_fixture(
        tmp_path / "ws-valid.md",
        "---\nprotocol: test\nactor: AGENT\nword_share:\n  min: 0.2\n  max: 0.8\n---\n# body\n",
    )
    fixture, errors = parse_fixture(fx)
    assert not errors
    assert fixture is not None
    assert fixture.word_share == WordShareBand(min=0.2, max=0.8)


# --- Error-path tests ---


def test_parse_fixture_unreadable_file_raw(tmp_path: Path) -> None:
    """parse_fixture returns error for unreadable file (raw path variant)."""
    import os

    from kanon._fidelity import parse_fixture

    bad = tmp_path / "bad.fixture.md"
    bad.write_text("content")
    os.chmod(str(bad), 0o000)
    try:
        fixture, errors = parse_fixture(bad)
        assert fixture is None
        assert any("cannot read" in e for e in errors)
    finally:
        os.chmod(str(bad), 0o644)


def test_parse_fixture_missing_frontmatter(tmp_path: Path) -> None:
    """parse_fixture returns error for file without YAML frontmatter."""
    from kanon._fidelity import parse_fixture

    bad = tmp_path / "no-fm.fixture.md"
    bad.write_text("Just plain text, no frontmatter.\n")
    fixture, errors = parse_fixture(bad)
    assert fixture is None
    assert any("frontmatter" in e for e in errors)


def test_parse_fixture_missing_protocol(tmp_path: Path) -> None:
    """parse_fixture returns error when protocol field is missing."""
    from kanon._fidelity import parse_fixture

    bad = tmp_path / "no-proto.fixture.md"
    bad.write_text(
        "---\nactor: agent\nturn-format: plain\n---\n# Test\n",
        encoding="utf-8",
    )
    fixture, errors = parse_fixture(bad)
    assert fixture is None
    assert any("protocol" in e.lower() for e in errors)
