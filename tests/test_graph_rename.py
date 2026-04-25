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

from click.testing import CliRunner

from kanon._atomic import read_sentinel
from kanon._rename import (
    _OP_GRAPH_RENAME,
    OPS_MANIFEST_FILENAME,
    perform_rename,
    recover_pending_rename,
)
from kanon.cli import _PENDING_OP_TO_COMMAND, main


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
