---
status: accepted
date: 2026-05-03
---
# ADR-0050: Kernel-flatten deferral — supersedes ADR-0049 §1(2)

## Context

[ADR-0049](0049-monorepo-layout.md) §1(2) and Decision D2 (vote 6–1) committed to renaming `src/kanon/` → `kernel/` so the substrate's most-edited file lands at depth 2. The Implementation Roadmap step E was sequenced last, with P7's empirical estimate of 2–4 hours for the rename + path-citing-file updates.

Implementation revealed an unanticipated engineering constraint: **Hatch's `[tool.hatch.build.targets.wheel.sources]` source-remapping does not survive editable installs (PEP 660)**. The mapping `"kernel" = "kanon"` (rename source dir to wheel-import path) produces a build-time error from the `editables` library:

> in the `sources` option changes a prefix rather than removes it

The supported remap is *prefix strip* (`"src" = ""`), not *prefix rename*. After `git mv src/kanon kernel` and updating `pyproject.toml` accordingly, `uv sync --reinstall` succeeded but `python -c "import kanon"` raised `ModuleNotFoundError: No module named 'kanon'`. The rename is incompatible with the project's `uv sync` development workflow (which depends on PEP 660 editable installs).

Three real options exist for landing ADR-0049 §1(2):

1. **Rename the Python package** (`kanon` → `kernel`). Source: `kernel/cli.py` at depth 2 ✓. Wheel: ships as `kernel-substrate` with `from kernel.cli import main`. CLI command stays `kanon` (Click app's name). BREAKING for any code that does `from kanon.X import Y` (substrate-internal: tests, `_validators/`, `_resolutions.py` import-checks). Per ADR-0048 there are zero current external consumers; rename cost is bounded to the kanon repo (~1–2 hours of `kanon\.` → `kernel\.` grep-replace).

2. **Compromise: `src/kanon/` → `kernel/kanon/`.** Source: `kernel/kanon/cli.py` at depth 3 (same as before; only the wrapper changed name). Hatch `packages = ["kernel/kanon"]` works without remap; editable installs work. Imports unchanged. Defeats the panel's "depth 2" goal but achieves a semantic rename of the wrapper.

3. **Skip kernel-flatten entirely.** Accept `src/kanon/cli.py` at depth 3 as-is. The other 5 ADR-0049 §1 rules deliver most of the panel's diagnosed pain points (bundle collapse, kill `packaging/`, `ci/`→`scripts/`, plans active+archive, byte-mirror loosened). The kernel-flatten was the most contested move (P7 dissented on cost grounds in R3).

## Decision

**ADR-0049 §1(2) (and Decision D2's `kernel/` half) is deferred indefinitely.** Option 3 (skip kernel-flatten) is the working position until a future ADR re-opens with a concrete plan for one of the other two options.

The deferral is normative: subsequent contributors should NOT attempt the simple `git mv src/kanon kernel` + Hatch source-remap path that this ADR documents as broken. Any future kernel-flatten requires either (a) a Python-package rename (Option 1) or (b) acceptance of depth-3 wrapper-rename (Option 2). The trade-off requires explicit ADR ratification, not implicit choice during a migration PR.

ADR-0049's other §1 rules — §1(1) kill `packaging/`, §1(3) per-aspect bundles, §1(4) docs/plans/active+archive, §1(5) `ci/`→`scripts/`, §1(6) hard substrate-vs-data boundary, §1(7) `aspects/` directory naming — and Decisions D1 (committed `.kanon/` with loosened byte-mirror) and D3 (`aspects/` not `disciplines/`) ARE all implemented and stand unchanged.

## Alternatives Considered

1. **Implement Option 1 in this ADR (Python package rename).** Rejected for now. The rename is the right destination but the panel did not anticipate it as the path; making it a single commit-cycle decision under the original ADR's authority would over-stretch the panel's mandate. Surface as a future ADR with explicit consideration of the one-time consumer-doc churn.

2. **Implement Option 2 (kernel/kanon wrapper).** Rejected for now. The panel rejected `src/<pkg>/` precisely because of the depth-3 wrapper tax; replacing `src/` with `kernel/` while keeping the wrapper preserves the tax. If a future ADR adopts Option 2 anyway, that's a reasoned trade-off; doing it implicitly under ADR-0049's authority is not.

3. **Migrate from Hatch to setuptools (`package_dir={"kanon": "kernel"}` works for editable installs).** Rejected for now. Build-tool migration is a much larger structural change than the kernel-flatten itself; it would re-litigate decisions outside this ADR's scope and introduce its own risks.

4. **Patch the `editables` library upstream + wait for the fix.** Rejected. The known limitation has been documented since the linked GitHub issue (pfmoore/editables#20) without resolution. Waiting on upstream for a ratified internal layout is not a viable migration plan.

## Consequences

- **`src/kanon/cli.py` stays at depth 3.** The substrate's most-edited file remains one `cd` deeper than the panel's optimal. The cost is small per edit; the cumulative cost over many releases is what the panel called out. We accept that cost until a future ADR chooses Option 1 or 2.
- **No kernel-flatten implementation in v0.4.0a4.** The release captures 5 of 6 ADR-0049 §1 rules. CHANGELOG is honest about what shipped vs. what was deferred.
- **ADR-0049 §1(2) is partially superseded.** ADR-0049's body remains unchanged (per ADR-immutability); ADR-0050 supersedes the kernel-flatten clause specifically. ADR-0049 §1(7) (`aspects/` directory) survives because it was not implemented as a top-level rename either; for the same reason (the source-remap wouldn't work for `kanon_reference` either), it stays at `src/kanon_reference/aspects/kanon_<slug>/` for now. A future ADR may revisit both flattens together.
- **No re-opening on the kernel-flatten without an ADR.** A contributor cannot land `git mv src/kanon kernel` in a future PR claiming "ADR-0049 says so" — this ADR explicitly forecloses that path and points at the engineering constraint.

## Config Impact

None. ADR-0050 is purely about the source-tree layout decision; consumer config (`.kanon/config.yaml`) is unaffected.

## References

- [ADR-0049](0049-monorepo-layout.md) — parent decision; §1(2) is what this supersedes.
- [ADR-0048](0048-kanon-as-protocol-substrate.md) — protocol-substrate commitment; the "no current consumers" basis for the bounded cost of any future Python-package rename.
- [ADR-0032](0032-adr-immutability-gate.md) — ADR body immutability discipline; ADR-0049's body stays unchanged; ADR-0050 supersedes by adding, not editing.
- [editables PR #20](https://github.com/pfmoore/editables/issues/20) — upstream tracking issue for the prefix-rename limitation.
- [Hatch build target docs](https://hatch.pypa.io/latest/config/build/#sources) — documentation for `[tool.hatch.build.targets.wheel.sources]`.
