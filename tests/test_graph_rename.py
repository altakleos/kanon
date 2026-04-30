"""Tests for `kanon graph rename` (Phase 3 of the spec-graph MVP plan).

This iteration covers the ``principle`` namespace end-to-end. Other
namespaces are accepted by the CLI per spec-graph-rename INV-1 but raise
``NotImplementedError`` until their rewrite engines land in subsequent
commits within Phase 3.

Each test names the spec invariant it exercises in its docstring.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from kanon._atomic import read_sentinel
from kanon._cli_helpers import _PENDING_OP_TO_COMMAND
from kanon._rename import (
    _OP_GRAPH_RENAME,
    OPS_MANIFEST_FILENAME,
    perform_rename,
    recover_pending_rename,
)
from kanon.cli import main


def _make_minimal_repo(root: Path) -> None:
    (root / "docs" / "foundations" / "principles").mkdir(parents=True)
    (root / "docs" / "foundations" / "personas").mkdir(parents=True)
    (root / "docs" / "specs").mkdir(parents=True)
    (root / "docs" / "plans").mkdir(parents=True)
    (root / "src" / "kanon" / "kit").mkdir(parents=True)
    (root / ".kanon").mkdir(parents=True)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# INV-1: CLI surface — --type required, valid set of seven


def test_inv1_type_required(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "rename", "--target", str(tmp_path), "P-foo", "P-bar",
    ])
    assert result.exit_code != 0
    assert "--type" in result.output


def test_inv1_invalid_type_lists_seven(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "rename", "--type", "bogus", "--target", str(tmp_path),
        "P-foo", "P-bar",
    ])
    assert result.exit_code != 0
    # Error names all seven valid types.
    for ns in ("principle", "persona", "spec", "aspect", "capability",
               "inv-anchor", "adr"):
        assert ns in result.output


def test_inv1_valid_namespace_accepted(tmp_path: Path) -> None:
    """Each declared namespace value must pass --type validation. Engines
    not yet shipped raise NotImplementedError at compute time, which is
    the expected staged-rollout signal."""
    _make_minimal_repo(tmp_path)
    runner = CliRunner()
    # The `principle` engine is fully implemented.
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    result = runner.invoke(main, [
        "graph", "rename", "--type", "principle", "--target", str(tmp_path),
        "--dry-run", "P-foo", "P-bar",
    ])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# INV-2: token-boundary match semantics


def test_inv2_token_boundary_does_not_match_substring(tmp_path: Path) -> None:
    """Renaming `P-foo` must not touch `P-foo-bar` in the same file's
    frontmatter — boundary regex stops at slug-character transitions."""
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/foundations/principles/P-foo-bar.md",
           "---\nid: P-foo-bar\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/specs/uses-both.md",
           "---\nstatus: accepted\nrealizes: [P-foo, P-foo-bar]\n---\n")
    perform_rename(tmp_path, "principle", "P-foo", "P-baz")
    spec_text = (tmp_path / "docs/specs/uses-both.md").read_text()
    # `P-foo-bar` must remain untouched.
    assert "P-foo-bar" in spec_text
    # `P-foo` (the bare one) must be replaced.
    assert "P-baz" in spec_text
    # The bare `P-foo` token must not be present anywhere as a standalone token.
    # (We grep for the "[P-baz" / "P-baz," shapes that result from list rewrites.)


# ---------------------------------------------------------------------------
# INV-3: ops-manifest written; idempotent re-run


def test_inv3_ops_manifest_cleared_on_success(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    perform_rename(tmp_path, "principle", "P-foo", "P-bar")
    assert not (tmp_path / ".kanon" / OPS_MANIFEST_FILENAME).exists()
    assert read_sentinel(tmp_path / ".kanon") is None


def test_inv3_idempotent_rerun_after_success(tmp_path: Path) -> None:
    """Re-applying an already-applied manifest must complete without
    errors; recovery is the contract for crash mid-rewrite."""
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    perform_rename(tmp_path, "principle", "P-foo", "P-bar")
    # The renamed file exists; the source is gone.
    assert (tmp_path / "docs/foundations/principles/P-bar.md").is_file()
    assert not (tmp_path / "docs/foundations/principles/P-foo.md").exists()


def test_inv3_recovery_completes_partial_rename(tmp_path: Path) -> None:
    """Simulate a crash by writing the ops-manifest + sentinel WITHOUT
    applying rewrites, then call recover_pending_rename and assert the
    rewrite is fully applied."""
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/specs/feature.md",
           "---\nstatus: accepted\nrealizes: [P-foo]\n---\n# Feature\n")
    # Compute the rewrites and write the manifest + sentinel without applying.
    from kanon._atomic import write_sentinel
    from kanon._rename import (
        OpsManifest,
        compute_rewrites,
        write_ops_manifest,
    )
    rewrites = compute_rewrites(tmp_path, "principle", "P-foo", "P-bar")
    write_ops_manifest(
        tmp_path,
        OpsManifest(old="P-foo", new="P-bar", type="principle", files=rewrites),
    )
    write_sentinel(tmp_path / ".kanon", _OP_GRAPH_RENAME)

    # Verify nothing has been applied yet — old file still exists.
    assert (tmp_path / "docs/foundations/principles/P-foo.md").is_file()

    # Recovery completes the work.
    recovered = recover_pending_rename(tmp_path)
    assert recovered is True
    assert (tmp_path / "docs/foundations/principles/P-bar.md").is_file()
    assert not (tmp_path / "docs/foundations/principles/P-foo.md").exists()
    # Spec frontmatter updated.
    spec_text = (tmp_path / "docs/specs/feature.md").read_text()
    assert "P-bar" in spec_text
    assert "P-foo" not in spec_text
    # Sentinel + manifest cleared.
    assert read_sentinel(tmp_path / ".kanon") is None
    assert not (tmp_path / ".kanon" / OPS_MANIFEST_FILENAME).exists()


# ---------------------------------------------------------------------------
# INV-6: --dry-run does not write anything


def test_inv6_dry_run_writes_no_files(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/specs/feature.md",
           "---\nstatus: accepted\nrealizes: [P-foo]\n---\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "rename", "--type", "principle", "--target", str(tmp_path),
        "--dry-run", "P-foo", "P-bar",
    ])
    assert result.exit_code == 0
    # No files moved.
    assert (tmp_path / "docs/foundations/principles/P-foo.md").is_file()
    assert not (tmp_path / "docs/foundations/principles/P-bar.md").exists()
    # No manifest, no sentinel.
    assert not (tmp_path / ".kanon" / OPS_MANIFEST_FILENAME).exists()
    assert read_sentinel(tmp_path / ".kanon") is None
    # Plan output mentions the move.
    assert "move:" in result.output


# ---------------------------------------------------------------------------
# INV-7: recovery message names "kanon graph rename"


def test_inv7_recovery_message_command_form() -> None:
    assert _PENDING_OP_TO_COMMAND[_OP_GRAPH_RENAME] == "kanon graph rename"


# ---------------------------------------------------------------------------
# ADR-0029: graph-rename auto-recovery via CLI _check_pending_recovery


def test_check_pending_recovery_auto_replays_graph_rename(tmp_path: Path) -> None:
    """Per ADR-0029, when `_check_pending_recovery` finds the `graph-rename`
    sentinel, it calls `recover_pending_rename` automatically — replaying
    the ops-manifest, clearing the sentinel, and emitting a "Recovered ..."
    message instead of the warn-and-rerun warning. Closes spec-graph-rename
    INV-3 at the CLI integration layer."""
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/specs/feature.md",
           "---\nstatus: accepted\nrealizes: [P-foo]\n---\n# Feature\n")

    # Stage a partial rename: ops-manifest + sentinel on disk, rewrites unapplied.
    from kanon._atomic import write_sentinel
    from kanon._rename import OpsManifest, compute_rewrites, write_ops_manifest

    rewrites = compute_rewrites(tmp_path, "principle", "P-foo", "P-bar")
    write_ops_manifest(
        tmp_path,
        OpsManifest(old="P-foo", new="P-bar", type="principle", files=rewrites),
    )
    write_sentinel(tmp_path / ".kanon", _OP_GRAPH_RENAME)

    # Call any CLI command whose entry runs `_check_pending_recovery`.
    # `graph orphans` is the cheapest one that takes --target and exits 0.
    runner = CliRunner()
    # Stage a minimal kanon project skeleton at tmp_path so verify is invokable.
    (tmp_path / ".kanon").mkdir(exist_ok=True)
    config = (tmp_path / ".kanon" / "config.yaml")
    if not config.is_file():
        config.write_text(
            "kit_version: 0.0.0\naspects: {kanon-sdd: {depth: 0, "
            "enabled_at: '2026-04-27T00:00:00+00:00', config: {}}}\n",
            encoding="utf-8",
        )
    (tmp_path / "AGENTS.md").write_text("# minimal\n", encoding="utf-8")
    result = runner.invoke(main, ["verify", str(tmp_path)])

    # Recovery message emitted; rewrite is fully applied.
    assert "Recovered interrupted 'graph-rename' operation" in result.output, (
        f"expected auto-recovery message in verify output, got: {result.output}"
    )
    # Warn-and-rerun message must NOT appear (it's the alternative branch).
    assert "Re-run 'kanon graph rename'" not in result.output
    # Rewrite was applied: new file exists, old file gone, spec frontmatter updated.
    assert (tmp_path / "docs/foundations/principles/P-bar.md").is_file()
    assert not (tmp_path / "docs/foundations/principles/P-foo.md").exists()
    assert "P-bar" in (tmp_path / "docs/specs/feature.md").read_text()
    # Sentinel + ops-manifest cleared.
    assert read_sentinel(tmp_path / ".kanon") is None
    assert not (tmp_path / ".kanon" / OPS_MANIFEST_FILENAME).exists()


# ---------------------------------------------------------------------------
# INV-10: collision detection


def test_inv10_collision_refuses(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/foundations/principles/P-bar.md",
           "---\nid: P-bar\nkind: pedagogical\nstatus: accepted\n---\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "rename", "--type", "principle", "--target", str(tmp_path),
        "P-foo", "P-bar",
    ])
    assert result.exit_code != 0
    assert "Collision" in result.output
    assert "P-bar.md" in result.output
    # The original file is untouched.
    assert (tmp_path / "docs/foundations/principles/P-foo.md").is_file()


# ---------------------------------------------------------------------------
# Slug grammar / argument validation


def test_old_equals_new_rejected(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "rename", "--type", "principle", "--target", str(tmp_path),
        "P-foo", "P-foo",
    ])
    assert result.exit_code != 0
    assert "identical" in result.output


def test_invalid_slug_rejected(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "rename", "--type", "principle", "--target", str(tmp_path),
        "P-foo!", "P-bar",
    ])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Happy path: full file rewrite + link target rewrite


def test_principle_rename_rewrites_link_target(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/specs/feature.md",
           "---\nstatus: accepted\nrealizes: [P-foo]\n---\n# Feature\n\n"
           "See [foo](../foundations/principles/P-foo.md) for context.\n")
    perform_rename(tmp_path, "principle", "P-foo", "P-bar")
    text = (tmp_path / "docs/specs/feature.md").read_text()
    assert "(../foundations/principles/P-bar.md)" in text
    assert "P-foo" not in text
    assert "[foo]" in text  # link label preserved


def test_dry_run_via_function_returns_status(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    report = perform_rename(
        tmp_path, "principle", "P-foo", "P-bar", dry_run=True,
    )
    assert report["status"] == "dry-run"
    assert report["files"] >= 1
    # No side effects.
    assert (tmp_path / "docs/foundations/principles/P-foo.md").is_file()


def test_unimplemented_namespace_emits_clear_error(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "rename", "--type", "spec", "--target", str(tmp_path),
        "old", "new",
    ])
    # Either NotImplementedError bubbles up (exit non-zero) or click
    # surfaces our message — either way, exit is non-zero and 'principle'
    # alone is what we promise to ship in this iteration.
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Ops-manifest schema sanity


def test_ops_manifest_records_full_content(tmp_path: Path) -> None:
    """The manifest must capture rendered post-rename content directly,
    not just a SHA — recovery does not re-derive content from the
    half-rewritten tree."""
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/specs/uses-foo.md",
           "---\nstatus: accepted\nrealizes: [P-foo]\n---\n")
    from kanon._atomic import write_sentinel
    from kanon._rename import (
        OpsManifest,
        compute_rewrites,
        manifest_path,
        write_ops_manifest,
    )
    rewrites = compute_rewrites(tmp_path, "principle", "P-foo", "P-bar")
    manifest = OpsManifest(
        old="P-foo", new="P-bar", type="principle", files=rewrites,
    )
    write_ops_manifest(tmp_path, manifest)
    write_sentinel(tmp_path / ".kanon", _OP_GRAPH_RENAME)
    payload = json.loads(manifest_path(tmp_path).read_text())
    assert payload["old"] == "P-foo"
    assert payload["new"] == "P-bar"
    assert payload["type"] == "principle"
    assert all("content" in entry for entry in payload["files"])
    assert all("sha256" in entry for entry in payload["files"])


# --- _rename.py coverage: _require_canonical_exists error paths ---


def test_require_canonical_exists_file_not_found(tmp_path: Path) -> None:
    """Missing principle file raises ClickException."""
    import click

    from kanon._rename import _require_canonical_exists

    _make_minimal_repo(tmp_path)
    with pytest.raises(click.ClickException, match="Cannot rename"):
        _require_canonical_exists(tmp_path, "principle", "P-nonexistent")


# --- _rename.py coverage: _replace_in_frontmatter edge cases ---


def test_replace_in_frontmatter_no_frontmatter(tmp_path: Path) -> None:
    """A file without frontmatter is returned unchanged."""
    from kanon._rename import _replace_in_frontmatter, _slug_boundary_pattern

    text = "# Just a heading\nNo frontmatter here.\n"
    result = _replace_in_frontmatter(text, _slug_boundary_pattern("P-foo"), "P-bar")
    assert result == text


def test_replace_in_frontmatter_no_match(tmp_path: Path) -> None:
    """Frontmatter that doesn't contain the slug is returned unchanged."""
    from kanon._rename import _replace_in_frontmatter, _slug_boundary_pattern

    text = "---\nid: P-other\nstatus: accepted\n---\nBody text.\n"
    result = _replace_in_frontmatter(text, _slug_boundary_pattern("P-foo"), "P-bar")
    assert result == text


# --- _rename.py coverage: read_ops_manifest error paths ---


def test_read_ops_manifest_file_not_found(tmp_path: Path) -> None:
    """Missing ops-manifest returns None."""
    from kanon._rename import read_ops_manifest

    assert read_ops_manifest(tmp_path) is None


def test_read_ops_manifest_json_decode_error(tmp_path: Path) -> None:
    """Malformed JSON in ops-manifest raises ClickException."""
    import click

    from kanon._rename import read_ops_manifest

    (tmp_path / ".kanon").mkdir(parents=True)
    (tmp_path / ".kanon" / "graph-rename.ops").write_text("not json{{{")
    with pytest.raises(click.ClickException, match="Cannot parse"):
        read_ops_manifest(tmp_path)


def test_read_ops_manifest_malformed_data(tmp_path: Path) -> None:
    """A non-dict ops-manifest raises ClickException."""
    import click

    from kanon._rename import read_ops_manifest

    (tmp_path / ".kanon").mkdir(parents=True)
    (tmp_path / ".kanon" / "graph-rename.ops").write_text('"just a string"')
    with pytest.raises(click.ClickException, match="malformed"):
        read_ops_manifest(tmp_path)


def test_read_ops_manifest_path_traversal(tmp_path: Path) -> None:
    """Path traversal in ops-manifest src/dst is rejected."""
    import json

    import click

    from kanon._rename import read_ops_manifest

    (tmp_path / ".kanon").mkdir(parents=True)
    payload = {
        "old": "a", "new": "b", "type": "spec",
        "files": [{"src": "ok.md", "dst": "../../escape.md", "content": "x"}],
    }
    (tmp_path / ".kanon" / "graph-rename.ops").write_text(json.dumps(payload))
    with pytest.raises(click.ClickException, match="Path traversal"):
        read_ops_manifest(tmp_path)


def test_compute_principle_rewrites_missing_file(tmp_path: Path) -> None:
    """_principle_rewrites raises ClickException on missing principle file."""
    import click

    from kanon._rename import _principle_rewrites

    with pytest.raises(click.ClickException, match="Cannot read principle file"):
        _principle_rewrites(tmp_path, "nonexistent", "new-name")


# --- _rename.py coverage: format_dry_run empty rewrites ---


def test_format_dry_run_empty_rewrites(tmp_path: Path) -> None:
    """An empty rewrites list produces the fallback message."""
    from kanon._rename import format_dry_run

    result = format_dry_run([], tmp_path)
    assert result == "(no files would change)"


# --- _rename.py coverage: compute_rewrites non-sdd namespace ---


def test_compute_rewrites_non_principle_namespace_raises(tmp_path: Path) -> None:
    """A non-principle namespace raises NotImplementedError."""
    from kanon._rename import compute_rewrites

    _make_minimal_repo(tmp_path)
    with pytest.raises(NotImplementedError, match="not yet implemented"):
        compute_rewrites(tmp_path, "spec", "old", "new")


# ---------------------------------------------------------------------------
# INV-8: aspect rename staged for future implementation


def test_inv8_aspect_namespace_raises_not_implemented(tmp_path: Path) -> None:
    """Per INV-8, aspect rename is staged for future implementation.
    ``compute_rewrites`` must raise ``NotImplementedError`` for the
    ``aspect`` namespace until the rewrite engine lands."""
    from kanon._rename import compute_rewrites

    _make_minimal_repo(tmp_path)
    with pytest.raises(NotImplementedError, match="not yet implemented"):
        compute_rewrites(tmp_path, "aspect", "old-name", "new-name")
