"""Tests for `kanon graph orphans` (Phase 2 of the spec-graph MVP).

Each invariant in `docs/specs/spec-graph-orphans.md` is exercised by at
least one test here. Test names cite the INV-* anchor they cover.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from kernel.cli import main


def _make_minimal_repo(root: Path) -> None:
    (root / "docs" / "foundations" / "principles").mkdir(parents=True)
    (root / "docs" / "foundations" / "personas").mkdir(parents=True)
    (root / "docs" / "specs").mkdir(parents=True)
    (root / "docs" / "plans").mkdir(parents=True)
    (root / "kernel" / "kit").mkdir(parents=True)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# INV-1: CLI surface — text and JSON formats, --type filter


def test_inv1_cli_text_default_no_orphans(tmp_path: Path) -> None:
    """An empty graph returns 'No orphans found.' in text mode."""
    _make_minimal_repo(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["graph", "orphans", "--target", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "No orphans found." in result.output


def test_inv1_cli_json_status_ok(tmp_path: Path) -> None:
    """JSON mode emits {orphans, status: 'ok'}."""
    _make_minimal_repo(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "orphans", "--target", str(tmp_path), "--format", "json",
    ])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "ok"
    assert isinstance(parsed["orphans"], dict)


def test_inv1_type_filter_restricts_namespace(tmp_path: Path) -> None:
    """--type principle reports only principle orphans."""
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-lonely.md",
           "---\nid: P-lonely\nkind: pedagogical\nstatus: accepted\n---\n")
    # An orphan persona too — must not appear under --type principle
    _write(tmp_path / "docs/foundations/personas/forgotten.md",
           "---\nid: forgotten\n---\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "orphans", "--target", str(tmp_path),
        "--type", "principle", "--format", "json",
    ])
    parsed = json.loads(result.output)
    assert "principle" in parsed["orphans"]
    assert "persona" not in parsed["orphans"]
    assert any(r["slug"] == "P-lonely" for r in parsed["orphans"]["principle"])


# ---------------------------------------------------------------------------
# INV-2: orphan definition — no inbound edges per namespace


def test_inv2_unreferenced_principle_is_orphan(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "orphans", "--target", str(tmp_path), "--format", "json",
    ])
    parsed = json.loads(result.output)
    assert any(r["slug"] == "P-foo" for r in parsed["orphans"]["principle"])


def test_inv2_principle_referenced_by_live_spec_is_not_orphan(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/specs/feature.md",
           "---\nstatus: accepted\nrealizes: [P-foo]\n---\n# Feature\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "orphans", "--target", str(tmp_path), "--format", "json",
    ])
    parsed = json.loads(result.output)
    assert all(r["slug"] != "P-foo" for r in parsed["orphans"].get("principle", []))


def test_inv2_persona_with_outbound_stresses_is_not_orphan(tmp_path: Path) -> None:
    """Persona INV-2 second clause: a persona whose `stresses:` points
    at a live spec or principle is non-orphan even without inbound."""
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/foundations/personas/critic.md",
           "---\nid: critic\nstresses: [P-foo]\n---\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "orphans", "--target", str(tmp_path), "--format", "json",
    ])
    parsed = json.loads(result.output)
    assert all(r["slug"] != "critic" for r in parsed["orphans"].get("persona", []))


def test_inv2_capability_orphan_when_no_requires_predicate(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    kit_root = tmp_path / "kernel/kit"
    _write(kit_root / "manifest.yaml", (
        "aspects:\n"
        "  alpha:\n"
        "    path: aspects/alpha\n"
        "    provides: [unused-cap]\n"
        "    requires: []\n"
    ))
    _write(kit_root / "aspects/alpha/manifest.yaml", "depth-0:\n  files: []\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "orphans", "--target", str(tmp_path), "--format", "json",
    ])
    parsed = json.loads(result.output)
    assert any(r["slug"] == "unused-cap" for r in parsed["orphans"]["capability"])


def test_inv2_capability_consumed_by_requires_is_not_orphan(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    kit_root = tmp_path / "kernel/kit"
    _write(kit_root / "manifest.yaml", (
        "aspects:\n"
        "  alpha:\n"
        "    path: aspects/alpha\n"
        "    provides: [used-cap]\n"
        "    requires: []\n"
        "  beta:\n"
        "    path: aspects/beta\n"
        "    provides: []\n"
        "    requires:\n"
        "      - used-cap\n"
    ))
    _write(kit_root / "aspects/alpha/manifest.yaml", "depth-0:\n  files: []\n")
    _write(kit_root / "aspects/beta/manifest.yaml", "depth-0:\n  files: []\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "orphans", "--target", str(tmp_path), "--format", "json",
    ])
    parsed = json.loads(result.output)
    assert all(r["slug"] != "used-cap"
               for r in parsed["orphans"].get("capability", []))


# ---------------------------------------------------------------------------
# INV-3: live-artifact scope — deferred specs don't contribute inbound


def test_inv3_deferred_spec_does_not_save_principle_from_orphan(tmp_path: Path) -> None:
    """Per orphans-spec INV-3, a deferred spec referencing a principle
    does NOT save it from being reported as orphan — its contract isn't
    load-bearing yet."""
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-future.md",
           "---\nid: P-future\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/specs/future-thing.md",
           "---\nstatus: deferred\nrealizes: [P-future]\n---\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "orphans", "--target", str(tmp_path), "--format", "json",
    ])
    parsed = json.loads(result.output)
    assert any(r["slug"] == "P-future" for r in parsed["orphans"]["principle"])


# ---------------------------------------------------------------------------
# INV-4: a deferred spec is itself never reported as an orphan


def test_inv4_deferred_spec_self_orphan_rule(tmp_path: Path) -> None:
    """A deferred spec with no inbound edges must NOT be reported as a
    spec orphan — by design, no plan serves it yet."""
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/specs/roadmap-entry.md",
           "---\nstatus: deferred\n---\n# Roadmap\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "orphans", "--target", str(tmp_path), "--format", "json",
    ])
    parsed = json.loads(result.output)
    assert all(r["slug"] != "roadmap-entry"
               for r in parsed["orphans"].get("spec", []))


def test_inv4_superseded_spec_is_excluded_too(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/specs/old-umbrella.md",
           "---\nstatus: superseded\n---\n# Old\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "orphans", "--target", str(tmp_path), "--format", "json",
    ])
    parsed = json.loads(result.output)
    assert all(r["slug"] != "old-umbrella"
               for r in parsed["orphans"].get("spec", []))


# ---------------------------------------------------------------------------
# INV-5: explicit opt-out via `orphan-exempt:`


def test_inv5_orphan_exempt_node_listed_with_flag(tmp_path: Path) -> None:
    """Exempt nodes are still listed; the JSON entry sets exempt=true and
    carries the reason. Text mode appends '(orphan-exempt: <reason>)'."""
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-conduct.md",
           "---\nid: P-conduct\nkind: pedagogical\nstatus: accepted\n"
           "orphan-exempt: true\norphan-exempt-reason: agent-conduct stance\n---\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "orphans", "--target", str(tmp_path), "--format", "json",
    ])
    parsed = json.loads(result.output)
    matching = [r for r in parsed["orphans"]["principle"] if r["slug"] == "P-conduct"]
    assert len(matching) == 1
    assert matching[0]["exempt"] is True
    assert matching[0]["reason"] == "agent-conduct stance"

    text_result = runner.invoke(main, [
        "graph", "orphans", "--target", str(tmp_path), "--type", "principle",
    ])
    assert "P-conduct" in text_result.output
    assert "orphan-exempt: agent-conduct stance" in text_result.output


# ---------------------------------------------------------------------------
# INV-6: no `--fail-on-orphan` / threshold flags


def test_inv6_no_fail_on_orphan_flag_exists(tmp_path: Path) -> None:
    """The CLI surface must NOT expose --fail-on-orphan or any threshold
    flag — orphans are informational per the spec."""
    runner = CliRunner()
    result = runner.invoke(main, ["graph", "orphans", "--help"])
    assert result.exit_code == 0
    assert "--fail-on-orphan" not in result.output
    assert "--warn-after" not in result.output
    assert "--fail-after" not in result.output


# ---------------------------------------------------------------------------
# INV-7: output shape — text and JSON


def test_inv7_text_output_one_line_per_orphan(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-aaa.md",
           "---\nid: P-aaa\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/foundations/principles/P-zzz.md",
           "---\nid: P-zzz\nkind: pedagogical\nstatus: accepted\n---\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "orphans", "--target", str(tmp_path), "--type", "principle",
    ])
    lines = [line for line in result.output.splitlines() if line.startswith("principle:")]
    assert lines == ["principle: P-aaa", "principle: P-zzz"]  # alphabetical


def test_inv7_json_shape(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "orphans", "--target", str(tmp_path), "--format", "json",
    ])
    parsed = json.loads(result.output)
    assert set(parsed.keys()) == {"orphans", "status"}
    assert parsed["status"] == "ok"
    assert isinstance(parsed["orphans"], dict)
    for ns, rows in parsed["orphans"].items():
        assert isinstance(ns, str)
        for row in rows:
            assert set(row.keys()) == {"slug", "exempt", "reason"}


# ---------------------------------------------------------------------------
# INV-9: exit code 0 even when orphans exist


def test_inv9_exit_code_zero_with_orphans(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-orphan.md",
           "---\nid: P-orphan\nkind: pedagogical\nstatus: accepted\n---\n")
    runner = CliRunner()
    result = runner.invoke(main, ["graph", "orphans", "--target", str(tmp_path)])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Real-repo smoke (regression guard)


_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_real_repo_command_succeeds() -> None:
    """The command must run cleanly against the kanon repo itself
    (status: ok, exit 0). The actual orphan list is allowed to be
    non-empty — orphans are informational findings, not errors."""
    runner = CliRunner()
    result = runner.invoke(main, [
        "graph", "orphans", "--target", str(_REPO_ROOT), "--format", "json",
    ])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "ok"
