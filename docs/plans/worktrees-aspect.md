# Plan: Implement Worktrees Aspect

Spec at `docs/specs/worktrees.md` has been approved.

## Goal

Implement the `worktrees` aspect as defined in the accepted spec and ADR-0014. Ship it as `stability: experimental` with depth range 0–2.

## Deliverables

### 1. Kit bundle: `src/kanon/kit/aspects/worktrees/`

```
aspects/worktrees/
├── manifest.yaml
├── agents-md/
│   ├── depth-0.md
│   ├── depth-1.md
│   └── depth-2.md
├── sections/
│   └── branch-hygiene.md
├── protocols/
│   └── worktree-lifecycle.md
└── files/
    └── scripts/
        ├── worktree-setup.sh
        ├── worktree-teardown.sh
        └── worktree-status.sh
```

### 2. Top-level manifest registration

Add to `src/kanon/kit/manifest.yaml`:
```yaml
  worktrees:
    path: aspects/worktrees
    stability: experimental
    depth-range: [0, 2]
    default-depth: 1
    requires:
      - "sdd >= 1"
```

### 3. Tests

Add tests to `tests/test_kit_integrity.py` validating:
- worktrees aspect directory exists with expected structure
- manifest.yaml is valid and has depth-0, depth-1, depth-2 keys
- agents-md files exist for each depth
- protocol has required frontmatter keys
- section file exists

Add CLI integration tests to `tests/test_cli.py`:
- `test_aspect_add_worktrees` — init with sdd depth 1, add worktrees, verify files scaffolded
- `test_worktrees_requires_sdd` — init with sdd depth 0, attempt to add worktrees, verify dependency check
- `test_worktrees_depth_1_no_scripts` — worktrees at depth 1, verify protocol+section present but no scripts/
- `test_worktrees_depth_2_has_scripts` — worktrees at depth 2, verify scripts/ scaffolded

## Content Specifications

### manifest.yaml
```yaml
# Worktrees aspect — isolated parallel execution via git worktrees.
# Depth 0: opt-out. Depth 1: prose guidance. Depth 2: prose + automation.
# Strict-superset semantics: depth-N is the union of depth-0..depth-N.

depth-0:
  files: []
  protocols: []
  sections: []

depth-1:
  files: []
  protocols:
    - worktree-lifecycle.md
  sections:
    - branch-hygiene
    - protocols-index

depth-2:
  files:
    - scripts/worktree-setup.sh
    - scripts/worktree-teardown.sh
    - scripts/worktree-status.sh
  protocols: []
  sections: []
```

### agents-md/depth-0.md
Empty/minimal — aspect enabled but no content scaffolded.

### agents-md/depth-1.md
Contains `<!-- kanon:begin:worktrees/branch-hygiene -->` / `<!-- kanon:end:worktrees/branch-hygiene -->` markers. References the lifecycle protocol.

### agents-md/depth-2.md
Same as depth-1 plus reference to shell helper scripts in `scripts/`.

### sections/branch-hygiene.md
Prose section covering:
- Change-scope trigger: multi-file/multi-step changes warrant a worktree
- `git worktree list` as secondary heuristic
- Branch naming: `.worktrees/<slug>/` convention
- Integration cadence: rebase from main regularly
- Trivial changes (typo, single-file) stay in main checkout

### protocols/worktree-lifecycle.md
Frontmatter: `status: accepted`, `date: 2026-04-23`, `depth-min: 1`, `invoke-when: multi-file or multi-step change, or git worktree list shows active worktrees`

Steps covering:
1. Decision: assess change scope → worktree or main checkout
2. Setup: branch naming, `git worktree add`
3. Work: normal development in the worktree
4. Integration: rebase cadence, conflict resolution
5. Teardown: non-destructive cleanup, stale detection

### files/scripts/worktree-setup.sh
Shell script: creates `.worktrees/<slug>` worktree with branch naming convention. Non-destructive (checks if exists first).

### files/scripts/worktree-teardown.sh
Shell script: removes worktree. Refuses if uncommitted changes exist. Reports status.

### files/scripts/worktree-status.sh
Shell script: lists active worktrees with age, branch, and status.

## Execution Order

1. Create all kit bundle files (manifest, agents-md, sections, protocols, scripts)
2. Register in top-level manifest.yaml
3. Add tests
4. Run full test suite + linter + type checker
5. Verify `kanon verify` still passes on this repo

## Success Criteria

- All existing 141 tests pass
- New worktrees tests pass
- `ruff check` clean
- `mypy` clean
- Coverage stays above 90%
