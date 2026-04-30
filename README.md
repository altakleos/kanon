# kanon

**Portable, self-hosting development-discipline kit for LLM-agent-driven repos.**

```bash
uv tool install kanon-kit
kanon init ~/myproject --tier 1
cd ~/myproject           # open with any LLM coding agent
```

**Requires POSIX (Linux / macOS).** Windows is not supported.

---

`kanon` packages development disciplines — starting with Spec-Driven Development and worktree isolation — as a pip-installable kit. Drop it into any repo, point your LLM agent at the scaffolded `AGENTS.md`, and the agent becomes a process-disciplined contributor: plans before building, specs before designing, worktrees for parallel work, verification as a first-class layer.

The kit is **aspect-oriented** — disciplines are packaged as opt-in *aspects*, each with its own depth dial. Enable only what you need; grow without ceremony you don't need yet.

The kit is **self-hosting** — this repo is itself a `kanon` project running `sdd` at depth 3 and `worktrees` at depth 2. The scaffolded bundle and this repo's own `docs/` share source of truth, enforced by CI.

## Quickstart

```bash
# Install
uv tool install kanon-kit          # or: pipx install kanon-kit

# Scaffold a new project (every default aspect at depth 1, ADR-0035)
kanon init ~/myproject --tier 1

# Add shell helpers for worktree isolation (worktrees 1 → 2)
kanon aspect set-depth ~/myproject worktrees 2

# Grow SDD depth as the project matures
kanon aspect set-depth ~/myproject sdd 2

# Keep the kit up to date
uv tool upgrade kanon-kit          # or: pipx upgrade kanon-kit
kanon upgrade ~/myproject

# Verify the project's shape
kanon verify ~/myproject
```

## Aspects

Disciplines are packaged as *aspects* — opt-in bundles of prose rules, protocols, AGENTS.md sections, and scaffolded files.

| Aspect | Depth range | Stability | What it provides |
|--------|-------------|-----------|------------------|
| `sdd` | 0–3 | stable | Spec-Driven Development: plans, specs, design docs, foundations, verification |
| `worktrees` | 0–2 | experimental | Worktree isolation: prose guidance (depth 1) + shell helpers (depth 2) |
| `release` | 0–2 | experimental | Disciplined release publishing: protocol (depth 1) + preflight script + reference workflow (depth 2) |
| `testing` | 0–3 | experimental | Test discipline + AC-first TDD: protocols (depth 1–2) + automated quality enforcement (depth 3) |
| `security` | 0–2 | experimental | Secure-by-default protocols (depth 1) + CI pattern scanner for common anti-patterns (depth 2) |
| `deps` | 0–2 | experimental | Dependency hygiene protocol (depth 1) + CI scanner for unpinned versions and duplicate-purpose packages (depth 2) |
| `fidelity` | 0–1 | experimental | Behavioural-conformance verification: lexical assertions over committed agent transcripts (depth 1) |

The canonical name of each kit-shipped aspect carries a `kanon-` source-namespace prefix (e.g., `kanon-sdd`, `kanon-worktrees`); bare names at every CLI input surface sugar to the `kanon-` namespace, so existing invocations like `kanon aspect set-depth . sdd 2` continue to work. See [ADR-0028](docs/decisions/0028-project-aspects.md) and [`docs/specs/project-aspects.md`](docs/specs/project-aspects.md).

### Project-defined aspects

Consumers may declare their own aspects under `.kanon/aspects/project-<local>/manifest.yaml`. The CLI discovers them transparently — they participate in `aspect list --target`, `aspect info <name> --target`, `aspect add`, `aspect remove`, `aspect set-depth`, `aspect set-config`, and `verify` alongside kit-shipped aspects.

A project-aspect's manifest mirrors the shape of a kit-side sub-manifest: registry fields (`stability`, `depth-range`, `default-depth`, optional `requires`/`provides`/`suggests`) and per-depth `depth-N: {files, protocols, sections}` entries in the same file. Optionally, a project-aspect may declare `validators: [<dotted.module.path>, ...]` — `kanon verify` imports each module in-process and invokes its `check(target, errors, warnings) -> None` entrypoint, with findings flowing into the same JSON report the kit's structural checks populate.

The two source namespaces are **strictly source-bounded**:

- `kanon-<local>` — kit-shipped, loaded from the installed pip kit.
- `project-<local>` — consumer-defined, loaded from `.kanon/aspects/`.

A `kanon-` directory under `.kanon/aspects/` is rejected at load with a single-line error; bare names sugar to `kanon-` only (project-aspects must always be referenced by their full `project-<local>` name). Cross-source path collisions (a project-aspect declaring the same `files/` path as a kit-aspect) raise a `ClickException` at scaffold time.

Capability substitutability is source-neutral: a `project-<local>`'s `provides:` capability can satisfy a kit-aspect's 1-token `requires:` predicate.

Per [`docs/specs/project-aspects.md`](docs/specs/project-aspects.md) and [ADR-0028](docs/decisions/0028-project-aspects.md). Third-party aspect publishing via pip (the `acme-` namespace) remains deferred per ADR-0012; project-aspects ride along with the consumer's own git history.

### SDD depths

| Depth | For | Artifacts |
|-------|-----|-----------|
| 0 | Prototypes, vibe-coding | `AGENTS.md` |
| 1 | Solo developer shipping a real tool | + `docs/decisions/`, `docs/plans/` |
| 2 | Team work with user-facing promises | + `docs/specs/` |
| 3 | Platform projects, multi-team | + `docs/design/`, `docs/foundations/` |

The legacy `kanon tier set` command is preserved as sugar for a uniform depth raise across all default aspects, capped at each aspect's maximum (ADR-0035).

## Supported agent harnesses

AGENTS.md is the canonical single source of truth. `kanon init` writes tool-specific shims pointing at it, so the same rules apply across:

- Claude Code (`CLAUDE.md`)
- Cursor (`.cursor/rules/kanon.mdc`)
- GitHub Copilot (`.github/copilot-instructions.md`)
- Windsurf (`.windsurf/rules/kanon.md`)
- Cline (`.clinerules/kanon.md`)
- Roo Code (`.roo/rules/kanon.md`)
- JetBrains AI (`.aiassistant/rules/kanon.md`)
- Kiro (`.kiro/steering/kanon.md`)

New harness support: add an entry to `harnesses.yaml`; no Python change required.

## Documentation

- [Vision](docs/foundations/vision.md) — what kanon is and is not
- [Aspect model](docs/design/aspect-model.md) — how aspects and depths work
- [Aspects spec](docs/specs/aspects.md) — the aspects contract
- [ADR-0012](docs/decisions/0012-aspect-model.md) — decision record for the aspect model
- [Development process](docs/sdd-method.md) — the SDD method
- [ADR index](docs/decisions/README.md) — the kit's own decisions
- [Roadmap](docs/plans/roadmap.md) — capabilities deferred to later releases
- [AGENTS.md](AGENTS.md) — contributor boot document

## Development

```bash
# With uv (recommended — fast, reproducible)
uv sync

# Without uv
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Run tests:

```bash
.venv/bin/pytest              # fast tests (~1.5s)
.venv/bin/pytest -m e2e       # installed-package E2E tests (~7s)
.venv/bin/pytest -m ''        # everything
```

## Security model

`kanon preflight` and `kanon verify` execute commands and code from project-local config files (`.kanon/config.yaml`, project-aspect manifests). The trust boundary is **repo write-access**: if you can commit to the repo, you can control what these commands run. This is the same trust model as `Makefile`, `package.json` scripts, or `.github/workflows/` — cloning a repo implies trusting its build/check configuration.

See [ADR-0036](docs/decisions/0036-secure-defaults-config-trust-carveout.md) for the full rationale.

## Status

**Early alpha (v0.3.1a2).** The kit ships seven aspects (`sdd` at depth 0–3; `worktrees`, `release`, `security`, `deps` at depth 0–2; `testing` at depth 0–3; `fidelity` at depth 0–1), the aspect model with a `provides:` capability registry, cross-harness shims, and self-hosting assertions. See [the roadmap](docs/plans/roadmap.md) for what's coming.

## License

Apache 2.0 — see [LICENSE](LICENSE).
