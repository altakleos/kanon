# kanon

**Portable, self-hosting development-discipline kit for LLM-agent-driven repos.**

```bash
pipx install kanon-kit
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
pipx install kanon-kit

# Scaffold a new project (SDD at depth 1)
kanon init ~/myproject --tier 1

# Add worktree isolation
kanon aspect set-depth ~/myproject worktrees 1

# Grow SDD depth as the project matures
kanon aspect set-depth ~/myproject sdd 2

# Keep the kit up to date
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

### SDD depths

| Depth | For | Artifacts |
|-------|-----|-----------|
| 0 | Prototypes, vibe-coding | `AGENTS.md` |
| 1 | Solo developer shipping a real tool | + `docs/decisions/`, `docs/plans/` |
| 2 | Team work with user-facing promises | + `docs/specs/` |
| 3 | Platform projects, multi-team | + `docs/design/`, `docs/foundations/` |

The legacy `kanon tier set` command is preserved as sugar for `kanon aspect set-depth <target> sdd <N>`.

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
- [Development process](docs/development-process.md) — the SDD method
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

## Status

**Early alpha (v0.2.0a5).** The kit ships two aspects (`sdd` at depth 0–3, `worktrees` at depth 0–2), the aspect model, cross-harness shims, and self-hosting assertions. See [the roadmap](docs/plans/roadmap.md) for what's coming.

## License

Apache 2.0 — see [LICENSE](LICENSE).
