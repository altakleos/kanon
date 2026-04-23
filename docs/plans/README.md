# Plans

Task breakdowns for features. Written AFTER design and ADRs, BEFORE implementation. Plans are permanent records and stay after a feature ships as historical documentation of how it was built.

See [`../development-process.md`](../development-process.md) § Plans and § How Plans Are Executed.

## Index

| Plan | Feature | Status |
|---|---|---|
| [v0.1-bootstrap](v0.1-bootstrap.md) | Initial kit bootstrap through v0.1.0a1 release | in-progress |
| [v0.1-kit-refactor-and-protocols](v0.1-kit-refactor-and-protocols.md) | Kit bundle refactor + three protocols | done |

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
