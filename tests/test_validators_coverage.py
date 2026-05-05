"""Tests for plan_completion and foundations_coherence validators."""
from __future__ import annotations

import time
from pathlib import Path


# --- plan_completion ---


class TestPlanCompletion:
    def test_no_plans_dir_no_error(self, tmp_path: Path) -> None:
        from kanon_core._validators.plan_completion import check

        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert errors == []

    def test_done_plan_with_unchecked_tasks_errors(self, tmp_path: Path) -> None:
        from kanon_core._validators.plan_completion import check

        plans = tmp_path / "docs" / "plans"
        plans.mkdir(parents=True)
        (plans / "my-plan.md").write_text(
            "---\nstatus: done\n---\n# Plan\n\n- [x] Task 1\n- [ ] Task 2\n",
            encoding="utf-8",
        )
        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert len(errors) == 1
        assert "unchecked" in errors[0]

    def test_done_plan_all_checked_no_error(self, tmp_path: Path) -> None:
        from kanon_core._validators.plan_completion import check

        plans = tmp_path / "docs" / "plans"
        plans.mkdir(parents=True)
        (plans / "my-plan.md").write_text(
            "---\nstatus: done\n---\n# Plan\n\n- [x] Task 1\n- [x] Task 2\n",
            encoding="utf-8",
        )
        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert errors == []

    def test_non_done_plan_with_unchecked_no_error(self, tmp_path: Path) -> None:
        from kanon_core._validators.plan_completion import check

        plans = tmp_path / "docs" / "plans"
        plans.mkdir(parents=True)
        (plans / "my-plan.md").write_text(
            "---\nstatus: approved\n---\n# Plan\n\n- [ ] Task 1\n",
            encoding="utf-8",
        )
        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert errors == []

    def test_skips_readme_and_roadmap(self, tmp_path: Path) -> None:
        from kanon_core._validators.plan_completion import check

        plans = tmp_path / "docs" / "plans"
        plans.mkdir(parents=True)
        (plans / "README.md").write_text(
            "---\nstatus: done\n---\n- [ ] Unchecked\n", encoding="utf-8"
        )
        (plans / "roadmap.md").write_text(
            "---\nstatus: done\n---\n- [ ] Unchecked\n", encoding="utf-8"
        )
        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert errors == []


# --- foundations_coherence ---


class TestFoundationsCoherence:
    def test_no_vision_file_no_warning(self, tmp_path: Path) -> None:
        from kanon_core._validators.foundations_coherence import check

        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert warnings == []

    def test_vision_without_principles_no_warning(self, tmp_path: Path) -> None:
        from kanon_core._validators.foundations_coherence import check

        foundations = tmp_path / "docs" / "foundations"
        foundations.mkdir(parents=True)
        (foundations / "vision.md").write_text("# Vision\n", encoding="utf-8")
        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert warnings == []

    def test_first_run_stores_hash_no_warning(self, tmp_path: Path) -> None:
        from kanon_core._validators.foundations_coherence import check

        foundations = tmp_path / "docs" / "foundations"
        principles = foundations / "principles"
        foundations.mkdir(parents=True)
        principles.mkdir()
        (foundations / "vision.md").write_text("# Vision\n", encoding="utf-8")
        (principles / "P-one.md").write_text("# P\n", encoding="utf-8")
        (tmp_path / ".kanon").mkdir()

        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert warnings == []
        assert (tmp_path / ".kanon" / "foundations-vision.sha").is_file()

    def test_vision_changed_without_downstream_update_warns(self, tmp_path: Path) -> None:
        from kanon_core._validators.foundations_coherence import check

        foundations = tmp_path / "docs" / "foundations"
        principles = foundations / "principles"
        foundations.mkdir(parents=True)
        principles.mkdir()
        (foundations / "vision.md").write_text("# Vision v1\n", encoding="utf-8")
        (principles / "P-one.md").write_text("# P\n", encoding="utf-8")

        kanon_dir = tmp_path / ".kanon"
        kanon_dir.mkdir()
        # Store old hash
        (kanon_dir / "foundations-vision.sha").write_text("oldhash", encoding="utf-8")

        # Make principle older than vision
        old_time = time.time() - 1000
        import os
        os.utime(principles / "P-one.md", (old_time, old_time))

        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert any("foundations-coherence" in w for w in warnings)

    def test_vision_changed_with_downstream_update_clears(self, tmp_path: Path) -> None:
        from kanon_core._validators.foundations_coherence import check

        foundations = tmp_path / "docs" / "foundations"
        principles = foundations / "principles"
        foundations.mkdir(parents=True)
        principles.mkdir()

        # Write vision first (older)
        (foundations / "vision.md").write_text("# Vision v2\n", encoding="utf-8")
        import os
        old_time = time.time() - 1000
        os.utime(foundations / "vision.md", (old_time, old_time))

        # Write principle after (newer)
        (principles / "P-one.md").write_text("# Updated P\n", encoding="utf-8")

        kanon_dir = tmp_path / ".kanon"
        kanon_dir.mkdir()
        (kanon_dir / "foundations-vision.sha").write_text("oldhash", encoding="utf-8")

        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert warnings == []
