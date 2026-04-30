---
status: done
date: 2026-04-30
---
# Plan: Address low-priority gaps from analysis

## Goal

Close the remaining low-severity findings from the codebase analysis.

## Tasks

- [x] Add a `Makefile` with common dev targets (`test`, `lint`, `typecheck`, `e2e`, `check`)
- [x] Add tests for `_banner.py` (`_BANNER` content, `_should_emit_banner` logic)
- [x] ~~Add `uv.lock` for CI reproducibility~~ — already exists

## Acceptance criteria

- `make check` runs lint + typecheck + tests in sequence
- `_banner.py` has test coverage for both exported symbols
- All existing tests still pass
