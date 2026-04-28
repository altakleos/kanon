# Plans

Task breakdowns for features. Written AFTER design and ADRs, BEFORE implementation. Plans are permanent records and stay after a feature ships as historical documentation of how it was built.

See [`../sdd-method.md`](../sdd-method.md) § Plans and § How Plans Are Executed.

## Index

| Plan | Feature | Status |
|---|---|---|
| [v0.1-bootstrap](v0.1-bootstrap.md) | Initial kit bootstrap through v0.1.0a1 release | done |
| [v0.1-kit-refactor-and-protocols](v0.1-kit-refactor-and-protocols.md) | Kit bundle refactor + three protocols | done |
| [v0.2-aspect-model](v0.2-aspect-model.md) | Aspects subsume tiers; SDD becomes the first aspect | done |
| [v0.2-invariant-alignment](v0.2-invariant-alignment.md) | Invariant alignment — verify, upgrade, POSIX-only | done |
| [aspect-decoupling](aspect-decoupling.md) | Aspect decoupling — remove sdd as structurally privileged | done |
| [worktrees-aspect](worktrees-aspect.md) | Worktrees aspect implementation | done |
| [release-aspect](release-aspect.md) | Release aspect implementation | done |
| [testing-aspect](testing-aspect.md) | Testing aspect implementation | done |
| [security-aspect](security-aspect.md) | Security aspect implementation | done |
| [deps-aspect](deps-aspect.md) | Deps aspect implementation | done |
| [fidelity-lock](fidelity-lock.md) | Fidelity lock — spec-SHA drift detection | done |
| [invariant-ids](invariant-ids.md) | Invariant IDs — stable anchors for spec invariants | done |
| [verified-by](verified-by.md) | Verified-by — invariant-to-test traceability | done |
| [close-test-gaps](close-test-gaps.md) | Close test coverage gaps | done |
| [cli-spec-realignment](cli-spec-realignment.md) | CLI spec realignment + crash-recovery sentinel (ADR-0024) | done |
| [agents-md-marker-hardening](agents-md-marker-hardening.md) | Line-anchored, fenced-block-aware AGENTS.md marker matching | done |
| [ci-scanner-fixes](ci-scanner-fixes.md) | CI scanner false-positive fixes (`check_deps`, `check_test_quality`) | done |
| [aspect-depth-refactor](aspect-depth-refactor.md) | Refactor `_set_aspect_depth` into named helpers | done |
| [aspect-config](aspect-config.md) | `kanon aspect set-config` and `aspect add --config` | done |
| [aspect-provides](aspect-provides.md) | `provides:` capability registry + generalised `requires:` | done |
| [project-aspects](project-aspects.md) | Project-defined aspects — namespace grammar, loader, migration, validator extension | done |
| [fidelity-and-immutability](fidelity-and-immutability.md) | v0.3 fidelity track + ADR-immutability gate | done |
| [spec-graph-mvp](spec-graph-mvp.md) | Spec-graph MVP — `kanon graph orphans` + `kanon graph rename` | done |
| [review-followups-batch-1](review-followups-batch-1.md) | Recovery model, coverage-floor prose, vocabulary, capability docs | done |
| [principles-clarification](principles-clarification.md) | Clarify kit-shipped principles don't propagate to consumers | done |
| [add-omc-routing-fallbacks](add-omc-routing-fallbacks.md) | Add missing OMC agent routing fallbacks | done |
| [process-gates-ci](process-gates-ci.md) | Process-gate CI enforcement for plan-before-build and spec-before-design | done |
| [index-consistency-validator](index-consistency-validator.md) | Index consistency validator for duplicate README entries | done |
| [test-import-validator](test-import-validator.md) | Test-import validator for orphaned CI test references | done |
| [broaden-spec-gate](broaden-spec-gate.md) | Broaden spec gate to catch all Click registration patterns | done |
| [close-fidelity-coverage-gaps](close-fidelity-coverage-gaps.md) | Close `_fidelity.py` coverage gaps (74 → 90%+) | done |
| [close-validator-coverage-gaps](close-validator-coverage-gaps.md) | Close validator coverage gaps | done |
| [merge-caution-guidance](merge-caution-guidance.md) | Add merge-caution guidance to worktree-lifecycle | done |
| [name-extension-points](name-extension-points.md) | Name the extension-point convention in sdd-method.md | done |
| [phase1-sensei-upstreams](phase1-sensei-upstreams.md) | Upstream sensei worktree hardening + process prose | done |
| [phase2-kit-validators](phase2-kit-validators.md) | Kit-aspect validators via `kanon verify` | draft |
| [plan-src-separation](plan-src-separation.md) | Enforce plan/src commit separation | done |
| [task-playbook](task-playbook.md) | Restructure agent routing as a capability-neutral Task Playbook | done |
| [track-a-doc-fixes](track-a-doc-fixes.md) | Track A documentation/config fixes | done |
| [track-c-dx](track-c-dx.md) | Reduce agent context overhead (Track C) | done |
| [wire-ci-scripts](wire-ci-scripts.md) | Wire unwired CI scripts into GitHub Actions workflows | done |
| [scaffold-v2](scaffold-v2.md) | Thin kernel, routing-index AGENTS.md, three file categories | in-progress |

## Roadmap

See [`roadmap.md`](roadmap.md) for capabilities deferred to later releases.

## Template

```markdown
---
feature: <feature-slug>
serves: docs/specs/<spec>.md
design: docs/design/<mechanism>.md
status: planned | in-progress | done
date: YYYY-MM-DD
---
# Plan: <Feature Name>

## Tasks
- [ ] T1: <description> → `path/to/file`
- [ ] T2: <description> → `path/to/file` (depends: T1)

## Acceptance Criteria
- [ ] AC1: <what must be true when done>
- [ ] verify passes
```
