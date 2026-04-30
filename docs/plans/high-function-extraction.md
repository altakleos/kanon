---
status: deferred
date: 2026-04-30
slug: high-function-extraction
---
# Plan: Oversized Function Extraction (Item 8)

## Goal

Extract `parse_fixture()` (174 lines) and `_principle_rewrites()` (83 lines)
into smaller helpers.

## Status: DEFERRED

These are internal functions with full test coverage. The size is a
maintainability concern, not a correctness issue. Deferring alongside the
cli.py modularization (medium-cli-modularization plan).

`init()` (169 lines) and `upgrade()` (91 lines) in cli.py are covered by
the existing deferred cli.py modularization plan.

## Proposed extraction (for future reference)

### parse_fixture (174 lines → ~4 helpers)

- `_parse_frontmatter_fields()` — extract and validate frontmatter keys
- `_parse_assertions()` — parse forbidden_phrases, required_one_of, required_all_of
- `_parse_word_share()` — parse word_share_band
- `_parse_pattern_density()` — parse pattern_density entries

### _principle_rewrites (83 lines → ~2 helpers)

- `_rewrite_frontmatter_id()` — handle the canonical file rename + id update
- `_rewrite_references()` — scan and update cross-references in docs/
