# kanon

**Portable, self-hosting Spec-Driven Development kit for LLM-agent-driven repos.**

```bash
pipx install kanon-kit
kanon init ~/myproject --tier 1
cd ~/myproject           # open with any LLM coding agent
```

---

`kanon` packages a proven SDD methodology (specs → design → ADRs → plans → implementation → verification) as a pip-installable kit. Drop it into any repo, point your LLM agent at the scaffolded `AGENTS.md`, and the agent becomes a process-disciplined contributor: plans before building, specs before designing, verification as a first-class authoritative layer.

The kit is **tiered** — start at tier-0 (just an `AGENTS.md` for vibe-coding), grow to tier-3 (full platform-scale stack) as the project matures. `kanon tier set <N>` moves any project between tiers non-destructively.

The kit is **self-hosting** — this repo is itself a tier-3 `kanon` project. The tier-3 scaffolded bundle and this repo's own `docs/` share source of truth, enforced by CI.

## Quickstart

```bash
# Install
pipx install kanon-kit

# Scaffold a new project
kanon init ~/myproject --tier 1

# Change tiers as the project grows
kanon tier set ~/myproject 2

# Keep the kit up to date
kanon upgrade ~/myproject

# Verify the project's SDD shape
kanon verify ~/myproject
```

## Tiers

| Tier | For | Artifacts |
|------|-----|-----------|
| 0 | Prototypes, vibe-coding, one-off scripts | `AGENTS.md` |
| 1 | Solo developer shipping a real tool | + `docs/decisions/`, `docs/plans/` |
| 2 | Team work with user-facing promises | + `docs/specs/` |
| 3 | Platform projects, multi-team | + `docs/design/`, `docs/foundations/` |

Tiers insulate: a tier-0 user never sees tier-3 artifacts. Tier migration is first-class — `kanon tier set <target> <N>` promotes or demotes any project between any two tiers without destroying user content.

## Supported agent harnesses

AGENTS.md is the canonical single source of truth. `kanon init` writes tool-specific shims pointing at it, so the same rules apply across:

- Claude Code (`CLAUDE.md`)
- OpenAI Codex (`AGENTS.md`, native)
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

**Early alpha (v0.2).** The kit ships two aspects (`sdd` at depth 0–3, `worktrees` at depth 0–2), the aspect model, cross-harness shims, and self-hosting assertions. See [the roadmap](docs/plans/roadmap.md) for what's coming.

## License

Apache 2.0 — see [LICENSE](LICENSE).
