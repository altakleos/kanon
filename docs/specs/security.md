---
status: accepted
design: "Follows ADR-0022"
date: 2026-04-24
realizes:
  - P-prose-is-code
  - P-tiers-insulate
stressed_by:
  - solo-with-agents
  - platform-team
fixtures:
  - tests/test_cli.py
  - tests/test_kit_integrity.py
  - tests/ci/test_check_security_patterns.py
invariant_coverage:
  INV-security-depth-range:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_kit_integrity.py::test_security_manifest_has_expected_depths
  INV-security-protocol:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_cli.py::test_aspect_add_security
  INV-security-agents-md-section:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
  INV-security-ci-validator:
    - tests/test_cli.py::test_security_depth_2_has_ci_script
    - tests/ci/test_check_security_patterns.py::test_sql_interpolation_detected
  INV-security-no-dependency:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_kit_integrity.py::test_security_manifest_paths_resolve
  INV-security-language-agnostic:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/ci/test_check_security_patterns.py::test_clean_file_no_findings
  INV-security-non-destructive:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_cli.py::test_aspect_remove_leaves_files
  INV-security-stability:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_kit_integrity.py::test_kit_security_aspect_dir_exists
---
# Spec: Security — hardened defaults for LLM-agent-authored code

## Intent

Package the discipline of writing secure code by default as an opt-in aspect. LLM agents produce predictable security anti-patterns: hardcoded secrets, string-interpolated queries, permissive CORS, disabled TLS verification, and overly broad file permissions. A single pushed secret is irreversible — it's in git history forever. This aspect ships prose procedures that make agents security-aware contributors before they write their first line of code.

The aspect is language-agnostic at all depths. The protocols describe *what* to avoid and *why*, not framework-specific APIs.

## Invariants

<!-- INV-security-depth-range -->
1. **Depth range is 0–2.** The `security` aspect declares `depth-range: [0, 2]`.
   - **Depth 0** — opt-out. Aspect enabled in config but no files scaffolded.
   - **Depth 1** — prose guidance. Protocol and AGENTS.md section scaffolded. Agents understand secure-by-default patterns and apply them when writing code.
   - **Depth 2** — prose guidance plus automation. CI validator scaffolded for common security anti-pattern detection.

<!-- INV-security-protocol -->
2. **Security-defaults protocol.** The aspect ships one protocol at `.kanon/protocols/kanon-security/secure-defaults.md` (depth ≥ 1) covering:
   - **Secrets:** Never hardcode secrets, API keys, tokens, or passwords in source. Use environment variables or secret managers. Never commit `.env` files. Add sensitive file patterns to `.gitignore`.
   - **Injection:** Always use parameterized queries for SQL. Never use string interpolation for shell commands. Validate and sanitize all external input.
   - **Transport:** Never disable TLS verification (`verify=False`, `rejectUnauthorized: false`). Never use `http://` for production endpoints.
   - **Permissions:** Use least-privilege file permissions. Never `chmod 777`. Never bind to `0.0.0.0` without explicit justification.
   - **Defaults:** Never use wildcard CORS (`*`) in non-development code. Never disable CSRF protection. Never use default/empty passwords.
   - Frontmatter `invoke-when`: writing or modifying code that handles secrets, user input, network requests, file operations, or authentication.

<!-- INV-security-agents-md-section -->
3. **AGENTS.md section.** At depth ≥ 1, the aspect contributes one marker-delimited section `security/secure-defaults` to AGENTS.md — a short prose summary of the core rules so an operating agent sees the security baseline on the boot chain.

<!-- INV-security-ci-validator -->
4. **CI validator (depth 2).** The aspect scaffolds `ci/check_security_patterns.py` — a language-agnostic pattern scanner that detects:
   - High-entropy strings in source that look like secrets (API keys, tokens, passwords).
   - SQL string concatenation or interpolation patterns.
   - Disabled TLS verification patterns (`verify=False`, `rejectUnauthorized`, `NODE_TLS_REJECT_UNAUTHORIZED`).
   - Overly permissive file modes (`0o777`, `chmod 777`).
   - Wildcard CORS patterns (`Access-Control-Allow-Origin: *`, `cors: { origin: '*' }`).
   The script outputs a JSON report with `{errors: [...], warnings: [...], status: "ok"|"fail"}` following the established CI script pattern. Detection is best-effort pattern-based — language-specific constructs may not be recognized.

<!-- INV-security-no-dependency -->
5. **No cross-aspect dependency.** `security` declares `requires: []`. Security discipline is independently useful without SDD, testing, or any other aspect. A project at sdd depth 0 (vibe-coding) still benefits from "never hardcode secrets."

<!-- INV-security-language-agnostic -->
6. **Language-agnostic at all depths.** Protocols describe security principles, not framework-specific APIs. The CI validator uses generic regex patterns that work across common languages. No language-specific config templates are scaffolded.

<!-- INV-security-non-destructive -->
7. **Non-destructive lifecycle.** Adding the security aspect does not modify existing files. Removing it leaves scaffolded files on disk. The CI validator is a copy-in template consumers adapt.

<!-- INV-security-stability -->
8. **Stability: experimental.** First release ships as experimental until self-hosted and validated.

## Rationale

**Why an aspect, not just AGENTS.md rules.** Security rules in a generic AGENTS.md are easy to ignore — they're mixed with unrelated guidance. A dedicated aspect with its own protocol and AGENTS.md section makes security a first-class concern with its own depth dial. Projects that don't need it opt out; projects that do get focused, auditable guidance.

**Why depth 0–2, not 0–3.** Security has two natural layers: knowledge (what to avoid) and detection (automated scanning). There's no meaningful third layer that isn't covered by dedicated SAST tools (Bandit, Semgrep, CodeQL) which are out of scope. The CI validator at depth 2 is a lightweight first line of defense, not a replacement for professional security tooling.

**Why no cross-aspect dependency.** Security is the one discipline that matters at every project maturity level. A vibe-coding prototype (sdd depth 0) still shouldn't push secrets to git. Gating security behind SDD would be counterproductive.

**Why best-effort pattern detection.** The CI validator uses regex patterns, not AST analysis. This means false positives (high-entropy strings that aren't secrets) and false negatives (secrets in unusual formats). This is acceptable — the validator is a safety net, not a guarantee. Professional SAST tools are out of scope.

## Out of Scope

- **SAST/DAST tooling integration.** Bandit, Semgrep, CodeQL, etc. are professional tools. The CI validator is a lightweight complement, not a replacement.
- **Threat modeling.** Too heavyweight for an aspect. Projects that need threat models should use dedicated frameworks.
- **Compliance frameworks.** SOC2, HIPAA, PCI-DSS are organizational concerns, not development disciplines packageable as prose.
- **Key management.** How to set up secret managers, rotate keys, or configure OIDC is infrastructure, not development discipline.
- **Runtime security.** WAFs, rate limiting, intrusion detection are operational concerns.
- **Cryptographic implementation.** The protocol says "use established libraries for crypto" but doesn't prescribe which ones.

## Decisions

See:
- **ADR-0022** — security aspect (secure-defaults protocol, CI validator, language-agnostic design).

ADR number is provisional until authored alongside this spec's promotion from `draft` to `accepted`.
