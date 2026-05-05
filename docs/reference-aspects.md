# Reference aspects shipped by this distribution

<!-- GENERATED FILE — DO NOT EDIT MANUALLY.
Source of truth: `pyproject.toml` `[project.entry-points."kanon.aspects"]`
+ each aspect's `packages/kanon-aspects/src/kanon_aspects/aspects/<slug>/manifest.yaml`.
Regenerate via: `python scripts/gen_reference_aspects.py`.
Drift is enforced by CI via `python scripts/gen_reference_aspects.py --check`.
Per ADR-0055 the per-aspect manifest is canonical; this file mirrors it for human review. -->

Aspects shipped by this distribution. The substrate (`kanon-core`) ships zero aspects per ADR-0044 substrate-independence; the table below enumerates the demonstrations the `kanon-aspects` distribution publishes via the `kanon.aspects` Python entry-point group (per ADR-0040).

Per `P-protocol-not-product`, these are reference implementations — not the substrate's product. A third-party publisher (an `acme-<vendor>-aspects` distribution) shipping its own aspects via the same entry-point group resolves through the same substrate code paths and would render an analogous table from its own pyproject.

| Aspect | Stability | Depth range | Default depth | Description |
|---|---|---|---|---|
| `kanon-deps` | experimental | 0–2 | 1 | Dependency hygiene and CI scanner |
| `kanon-fidelity` | experimental | 0–1 | 1 | Behavioural conformance via lexical assertions |
| `kanon-release` | experimental | 0–2 | 1 | Release checklist, preflight, and CLI gate |
| `kanon-sdd` | stable | 0–3 | 1 | Spec-Driven Development: plans, specs, design docs, foundations |
| `kanon-security` | experimental | 0–2 | 1 | Secure-by-default protocols and CI scanner |
| `kanon-testing` | experimental | 0–3 | 1 | Test discipline, AC-first TDD, error diagnosis |
| `kanon-worktrees` | experimental | 0–2 | 1 | Worktree isolation for parallel work |

