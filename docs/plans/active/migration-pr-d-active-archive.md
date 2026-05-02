---
status: approved
slug: migration-pr-d-active-archive
date: 2026-05-02
---

# Plan: Migration PR D — `docs/plans/active/` + `archive/` (per ADR-0049 §Implementation Roadmap step D)

## Goal

Partition `docs/plans/` into `active/` (status:draft / status:approved) and `archive/` (status:done). Per ADR-0049 §1(4); panel data showed 100+ plan files growing 112%/100 commits, making flat listing operationally unusable.

## Scope

In scope:
- For each `.md` in `docs/plans/`, read frontmatter `status:`. Move to `docs/plans/archive/` if status:done; else `docs/plans/active/`. README.md + roadmap.md (no status frontmatter) stay at `docs/plans/`.
- Update `scripts/check_process_gates.py` to scan both `docs/plans/active/` and `docs/plans/archive/`.
- Update `_validators/plan_completion.py` to scan both subdirs.
- Update any other tooling/docs that hard-codes `docs/plans/<slug>.md` paths.
- Recapture fidelity lock if needed.

Out of scope:
- Updating historical plan/ADR refs to plans (those are append-only history; refs stay in their current form).
- The `kanon init` scaffold change to consumer-side `docs/plans/active+archive/` (consumers already have flat — moving them is a SEPARATE change with consumer impact; defer to a future PR or to `kanon migrate` if needed).

## Acceptance criteria

- AC1: `docs/plans/active/` contains all status:draft + status:approved plans.
- AC2: `docs/plans/archive/` contains all status:done plans.
- AC3: `docs/plans/README.md` and `docs/plans/roadmap.md` stay at `docs/plans/` root (no status frontmatter to partition by).
- AC4: `scripts/check_process_gates.py` scans both subdirs.
- AC5: 7 standalone gates green; full pytest passes.

## Steps

1. For each plan with status:done, `git mv` to `archive/`.
2. For each plan with status:draft / status:approved, `git mv` to `active/`.
3. Update `scripts/check_process_gates.py` `_find_valid_plan` to scan both subdirs.
4. Update `src/kanon/_validators/plan_completion.py` to scan both subdirs.
5. Run gates + pytest.
6. CHANGELOG entry.
7. Commit + push + PR.

## Verification

- `fd . docs/plans/active -t f -e md | wc -l` → ~38
- `fd . docs/plans/archive -t f -e md | wc -l` → ~66
- `ls docs/plans/*.md` → README.md, roadmap.md (and the new active/active.md if any partition file)
- `kanon verify .` → ok
- 7 gates → ok
