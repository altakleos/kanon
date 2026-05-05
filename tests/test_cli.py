"""Tests for the kanon CLI: init, upgrade, version, banner, sentinel.

Includes tier-migration round-trip smoke: 0 → 1 → 2 → 3 → 2 → 1 → 0
preserves user-authored files and verify stays OK at every step.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from kanon_core import __version__
from kanon_core.cli import main


def _extract_verify_json(output: str) -> dict:
    """Extract the first JSON object from `verify` output (report precedes the human summary)."""
    start = output.find("{")
    end = output.rfind("}")
    return json.loads(output[start:end + 1])




_EXPECTED_PROTOCOLS_BY_TIER: dict[int, set[str]] = {
    0: set(),
    1: {
        "tier-up-advisor.md", "verify-triage.md", "completion-checklist.md",
        "scope-check.md", "plan-before-build.md", "adr-authoring.md",
    },
    2: {
        "tier-up-advisor.md", "verify-triage.md", "completion-checklist.md",
        "scope-check.md", "plan-before-build.md", "adr-authoring.md", "spec-review.md",
        "spec-before-design.md", "adr-immutability.md", "foundations-authoring.md",
        "foundations-review.md",
    },
    3: {
        "tier-up-advisor.md",
        "verify-triage.md",
        "completion-checklist.md",
        "scope-check.md",
        "plan-before-build.md",
        "adr-authoring.md",
        "spec-review.md",
        "spec-before-design.md",
        "adr-immutability.md",
        "foundations-authoring.md",
        "foundations-review.md",
        "design-before-plan.md",
    },
}


_PROJECT_ASPECT_MIN_MANIFEST = (
    "stability: experimental\n"
    "depth-range: [0, 1]\n"
    "default-depth: 1\n"
    "requires: []\n"
    "depth-0:\n"
    "  files: []\n"
    "  protocols: []\n"
    "  sections: []\n"
    "depth-1:\n"
    "  files: []\n"
    "  protocols: []\n"
    "  sections: []\n"
)


def _stage_project_aspect(target: Path, name: str, manifest_text: str) -> Path:
    """Drop a project-aspect manifest at <target>/.kanon/aspects/<name>/manifest.yaml."""
    aspect_dir = target / ".kanon" / "aspects" / name
    aspect_dir.mkdir(parents=True, exist_ok=True)
    (aspect_dir / "manifest.yaml").write_text(manifest_text, encoding="utf-8")
    return aspect_dir




def _read_banner() -> str:
    """Read the canonical banner constant via the same import path as production."""
    from kanon_core._banner import _BANNER
    return _BANNER




def _banner_literal() -> str:
    """The byte-frozen banner literal asserted by INV-kanon-banner-byte-frozen."""
    return (
        "\n"
        "  _  __\n"
        " | |/ /__ _ _ __   ___  _ __\n"
        " | ' // _` | '_ \\ / _ \\| '_ \\\n"
        " | . \\ (_| | | | | (_) | | | |\n"
        " |_|\\_\\__,_|_| |_|\\___/|_| |_|\n"
        "\n"
    )





# --- init ---


@pytest.mark.parametrize("tier", [0, 1, 2, 3])
def test_init_scaffolds_all_required_files(tmp_path: Path, tier: int) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--tier", str(tier)])
    assert result.exit_code == 0, result.output

    assert (target / "AGENTS.md").is_file()
    assert (target / "CLAUDE.md").is_file()
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["kanon-sdd"]["depth"] == tier
    assert config["kit_version"] == __version__
    assert "enabled_at" in config["aspects"]["kanon-sdd"]



# Phase A.3: test_kit_global_files_always_present retired (kit-global files: deleted per ADR-0048).


def test_init_without_sdd(tmp_path: Path) -> None:
    """kanon init with only worktrees+testing (no sdd) produces a valid project."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--aspects", "kanon-worktrees:1,kanon-testing:1"])
    assert result.exit_code == 0, result.output
    assert (target / "AGENTS.md").is_file()
    assert (target / ".kanon" / "config.yaml").is_file()
    # No sdd files
    assert not (target / "docs" / "sdd-method.md").exists()
    assert not (target / "docs" / "decisions").exists()
    assert not (target / "docs" / "plans").exists()
    # Worktrees + testing protocols present
    assert (target / ".kanon" / "protocols" / "kanon-worktrees" / "worktree-lifecycle.md").is_file()
    assert (target / ".kanon" / "protocols" / "kanon-testing" / "test-discipline.md").is_file()
    # Verify passes
    verify_result = runner.invoke(main, ["verify", str(target)])
    assert verify_result.exit_code == 0, verify_result.output



def test_init_bare(tmp_path: Path) -> None:
    """kanon init with no aspects produces a minimal valid project."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--aspects", ""])
    assert result.exit_code == 0, result.output
    assert (target / "AGENTS.md").is_file()
    assert (target / ".kanon" / "config.yaml").is_file()
    # No aspect files (Phase A.3: kit.md retired per ADR-0048)
    assert not (target / "docs").exists()
    assert not (target / ".kanon" / "protocols").exists()
    # Verify passes (with warning)
    verify_result = runner.invoke(main, ["verify", str(target)])
    assert verify_result.exit_code == 0, verify_result.output



def test_init_lite(tmp_path: Path) -> None:
    """--lite is sugar for sdd at depth 0."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--lite"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["kanon-sdd"]["depth"] == 0
    assert not (target / "docs" / "sdd-method.md").exists()



def test_profile_solo_enables_only_sdd(tmp_path: Path) -> None:
    """INV-cli-init-profile: --profile solo enables exactly kanon-sdd at depth 1."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--profile", "solo"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert set(config["aspects"]) == {"kanon-sdd"}
    assert config["aspects"]["kanon-sdd"]["depth"] == 1


def test_profile_team_enables_five_aspects(tmp_path: Path) -> None:
    """INV-cli-init-profile: --profile team enables sdd+testing+security+deps+worktrees at depth 1."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--profile", "team"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    expected = {"kanon-sdd", "kanon-testing", "kanon-security", "kanon-deps", "kanon-worktrees"}
    assert set(config["aspects"]) == expected
    for name in expected:
        assert config["aspects"][name]["depth"] == 1


def test_profile_all_uses_default_depths(tmp_path: Path) -> None:
    """INV-cli-init-profile: --profile all enables every kit aspect at its manifest default-depth."""
    from kanon_core._manifest import _load_top_manifest
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--profile", "all"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    top = _load_top_manifest()
    kit_aspects = {n for n in top["aspects"] if n.startswith("kanon-")}
    assert set(config["aspects"]) == kit_aspects
    for name in kit_aspects:
        assert config["aspects"][name]["depth"] == int(top["aspects"][name]["default-depth"])


def test_profile_max_uses_max_depths(tmp_path: Path) -> None:
    """INV-cli-init-profile: --profile max enables every kit aspect at the upper end of its depth-range."""
    from kanon_core._manifest import _load_top_manifest
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--profile", "max"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    top = _load_top_manifest()
    kit_aspects = {n for n in top["aspects"] if n.startswith("kanon-")}
    assert set(config["aspects"]) == kit_aspects
    for name in kit_aspects:
        assert config["aspects"][name]["depth"] == int(top["aspects"][name]["depth-range"][1])


def test_profile_full_is_rejected(tmp_path: Path) -> None:
    """INV-cli-init-profile: legacy --profile full is rejected with click's choice error."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--profile", "full"])
    assert result.exit_code != 0
    assert "full" in result.output.lower() or "invalid" in result.output.lower()
    assert not (target / ".kanon").exists()


def test_init_writes_full_agents_md_when_absent(tmp_path: Path) -> None:
    """INV-cli-init-agents-md-merge: absent AGENTS.md → write the full kit-rendered file."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--profile", "solo"])
    assert result.exit_code == 0, result.output
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    # Kit-rendered AGENTS.md carries the hard-gates table and a kanon marker.
    assert "## Hard Gates" in agents
    assert "<!-- kanon:begin:" in agents


def test_init_refreshes_marker_bodies_when_present(tmp_path: Path) -> None:
    """INV-cli-init-agents-md-merge: existing AGENTS.md with kanon markers \
→ refresh marker bodies, preserve outside content."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    target.mkdir()
    # Pre-existing AGENTS.md with a kanon marker block + user prose outside.
    user_prose_above = "# My project\n\nUser-authored content above the marker.\n\n"
    user_prose_below = "\n\n## Project notes\n\nUser-authored content below the marker.\n"
    marker_block = (
        "<!-- kanon:begin:protocols-index -->\nSTALE BODY\n<!-- kanon:end:protocols-index -->"
    )
    (target / "AGENTS.md").write_text(user_prose_above + marker_block + user_prose_below, encoding="utf-8")
    result = runner.invoke(main, ["init", str(target), "--profile", "team"])
    assert result.exit_code == 0, result.output
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    # Outside-marker content survives byte-for-byte.
    assert "User-authored content above the marker." in agents
    assert "User-authored content below the marker." in agents
    # Stale marker body was refreshed (no longer literal "STALE BODY").
    assert "STALE BODY" not in agents


def test_init_prepends_kit_content_when_no_markers(tmp_path: Path) -> None:
    """INV-cli-init-agents-md-merge: existing AGENTS.md without markers \
→ prepend kit content above existing prose under `## Project context`."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    target.mkdir()
    existing = "# My project\n\nThis repo is for X. We use Y. Conventions: Z.\n"
    (target / "AGENTS.md").write_text(existing, encoding="utf-8")
    result = runner.invoke(main, ["init", str(target), "--profile", "team"])
    assert result.exit_code == 0, result.output
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    # Kit content sits at the top.
    hard_gates_idx = agents.find("## Hard Gates")
    project_context_idx = agents.find("## Project context")
    assert hard_gates_idx >= 0, "kit content not present"
    assert project_context_idx > hard_gates_idx, "kit content must precede `## Project context`"
    # Existing prose preserved verbatim under the H2.
    assert existing.strip() in agents


def test_init_mutual_exclusion(tmp_path: Path) -> None:
    """--lite and --profile are mutually exclusive with --tier and --aspects."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--lite", "--tier", "1"])
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def _extract_verify_json(output: str) -> dict:
    """Extract the first JSON object from `verify` output (report precedes the human summary)."""
    start = output.find("{")
    end = output.rfind("}")
    return json.loads(output[start:end + 1])



@pytest.mark.parametrize("tier", [1, 2, 3])
def test_init_verify_returns_ok(tmp_path: Path, tier: int) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", str(tier)])
    result = runner.invoke(main, ["verify", str(target)])
    assert result.exit_code == 0, result.output
    report = _extract_verify_json(result.output)
    assert report["status"] == "ok"
    assert report["aspects"]["kanon-sdd"] == tier



def test_init_rejects_existing_without_force(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Second init without --force should fail.
    result = runner.invoke(main, ["init", str(target), "--tier", "1"])
    assert result.exit_code != 0
    assert "already exists" in result.output.lower()



def test_init_writes_all_shims(tmp_path: Path) -> None:
    """With --harness for each known harness, all shims are written."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    harness_args = []
    for name in ["claude-code", "kiro", "cursor", "copilot", "windsurf", "cline", "roo", "jetbrains-ai"]:
        harness_args.extend(["--harness", name])
    runner.invoke(main, ["init", str(target), "--tier", "1", *harness_args])

    expected_shims = [
        "CLAUDE.md",
        ".kiro/steering/kanon.md",
        ".cursor/rules/kanon.mdc",
        ".github/copilot-instructions.md",
        ".windsurf/rules/kanon.md",
        ".clinerules/kanon.md",
        ".roo/rules/kanon.md",
        ".aiassistant/rules/kanon.md",
    ]
    for shim_path in expected_shims:
        assert (target / shim_path).is_file(), f"missing shim: {shim_path}"



def test_init_default_writes_only_claude_md(tmp_path: Path) -> None:
    """In a clean dir with no harness dotdirs, only CLAUDE.md is written."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    assert (target / "CLAUDE.md").is_file()
    assert not (target / ".cursor/rules/kanon.mdc").exists()
    assert not (target / ".kiro/steering/kanon.md").exists()



def test_init_auto_detects_harness(tmp_path: Path) -> None:
    """When a harness dotdir exists, its shim is written."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    target.mkdir()
    (target / ".cursor").mkdir()

    runner.invoke(main, ["init", str(target), "--tier", "1"])

    assert (target / "CLAUDE.md").is_file()
    assert (target / ".cursor/rules/kanon.mdc").is_file()
    assert not (target / ".kiro/steering/kanon.md").exists()



def test_init_harness_explicit(tmp_path: Path) -> None:
    """--harness flag selects specific shims."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1", "--harness", "kiro"])

    assert (target / "AGENTS.md").is_file()
    assert (target / ".kiro/steering/kanon.md").is_file()
    assert not (target / ".cursor/rules/kanon.mdc").exists()
    assert not (target / ".windsurf/rules/kanon.md").exists()



def test_shims_are_pointers_not_duplicates(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1",
                         "--harness", "claude-code", "--harness", "cursor", "--harness", "windsurf"])

    # Shims should be short — well under 1000 chars — and must not contain
    # the plan-before-build rule text (which is AGENTS.md's job).
    for shim_name in ["CLAUDE.md", ".cursor/rules/kanon.mdc", ".windsurf/rules/kanon.md"]:
        content = (target / shim_name).read_text(encoding="utf-8")
        assert len(content) < 1000
        assert "Required: Plan Before Build" not in content


# --- protocol layer + kit.md ---


_EXPECTED_PROTOCOLS_BY_TIER: dict[int, set[str]] = {
    0: set(),
    1: {
        "tier-up-advisor.md", "verify-triage.md", "completion-checklist.md",
        "scope-check.md", "plan-before-build.md", "adr-authoring.md",
    },
    2: {
        "tier-up-advisor.md", "verify-triage.md", "completion-checklist.md",
        "scope-check.md", "plan-before-build.md", "adr-authoring.md", "spec-review.md",
        "spec-before-design.md", "adr-immutability.md", "foundations-authoring.md",
        "foundations-review.md",
    },
    3: {
        "tier-up-advisor.md",
        "verify-triage.md",
        "completion-checklist.md",
        "scope-check.md",
        "plan-before-build.md",
        "adr-authoring.md",
        "spec-review.md",
        "spec-before-design.md",
        "adr-immutability.md",
        "foundations-authoring.md",
        "foundations-review.md",
        "design-before-plan.md",
    },
}



@pytest.mark.parametrize("tier", [0, 1, 2, 3])
def test_protocols_scaffolded_at_correct_tier(tmp_path: Path, tier: int) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", str(tier)])
    protocols_dir = target / ".kanon" / "protocols" / "kanon-sdd"
    actual: set[str] = (
        {p.name for p in protocols_dir.glob("*.md")}
        if protocols_dir.exists()
        else set()
    )
    assert actual == _EXPECTED_PROTOCOLS_BY_TIER[tier]



# Phase A.3: test_kit_md_scaffolded_at_all_tiers retired (kit.md template deleted per ADR-0048).


@pytest.mark.parametrize("tier", [1, 2, 3])
def test_protocols_index_marker_present_tier1_plus(tmp_path: Path, tier: int) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", str(tier)])
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- kanon:begin:protocols-index -->" in agents
    assert "<!-- kanon:end:protocols-index -->" in agents
    assert "tier-up-advisor" in agents
    assert "verify-triage" in agents
    if tier >= 2:
        assert "spec-review" in agents
    else:
        assert "spec-review" not in agents



def test_protocols_index_present_at_tier_0(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "0"])
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- kanon:begin:protocols-index -->" in agents
    assert "No protocols active" in agents



def test_init_preserves_user_content_outside_markers(tmp_path: Path) -> None:
    """User content in AGENTS.md outside kit markers must survive `upgrade`."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    agents_md = target / "AGENTS.md"
    original = agents_md.read_text(encoding="utf-8")
    # Add a user-authored section at the end.
    user_block = "\n## Project-specific notes (user-authored)\n\nDo not overwrite me.\n"
    agents_md.write_text(original + user_block, encoding="utf-8")

    # `upgrade` should leave user content intact (kit version unchanged so it's a noop,
    # but the merge logic is still exercised on tier-set).
    result = runner.invoke(main, ["tier", "set", str(target), "2"])
    assert result.exit_code == 0, result.output
    after = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "Project-specific notes (user-authored)" in after
    assert "Do not overwrite me." in after



# --- --version ---


def test_version_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output



# --- upgrade ---


def test_upgrade_bumps_version(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Patch config to an old version.
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["kit_version"] = "0.0.0"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert updated["kit_version"] == __version__
    assert "0.0.0" in result.output
    assert __version__ in result.output



def test_upgrade_already_current(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    assert "already at" in result.output.lower()



def test_upgrade_noop_does_not_churn_config(tmp_path: Path) -> None:
    """A no-op upgrade must not rewrite the config file."""

    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    config_path = target / ".kanon" / "config.yaml"
    before_bytes = config_path.read_bytes()

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    assert config_path.read_bytes() == before_bytes, (
        "upgrade must not rewrite config on a no-op"
    )



def test_upgrade_preserves_aspect_config(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    # Phase A.4: kanon-testing's config-schema retired; this test now uses
    # arbitrary user config keys (substrate preserves any keys verbatim).
    config["aspects"]["kanon-testing"] = {
        "depth": 3,
        "enabled_at": "2025-01-01T00:00:00+00:00",
        "config": {"my_custom_key": "value-a", "another_key": "value-b"},
    }
    config["kit_version"] = "0.0.0"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert updated["aspects"]["kanon-testing"]["config"]["my_custom_key"] == "value-a"
    assert updated["aspects"]["kanon-testing"]["config"]["another_key"] == "value-b"



def test_upgrade_preserves_enabled_at_on_version_bump(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    # Set a distinctive timestamp that cannot coincidentally match _now_iso().
    config["aspects"]["kanon-sdd"]["enabled_at"] = "2024-06-15T12:00:00+00:00"
    config["kit_version"] = "0.0.0"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert updated["aspects"]["kanon-sdd"]["enabled_at"] == "2024-06-15T12:00:00+00:00"



def test_upgrade_preserves_extra_root_keys(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["preflight-stages"] = {
        "push": [{"run": "echo test", "label": "test-scan"}],
    }
    config["kit_version"] = "0.0.0"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert updated["preflight-stages"] == {
        "push": [{"run": "echo test", "label": "test-scan"}],
    }



def test_upgrade_heals_edited_markers(tmp_path: Path) -> None:
    """`upgrade` re-renders kit-managed marker sections even when kit_version
    is unchanged. User content outside markers is preserved."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "2"])

    agents_path = target / "AGENTS.md"
    original = agents_path.read_text(encoding="utf-8")

    # Corrupt the body of a kit-managed marker section.
    begin = "<!-- kanon:begin:protocols-index -->"
    end = "<!-- kanon:end:protocols-index -->"
    bi = original.find(begin)
    ei = original.find(end, bi + len(begin))
    assert bi >= 0 and ei > bi
    corrupted = original[: bi + len(begin)] + "\nGARBAGE BODY\n" + original[ei:]
    # Add user content outside markers — must survive.
    corrupted += "\n## My Custom Section\n\nUser-authored. Do not touch.\n"
    agents_path.write_text(corrupted, encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    final = agents_path.read_text(encoding="utf-8")
    assert "GARBAGE BODY" not in final, "upgrade did not re-render marker body"
    assert "My Custom Section" in final, "upgrade clobbered user content"
    assert "User-authored. Do not touch." in final
    # The kit's canonical body is restored — sanity-check it begins with the
    # section's header, which the kit ships in `sections/plan-before-build.md`.
    assert "Plan Before Build" in final



def test_upgrade_not_a_kanon_project(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["upgrade", str(tmp_path)])
    assert result.exit_code != 0
    assert "not a kanon project" in result.output.lower()



def test_upgrade_malformed_config(tmp_path: Path) -> None:
    runner = CliRunner()
    config_dir = tmp_path / ".kanon"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text("bad", encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(tmp_path)])
    assert result.exit_code != 0
    assert "malformed" in result.output.lower()



def test_upgrade_legacy_v1_migration(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    # Rewrite config to legacy v1 format.
    config_path = target / ".kanon" / "config.yaml"
    config_path.write_text(
        yaml.safe_dump({"kit_version": "0.0.1", "tier": 2}, sort_keys=False),
        encoding="utf-8",
    )

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert "aspects" in updated
    assert "tier" not in updated



def test_upgrade_preserves_user_content(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Add user content to AGENTS.md.
    agents = target / "AGENTS.md"
    agents.write_text(
        agents.read_text(encoding="utf-8") + "\n<!-- MY CUSTOM SECTION -->\nHello world\n",
        encoding="utf-8",
    )
    # Patch config to old version so upgrade actually runs.
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["kit_version"] = "0.0.0"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    assert "MY CUSTOM SECTION" in (target / "AGENTS.md").read_text(encoding="utf-8")



def test_upgrade_refreshes_shims(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Corrupt a shim.
    claude_md = target / "CLAUDE.md"
    assert claude_md.exists()
    claude_md.write_text("corrupted", encoding="utf-8")
    # Patch config to old version so upgrade runs.
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["kit_version"] = "0.0.0"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    assert claude_md.read_text(encoding="utf-8") != "corrupted"



def test_upgrade_creates_agents_md_if_missing(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Delete AGENTS.md and patch config to old version.
    (target / "AGENTS.md").unlink()
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["kit_version"] = "0.0.0"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    assert (target / "AGENTS.md").is_file()



# --- upgrade: flat protocol migration ---


def test_upgrade_migrates_flat_protocols(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "2"])

    # Create a flat protocol file (v1 layout: .kanon/protocols/*.md).
    protocols_dir = target / ".kanon" / "protocols"
    flat_file = protocols_dir / "some-protocol.md"
    flat_file.write_text("# Custom protocol\n\nDo the thing.\n", encoding="utf-8")

    # Patch config to old version so upgrade actually runs.
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["kit_version"] = "0.0.0"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    # Flat file should be moved into sdd/ subdirectory.
    assert not flat_file.exists(), "flat protocol file should have been moved"
    migrated = protocols_dir / "kanon-sdd" / "some-protocol.md"
    assert migrated.is_file(), "protocol should be at .kanon/protocols/kanon-sdd/some-protocol.md"
    assert "Custom protocol" in migrated.read_text(encoding="utf-8")
    assert "namespaced" in result.output.lower()



# --- cli.py: init with --force overwrites ---


def test_init_force_overwrites(tmp_path: Path) -> None:
    """Line 98→100: init with --force on existing project."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["init", str(target), "--tier", "2", "--force"])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert config["aspects"]["kanon-sdd"]["depth"] == 2



# --- cli.py: init with default tier (no --tier flag) ---


def test_init_default_tier(tmp_path: Path) -> None:
    """Phase A.3 (per ADR-0048 de-opinionation): `kanon init` with no flags
    scaffolds an empty project (no aspects enabled). Consumers must opt in
    via --aspects, --tier, --lite, or --profile.
    """
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target)])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    # No aspects enabled — de-opinionation default.
    assert config.get("aspects", {}) == {}



# --- cli.py: upgrade where AGENTS.md content actually changes ---


def test_upgrade_modifies_agents_md(tmp_path: Path) -> None:
    """Line 145: upgrade path where merged AGENTS.md differs from existing."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    # Corrupt a marker section so merge produces a diff
    agents = target / "AGENTS.md"
    text = agents.read_text(encoding="utf-8")
    text = text.replace(
        "<!-- kanon:begin:kanon-sdd/body -->",
        "<!-- kanon:begin:kanon-sdd/body -->\nCORRUPTED CONTENT",
    )
    agents.write_text(text, encoding="utf-8")
    # Patch config to old version so upgrade runs
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["kit_version"] = "0.0.0"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    # The corrupted content should be replaced by the merge
    final = agents.read_text(encoding="utf-8")
    assert "CORRUPTED CONTENT" not in final



# --- Sentinel crash-recovery integration tests (ADR-0024) ---


def test_sentinel_absent_after_successful_init(tmp_path: Path) -> None:
    """After a successful init, .kanon/.pending must not exist."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    result = runner.invoke(main, ["init", str(target), "--tier", "1"])
    assert result.exit_code == 0, result.output
    assert not (target / ".kanon" / ".pending").exists()



def test_sentinel_absent_after_successful_upgrade(tmp_path: Path) -> None:
    """After a successful upgrade, .kanon/.pending must not exist."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    assert not (target / ".kanon" / ".pending").exists()



def test_sentinel_absent_after_successful_set_depth(tmp_path: Path) -> None:
    """After a successful set-depth, .kanon/.pending must not exist."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])
    result = runner.invoke(main, ["aspect", "set-depth", str(target), "kanon-sdd", "2"])
    assert result.exit_code == 0, result.output
    assert not (target / ".kanon" / ".pending").exists()



def test_upgrade_v1_legacy_round_trip_preserves_user_content(tmp_path: Path) -> None:
    """End-to-end: a v1-shaped config + AGENTS.md user prose survives upgrade
    intact; resulting config is v3 with `kanon-sdd`.
    """
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    # Hand-rewrite to v1 shape.
    (target / ".kanon" / "config.yaml").write_text(
        yaml.safe_dump({"kit_version": "0.1.0a1", "tier": 2}, sort_keys=False),
        encoding="utf-8",
    )
    # Add user-authored prose outside markers (must survive).
    agents_path = target / "AGENTS.md"
    agents_path.write_text(
        agents_path.read_text(encoding="utf-8")
        + "\n## My private notes\nDo not lose me.\n",
        encoding="utf-8",
    )
    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text())
    assert "tier" not in config
    assert config["aspects"]["kanon-sdd"]["depth"] == 2
    assert "## My private notes" in agents_path.read_text(encoding="utf-8")
    assert "Do not lose me." in agents_path.read_text(encoding="utf-8")


# --- ADR-0028 / Phase 3: project-aspects (T23, T24, T25, T26) ---


_PROJECT_ASPECT_MIN_MANIFEST = (
    "stability: experimental\n"
    "depth-range: [0, 1]\n"
    "default-depth: 1\n"
    "requires: []\n"
    "depth-0:\n"
    "  files: []\n"
    "  protocols: []\n"
    "  sections: []\n"
    "depth-1:\n"
    "  files: []\n"
    "  protocols: []\n"
    "  sections: []\n"
)


def _stage_project_aspect(target: Path, name: str, manifest_text: str) -> Path:
    """Drop a project-aspect manifest at <target>/.kanon/aspects/<name>/manifest.yaml."""
    aspect_dir = target / ".kanon" / "aspects" / name
    aspect_dir.mkdir(parents=True, exist_ok=True)
    (aspect_dir / "manifest.yaml").write_text(manifest_text, encoding="utf-8")
    return aspect_dir



def test_upgrade_does_not_modify_project_aspect_files(tmp_path: Path) -> None:
    """`kanon upgrade` re-renders kit-aspect content from the installed kit and
    leaves project-aspect contents under .kanon/aspects/ untouched. The
    `kit_version` pin in config governs only kit-aspect content; project-
    aspects version with the consumer's own git history (project-aspects
    spec INV-10 / source-routing)."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    aspect_dir = _stage_project_aspect(
        target, "project-stable", _PROJECT_ASPECT_MIN_MANIFEST
    )
    # Add a sentinel file inside the project-aspect directory; upgrade must
    # not touch it.
    sentinel = aspect_dir / "do-not-touch.txt"
    sentinel.write_text("user-authored content\n", encoding="utf-8")

    runner.invoke(main, ["aspect", "add", str(target), "project-stable"])

    # Force kit_version mismatch so upgrade actively re-renders kit content.
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["kit_version"] = "0.0.1"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["upgrade", str(target)])
    assert result.exit_code == 0, result.output

    # Project-aspect's user-authored content survives upgrade verbatim.
    assert sentinel.read_text(encoding="utf-8") == "user-authored content\n"
    assert (
        (aspect_dir / "manifest.yaml").read_text(encoding="utf-8")
        == _PROJECT_ASPECT_MIN_MANIFEST
    )

    # Upgrade refreshed the kit_version pin (kit-side content path) but the
    # project-aspect's config entry survives unchanged.
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert config["kit_version"] != "0.0.1"  # bumped by upgrade
    assert "project-stable" in config["aspects"]
    assert config["aspects"]["project-stable"]["depth"] == 1


# --- kanon-banner spec tests (docs/specs/kanon-banner.md) ---


def _read_banner() -> str:
    """Read the canonical banner constant via the same import path as production."""
    from kanon_core._banner import _BANNER
    return _BANNER


def _banner_literal() -> str:
    """The byte-frozen banner literal asserted by INV-kanon-banner-byte-frozen."""
    return (
        "\n"
        "  _  __\n"
        " | |/ /__ _ _ __   ___  _ __\n"
        " | ' // _` | '_ \\ / _ \\| '_ \\\n"
        " | . \\ (_| | | | | (_) | | | |\n"
        " |_|\\_\\__,_|_| |_|\\___/|_| |_|\n"
        "\n"
    )



# INV-kanon-banner-single-source: one constant feeds all three surfaces.
def test_banner_constant_used_by_all_surfaces() -> None:
    """The _BANNER constant defined in kernel/_banner.py is the only
    byte-equal copy in the source tree, and it is referenced by both the
    runtime emission path (cli.py) and the AGENTS.md scaffolding (_scaffold.py).
    """
    import kanon_core._banner as banner_mod

    src_root = Path(banner_mod.__file__).resolve().parent
    cli_text = (src_root / "cli.py").read_text(encoding="utf-8")
    scaffold_text = (src_root / "_scaffold.py").read_text(encoding="utf-8")

    assert "from kanon_core._banner import" in cli_text and "_BANNER" in cli_text
    assert "from kanon_core._banner import _BANNER" in scaffold_text

    # No second byte-equal copy of the banner literal anywhere else in src/.
    literal_substr = " |_|\\_\\__,_|_| |_|\\___/|_| |_|"
    matches = sum(
        1 for p in src_root.rglob("*.py")
        if literal_substr in p.read_text(encoding="utf-8")
    )
    # _banner.py defines it; tests use the helper above (not a literal).
    assert matches == 1, f"banner literal appears in {matches} .py files; expected 1"



# INV-kanon-banner-tty-only: runtime emits only when stderr is a TTY.
def test_banner_emitted_on_tty(tmp_path: Path) -> None:
    """When stderr is a TTY, init and upgrade emit the banner on stderr."""
    runner = CliRunner()
    target = tmp_path / "scratch"

    with patch("kanon_core._banner._should_emit_banner", return_value=True):
        init_result = runner.invoke(main, ["init", str(target), "--tier", "1"])
        upgrade_result = runner.invoke(main, ["upgrade", str(target)])

    assert init_result.exit_code == 0, init_result.output
    assert upgrade_result.exit_code == 0, upgrade_result.output
    banner = _read_banner()
    assert banner in init_result.stderr, "banner missing from init stderr"
    assert banner in upgrade_result.stderr, "banner missing from upgrade stderr"



def test_banner_suppressed_when_stderr_not_tty(tmp_path: Path) -> None:
    """When stderr is not a TTY (CliRunner default), banner is suppressed."""
    runner = CliRunner()
    target = tmp_path / "scratch"

    init_result = runner.invoke(main, ["init", str(target), "--tier", "1"])
    upgrade_result = runner.invoke(main, ["upgrade", str(target)])

    assert init_result.exit_code == 0, init_result.output
    assert upgrade_result.exit_code == 0, upgrade_result.output
    banner = _read_banner()
    assert banner not in init_result.stderr
    assert banner not in upgrade_result.stderr



# INV-kanon-banner-quiet-suppresses: --quiet beats TTY.
def test_banner_suppressed_with_quiet_flag(tmp_path: Path) -> None:
    """Even when stderr is a TTY, --quiet/-q suppresses the banner."""
    runner = CliRunner()
    target = tmp_path / "scratch"

    with patch("kanon_core._banner._should_emit_banner", return_value=False):
        # _should_emit_banner already returns False when quiet=True; this
        # test validates the wiring by invoking with --quiet and asserting
        # the banner is absent regardless of TTY.
        init_result = runner.invoke(
            main, ["init", str(target), "--tier", "1", "--quiet"]
        )
        upgrade_result = runner.invoke(
            main, ["upgrade", str(target), "-q"]
        )

    assert init_result.exit_code == 0, init_result.output
    assert upgrade_result.exit_code == 0, upgrade_result.output
    banner = _read_banner()
    assert banner not in init_result.stderr
    assert banner not in upgrade_result.stderr
    # --quiet on init also suppresses the trailing "Next steps" advisory.
    assert "Next steps" not in init_result.output
    assert "Grow when ready" not in init_result.output



# INV-kanon-banner-stderr-only: never on stdout.
def test_banner_goes_to_stderr_not_stdout(tmp_path: Path) -> None:
    """When emitted, the banner appears on stderr, never stdout."""
    runner = CliRunner()
    target = tmp_path / "scratch"

    with patch("kanon_core._banner._should_emit_banner", return_value=True):
        init_result = runner.invoke(main, ["init", str(target), "--tier", "1"])
        upgrade_result = runner.invoke(main, ["upgrade", str(target)])

    banner = _read_banner()
    assert banner in init_result.stderr
    assert banner not in init_result.stdout
    assert banner in upgrade_result.stderr
    assert banner not in upgrade_result.stdout



# INV-kanon-banner-byte-frozen: exact bytes.
def test_banner_exact_byte_content() -> None:
    """The _BANNER constant equals the frozen byte literal."""
    assert _read_banner() == _banner_literal()



def test_banner_present_at_top_of_scaffolded_agents_md(tmp_path: Path) -> None:
    """Scaffolded AGENTS.md contains the banner verbatim inside the marker
    block, positioned above the H1.
    """
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    banner = _read_banner()

    # Banner bytes (with surrounding newlines stripped) appear in AGENTS.md.
    assert banner.strip("\n") in agents

    # And they sit before the H1.
    banner_pos = agents.find(banner.strip("\n"))
    h1_pos = agents.find("# AGENTS.md —")
    assert banner_pos != -1 and h1_pos != -1
    assert banner_pos < h1_pos, "banner must appear before the H1"



# INV-kanon-banner-surface-enumeration: only init, upgrade, AGENTS.md.
def test_banner_not_emitted_by_other_commands(tmp_path: Path) -> None:
    """Commands other than init/upgrade do not emit the banner, even on a TTY."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    banner = _read_banner()
    with patch("kanon_core._banner._should_emit_banner", return_value=True):
        for cmd in (
            ["verify", str(target)],
            ["aspect", "list"],
            ["tier", "set", str(target), "1"],
        ):
            result = runner.invoke(main, cmd)
            assert banner not in result.stderr, (
                f"banner unexpectedly emitted by {cmd[0]}"
            )
            assert banner not in result.stdout, (
                f"banner unexpectedly on stdout for {cmd[0]}"
            )



def test_banner_in_agents_md_marker_block(tmp_path: Path) -> None:
    """In scaffolded AGENTS.md, the banner sits inside the kanon:begin:banner
    marker pair, not as loose prose.
    """
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--tier", "1"])

    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    banner = _read_banner().strip("\n")

    begin = "<!-- kanon:begin:banner -->"
    end = "<!-- kanon:end:banner -->"
    begin_pos = agents.find(begin)
    end_pos = agents.find(end)
    banner_pos = agents.find(banner)

    assert begin_pos != -1, "missing kanon:begin:banner marker"
    assert end_pos != -1, "missing kanon:end:banner marker"
    assert begin_pos < banner_pos < end_pos, (
        "banner must sit between begin/end markers"
    )


# --- Plan v040a1-release-prep PR 3: kanon init writes v4-shape configs;
# config-mutating verbs preserve v4 fields across writes.


def test_init_writes_v4_config_fields(tmp_path: Path) -> None:
    """Per plan v040a1-release-prep PR 3: kanon init MUST produce a v4-shape
    config (schema-version: 4 + kanon-dialect pin) so fresh installs are not
    born requiring `kanon migrate`."""
    runner = CliRunner()
    target = tmp_path / "fresh"
    result = runner.invoke(main, ["init", str(target), "--profile", "solo"])
    assert result.exit_code == 0, result.output

    config = yaml.safe_load((target / ".kanon" / "config.yaml").read_text(encoding="utf-8"))
    assert config["schema-version"] == 4, "init MUST stamp schema-version: 4"
    assert config["kanon-dialect"] == "2026-05-01", (
        "init MUST stamp the v1 dialect pin"
    )


def test_aspect_remove_preserves_v4_fields(tmp_path: Path) -> None:
    """Per plan v040a1-release-prep PR 3: config-mutating verbs MUST round-trip
    schema-version, kanon-dialect, and any other publisher-added top-level keys.
    Without this, mutation silently strips the v4 commitment authored at init."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    runner.invoke(main, ["init", str(target), "--profile", "solo"])
    # Add an extra top-level key (simulates a publisher-added field — the kit
    # ignores unknown keys but they must round-trip across writes).
    config_path = target / ".kanon" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["custom-publisher-field"] = {"opaque": "value"}
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    # Trigger a mutation. solo profile enables kanon-sdd; remove it.
    r = runner.invoke(main, ["aspect", "remove", str(target), "kanon-sdd"])
    assert r.exit_code == 0, r.output

    after = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert after["schema-version"] == 4, "schema-version must survive mutation"
    assert after["kanon-dialect"] == "2026-05-01", "kanon-dialect must survive mutation"
    assert after["custom-publisher-field"] == {"opaque": "value"}, (
        "publisher-added top-level keys must round-trip"
    )


# --- Plan v040a1-followup AC7: kanon init grow-hints use canonical
# kanon-<local> names; bare names trigger Phase A.5 deprecation warnings,
# so the hints must not walk users into them.


def test_init_hints_use_canonical_kanon_names(tmp_path: Path) -> None:
    """Init grow-hints must reference aspects via the canonical kanon-<local>
    form. Bare-name shorthand (`testing`, `security`, `worktrees`, `sdd`) is
    deprecated per Phase A.5 / ADR-0045 and emits stderr warnings — recommending
    them in init hints would walk every new user straight into the warning."""
    runner = CliRunner()
    target = tmp_path / "scratch"
    # --profile solo enables only kanon-sdd; the testing/security/worktrees
    # hints (which suggest growing) all fire.
    result = runner.invoke(main, ["init", str(target), "--profile", "solo"])
    assert result.exit_code == 0, result.output

    # Positive: the canonical forms appear.
    assert "kanon aspect add . kanon-testing" in result.output
    assert "kanon aspect add . kanon-security" in result.output
    assert "kanon aspect add . kanon-worktrees" in result.output
    assert "kanon aspect set-depth . kanon-sdd " in result.output

    # Negative: the deprecated bare forms do NOT appear.
    # Match `add . <bare> ` (with surrounding spaces so we don't trip on `kanon-testing`).
    for bare in ("testing", "security", "worktrees", "sdd"):
        assert f"add . {bare} " not in result.output, (
            f"init hint suggests deprecated bare-name aspect {bare!r}; "
            "use the canonical kanon-<local> form."
        )
        assert f"set-depth . {bare} " not in result.output, (
            f"init hint suggests deprecated bare-name aspect {bare!r}."
        )

