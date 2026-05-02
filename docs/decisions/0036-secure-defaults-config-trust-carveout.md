---
status: accepted (lite)
date: 2026-04-30
weight: lite
---
# ADR-0036: Secure-defaults carve-out for same-repo config commands

## Decision

The kit-shipped `secure-defaults` protocol (`kanon-security/secure-defaults.md` § 2 "Injection") gains an explicit carve-out: `subprocess.run(cmd, shell=True, ...)` is acceptable when `cmd` is sourced from a config file inside the same git repository as the running CLI. The trust boundary for such a command is *write-access to that config file*. An attacker with write-access to the repo already owns the runtime; restricting the call site does not raise the bar.

`src/kanon/_preflight.py:96` is the first lived example: every preflight check the runtime executes comes from `.kanon/config.yaml` (consumer overrides) or from an aspect's `preflight:` manifest entries (kit-supplied). The call site carries a `# nosec` comment naming this ADR so a future reader can audit the rationale without re-deriving it.

## Why

Preflight commands include shell-only constructs that the runtime cannot legitimately reject:

- env-var expansion (the kit's own release-stage check uses `$TAG`),
- `&&` and `||` for sequencing,
- pipes (`|`) and redirection (`>`),
- subshells.

Refactoring `_preflight.py` to `subprocess.run(shlex.split(cmd), ...)` would silently break any consumer config relying on these features — an uncalibrated behavior break that fails the kit's compatibility contract. The protocol prose was overbroad; the safer move is to narrow the prose to its actual scope (untrusted-input injection) and document the trust boundary that already governs the existing call site.

The carve-out is two-token tight: (a) the command source must be a file *inside* the same repo as the running CLI, and (b) the trust boundary that legitimises it is repo write-access. Both clauses must hold. A command sourced from environment variables, network input, or a file outside the repo does *not* qualify.

## Alternative

Refactor `_preflight.py:96` to argv form via `shlex.split`. Rejected — silently breaks consumer configs that depend on shell features (env-var expansion, sequencing, pipes, redirection); no migration path; no warning surface.

## References

- [`src/kanon/_preflight.py:96`](../../src/kanon/_preflight.py) — first lived call site.
- [`src/kanon_reference/aspects/kanon_security/protocols/secure-defaults.md`](../../src/kanon_reference/aspects/kanon_security/protocols/secure-defaults.md) — protocol carrying the carve-out.
- [`docs/plans/preflight-shell-trust-boundary.md`](../plans/preflight-shell-trust-boundary.md) — implementing plan.
- [`docs/specs/preflight.md`](../specs/preflight.md) — preflight spec.
