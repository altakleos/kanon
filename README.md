# kanon

**A protocol substrate for spec-driven discipline in LLM-agent-driven repos.**

```bash
uv tool install kanon-kit
kanon init ~/myproject --profile solo
cd ~/myproject           # open with any LLM coding agent
```

**Requires POSIX (Linux / macOS).** Windows is not supported.

---

`kanon` is a **protocol substrate** ([ADR-0048](docs/decisions/0048-kanon-as-protocol-substrate.md)) — a small kernel (`kanon-core`) plus a separately distributed reference set of opt-in disciplines (`kanon-aspects`) that publishers and consumers compose. Drop it into any repo, point your LLM agent at the scaffolded `AGENTS.md`, and the agent becomes a process-disciplined contributor: plans before building, specs before designing, worktrees for parallel work, verification as a first-class layer.

The substrate is **publisher-symmetric**: kit-shipped (`kanon-`), consumer-defined (`project-`), and third-party (`acme-`) aspects all flow through identical code paths. The substrate makes no claim about which disciplines are "right" — it only enforces the grammar by which any publisher's disciplines are authored, composed, and verified.

The substrate is **self-hosting** — this repo opts into the seven reference aspects via the same publisher recipe (`.kanon/recipes/reference-default.yaml`) any external consumer would use, and passes `kanon verify .` against itself on every commit ([ADR-0044](docs/decisions/0044-substrate-self-conformance.md)).

## Quickstart

```bash
# Install
uv tool install kanon-kit          # or: pipx install kanon-kit

# Scaffold a new project — pick a profile that matches your team shape
kanon init ~/myproject --profile solo     # or: --profile team / --profile max
                                           # or: --aspects kanon-sdd:1,kanon-worktrees:1

# Add shell helpers for worktree isolation (worktrees 1 → 2)
kanon aspect set-depth ~/myproject kanon-worktrees 2

# Grow SDD depth as the project matures
kanon aspect set-depth ~/myproject kanon-sdd 2

# Keep the substrate up to date
uv tool upgrade kanon-kit          # or: pipx upgrade kanon-kit
kanon upgrade ~/myproject

# Verify the project's shape
kanon verify ~/myproject
```

## Reference aspects

The seven reference aspects ship via `kanon-aspects` (and re-exported by `kanon-kit`); each is opt-in and individually depth-dialed.

| Aspect | Depth range | Stability | What it provides |
|--------|-------------|-----------|------------------|
| `kanon-sdd` | 0–3 | stable | Spec-Driven Development: plans, specs, design docs, foundations, verification |
| `kanon-worktrees` | 0–2 | experimental | Worktree isolation: prose guidance (depth 1) + shell helpers (depth 2) |
| `kanon-release` | 0–2 | experimental | Disciplined release publishing: protocol (depth 1) + preflight/publishing protocols (depth 2) |
| `kanon-testing` | 0–3 | experimental | Test discipline + AC-first TDD: protocols (depth 1–2) + invariants (depth 3) |
| `kanon-security` | 0–2 | experimental | Secure-by-default protocols (depth 1–2) |
| `kanon-deps` | 0–2 | experimental | Dependency hygiene protocol (depth 1–2) |
| `kanon-fidelity` | 0–1 | experimental | Behavioural-conformance verification: lexical assertions over committed agent transcripts (depth 1) |

Aspect names are namespaced by source publisher (`kanon-`, `project-`, `acme-`); bare-name shorthand at the CLI input surface (`sdd` → `kanon-sdd`, etc.) is **deprecated** in v0.4 — it privileges the kit namespace and breaks publisher symmetry. New scripts and documentation should use the full `kanon-<local>` form.

### Project-defined and third-party aspects

Consumers may declare their own aspects under `.kanon/aspects/project-<local>/manifest.yaml` (loaded via filesystem; see [`docs/specs/project-aspects.md`](docs/specs/project-aspects.md)). Third-party publishers register their aspects via the `kanon.aspects` Python entry-point group ([ADR-0040](docs/decisions/0040-kernel-reference-runtime-interface.md)). All three namespaces verify under identical rules — see [ADR-0042](docs/decisions/0042-verification-scope-of-exit-zero.md) for `kanon verify` exit-zero semantics.

The two filesystem source namespaces are **strictly source-bounded**:

- `kanon-<local>` — reference-shipped, loaded from the installed `kanon-aspects` distribution via entry-points.
- `project-<local>` — consumer-defined, loaded from `.kanon/aspects/`.

A `kanon-` directory under `.kanon/aspects/` is rejected at load. Cross-source path collisions raise a `ClickException` at scaffold time. Capability substitutability is source-neutral: a `project-<local>`'s `provides:` capability can satisfy a kit-aspect's 1-token `requires:` predicate.

### SDD depths

| Depth | For | Artifacts |
|-------|-----|-----------|
| 0 | Prototypes, vibe-coding | `AGENTS.md` |
| 1 | Solo developer shipping a real tool | + `docs/decisions/`, `docs/plans/` |
| 2 | Team work with user-facing promises | + `docs/specs/` |
| 3 | Platform projects, multi-team | + `docs/design/`, `docs/foundations/` |

## Supported agent harnesses

`AGENTS.md` is the canonical single source of truth. `kanon init` writes tool-specific shims pointing at it, so the same rules apply across:

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
- [De-opinionation manifesto](docs/foundations/de-opinionation.md) — why v0.4 is a protocol substrate, not a kit
- [Aspect model](docs/design/aspect-model.md) — how aspects and depths work
- [Dialect grammar spec](docs/specs/dialect-grammar.md) — realization-shape, dialect versioning, composition
- [Distribution + cadence spec](docs/specs/release-cadence.md) — kernel/reference split, release pacing
- [Substrate self-conformance spec](docs/specs/substrate-self-conformance.md) — independence + self-host invariants
- [Resolutions spec](docs/specs/resolutions.md) — runtime-binding model
- [ADR-0048](docs/decisions/0048-kanon-as-protocol-substrate.md) — the protocol-substrate commitment
- [Development process](docs/sdd-method.md) — the SDD method
- [ADR index](docs/decisions/README.md) — the substrate's own decisions
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
.venv/bin/pytest                    # fast tests
.venv/bin/pytest -m e2e --no-cov    # installed-package E2E tests
.venv/bin/pytest -m ''              # everything (deselected included)
```

New contributor? Start with [`docs/contributing.md`](docs/contributing.md) — module map, gate matrix, and a "where does my change go?" decision flow.

## Security model

`kanon preflight` and `kanon verify` execute commands and code from project-local config files (`.kanon/config.yaml`, project-aspect manifests). The trust boundary is **repo write-access**: if you can commit to the repo, you can control what these commands run. This is the same trust model as `Makefile`, `package.json` scripts, or `.github/workflows/` — cloning a repo implies trusting its build/check configuration.

See [ADR-0036](docs/decisions/0036-secure-defaults-config-trust-carveout.md) for the full rationale.

## Status

**Early alpha (v0.4.0a1).** The "kit → protocol substrate" pivot ([ADR-0045](docs/decisions/0045-de-opinionation-transition.md), [ADR-0048](docs/decisions/0048-kanon-as-protocol-substrate.md)) lands here: kernel-reference split skeleton, entry-point discovery for aspects, dialect grammar with realization-shape + composition algebra, resolutions replay engine, substrate-independence CI gate, deprecated-on-arrival `kanon migrate v0.3 → v0.4`. v0.3.x consumers cannot upgrade in place; use `kanon migrate` once. See [the roadmap](docs/plans/roadmap.md) for what's coming.

## License

Apache 2.0 — see [LICENSE](LICENSE).
