---
status: accepted
design: "Follows ADR-0004"
date: 2026-04-22
realizes:
  - P-verification-co-authored
stressed_by:
  - platform-team
fixtures:
  - tests/test_cli.py
  - tests/scripts/test_check_foundations.py
  - tests/scripts/test_check_links.py
  - tests/scripts/test_release_preflight.py
invariant_coverage:
  INV-verification-contract-tier-aware:
    - tests/test_cli.py::test_init_verify_returns_ok
  INV-verification-contract-required-files-per-tier:
    - tests/test_cli_verify.py::test_verify_fails_on_missing_file
  INV-verification-contract-foundation-backreferences:
    - tests/scripts/test_check_foundations.py::test_real_repo_passes
  INV-verification-contract-markdown-link-resolution:
    - tests/scripts/test_check_links.py::test_real_repo_passes
  INV-verification-contract-agents-md-marker-integrity:
    - tests/test_cli_verify.py::test_verify_fails_on_missing_marker
    - tests/test_cli_verify.py::test_verify_marker_imbalance
  INV-verification-contract-changelog-entry:
    - tests/scripts/test_release_preflight.py::test_changelog_entry_present
  INV-verification-contract-output-format:
    - tests/test_cli.py::test_init_verify_returns_ok
  INV-verification-contract-does-not-execute-code:
    - tests/test_cli.py::test_init_verify_returns_ok
  INV-verification-contract-model-version-compat:
    - tests/test_cli.py::test_init_verify_returns_ok
  INV-verification-contract-fidelity-replay-carveout:
    - tests/test_fidelity.py::test_invariant_anchor_resolves
  INV-verification-contract-exit-zero-scope:
    - tests/test_cli.py::test_init_verify_returns_ok
---
# Spec: Verification contract — what `kanon verify` guarantees

## Intent

Define the checks `kanon verify <target>` runs on a consumer repo, the error/warning taxonomy it emits, and the guarantees it provides to the consumer.

## Invariants

<!-- INV-verification-contract-tier-aware -->
1. **Aspect-aware.** `verify` reads `.kanon/config.yaml` → `aspects:` mapping and computes the expected file set as a function of each aspect's declared depth. Absence of `config.yaml` is a hard error.
<!-- INV-verification-contract-required-files-per-tier -->
2. **Required files per aspect depth.** For each enabled aspect at its declared depth, `verify` checks that the files named in the aspect's depth manifest all exist. Missing required files are hard errors (exit non-zero).
<!-- INV-verification-contract-foundation-backreferences -->
3. **Foundation backreferences (CI-only).** At sdd depth ≥ 3, `scripts/check_foundations.py` walks every spec's `serves:`/`realizes:`/`stressed_by:` frontmatter and asserts every slug resolves to an existing foundation file of the matching type. This check runs as a standalone CI script, not as part of `kanon verify`.
<!-- INV-verification-contract-markdown-link-resolution -->
4. **Markdown link resolution.** At sdd depth ≥ 2, `verify` scans every `*.md` file under `docs/` and asserts every relative link resolves to an existing path. Identical to `scripts/check_links.py`.
<!-- INV-verification-contract-agents-md-marker-integrity -->
5. **AGENTS.md marker integrity.** `verify` checks that every `<!-- kanon:begin:X -->` has a matching `<!-- kanon:end:X -->` and that the set of enabled sections matches the declared aspects and depths. Mismatches are hard errors.
<!-- INV-verification-contract-model-version-compat -->
6. **Model-version compatibility (warning-level).** Per ADR-0005, `verify` emits warnings for transcript fixtures whose `validated-against:` frontmatter does not include the consumer's declared default model. Warnings do not fail the exit code in v0.1.
<!-- INV-verification-contract-changelog-entry -->
7. **CHANGELOG entry for current version (CI-only).** The release aspect's `scripts/release-preflight.py` checks for a dated CHANGELOG entry matching the version at release time. This is a release-gate check, not a `kanon verify` invariant.
<!-- INV-verification-contract-output-format -->
8. **Output format.** `verify` prints a JSON report to stdout (plus a short human-readable summary to stderr), with fields `{target, aspects, status, errors: [...], warnings: [...]}`. Exit 0 on `status: ok`, non-zero otherwise.
<!-- INV-verification-contract-does-not-execute-code -->
9. **Does not execute code by default.** In the default flow, `verify` is read-only against the target repo. It does not run the consumer's tests, does not import consumer Python, does not call out to the consumer's LLM model. It is a static check. The single carve-out from this invariant is INV-10 below; no other behavioural extension is authorised by this spec.
<!-- INV-verification-contract-fidelity-replay-carveout -->
10. **Fidelity-fixture replay (carve-out from INV-9).** When and only when the consumer has enabled an aspect that declares the `behavioural-verification` capability (per ADR-0026) — including the kit-shipped `kanon-fidelity` aspect at depth ≥ 1 — `verify` MAY load `.kanon/fidelity/<protocol>.dogfood.md` capture files from the consumer's tree and run lexical assertions over them: `forbidden_phrases`, `required_one_of`, `required_all_of` matched against named-actor turns. The carve-out is bounded by four constraints, each of which is a hard contract:

    1. **Text-only replay.** No LLM calls, no subprocesses, no test-runner invocation, no Python imports of consumer code.
    2. **Read-only against committed files.** Replay only reads files already present in the consumer's tree at the SHA `verify` is run against; it never writes captures, never spawns agents.
    3. **Aspect-gated.** Bare `kanon verify` on a project that has not enabled an aspect declaring `behavioural-verification` is structural-only — exactly INV-9's default flow.
    4. **No latency contract change.** Tier-1 replay is regex/substring over committed text and adds O(milliseconds) per fixture; the existing fast-CI ethos is preserved.

    Tier-2 (workstation capture via `kanon transcripts capture`) and Tier-3 (paid nightly e2e against a live LLM) are **not** authorised by this carve-out and require their own ADRs if/when proposed.

<!-- INV-verification-contract-exit-zero-scope -->
11. **Exit-zero scope boundary.** `kanon verify` exit-0 means: the consumer repo conforms to the structural and behavioural contracts expressed in the discipline aspects the consumer has explicitly enabled, at the depths the consumer has declared. It MUST NOT be interpreted as — and the substrate MUST NOT represent it as — (a) a signal that the consumer's repository follows good engineering practices beyond what the enabled aspects define; (b) a correctness or quality endorsement of any prose, protocol, or code in the consumer's tree; (c) a guarantee that the consumer's declared agent will comply with the enabled protocols at runtime — exit-0 is a static structural check, not a runtime behavioural guarantee; (d) confirmation that resolution-replay invocations are semantically correct realizations of their contracts (resolutions are checked for *structural* coherence per [`docs/specs/resolutions.md`](resolutions.md), not for semantic correctness; the agent's choice of invocation is the resolution publisher's responsibility, not the substrate's).

    Aspects from any namespace (`kanon-`, `project-`, `acme-`) are verified identically; no publisher receives a warranty exemption (per `P-publisher-symmetry`). The substrate enforces structural coherence relative to the consumer's chosen aspects; correctness of those aspects' prose is each publisher's responsibility.

    This INV is the verification-contract anchor for the protocol-substrate's published commitments. It records what the substrate's exit code claims and — equally importantly — what it does NOT claim. Authored under [ADR-0039](../decisions/0039-contract-resolution-model.md); future ADRs (0042 verification scope-of-exit-zero) may extend the public-facing claim wording without weakening this structural anchor.

## Rationale

Consumer-facing `verify` is the most visible CLI for users. It must be fast (read-only static check), reliable (no stochasticity), and tier-aware (not complain about missing specs in tier-1 projects).

The check set is the intersection of what Sensei's `sensei verify`, `check_foundations`, and `check_links` deliver. New checks (fidelity-lock, invariant-ids) are deferred to v0.2+ per the roadmap.

## Out of Scope

- Running the consumer's pytest suite (not the kit's job).
- Running any LLM model against fixtures (model-version compatibility is a warning-level signal, not a re-run trigger — see ADR-0005).
- Linting the consumer's Python code.

## Decisions

See ADR-0005 (model-version compatibility), ADR-0008 (tier-aware checks), ADR-0029 (fidelity-fixture replay carve-out from INV-9), [ADR-0039](../decisions/0039-contract-resolution-model.md) (resolution-replay structural conformance and INV-11 exit-zero scope boundary), [ADR-0042](../decisions/0042-verification-scope-of-exit-zero.md) (canonical public claim wording for INV-11; immutable across substrate releases).
