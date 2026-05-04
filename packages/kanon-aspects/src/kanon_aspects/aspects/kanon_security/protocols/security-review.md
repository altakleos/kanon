---
status: accepted
date: 2026-05-04
depth-min: 2
invoke-when: A spec or plan introduces a new external-facing endpoint, a new data store, a new authentication mechanism, or a new third-party integration
---
# Protocol: Security Review

## Purpose

Review architectural security implications of changes that introduce new attack surfaces, beyond the code-level checks in `secure-defaults` (depth 1).

## Steps

### 1. Identify the surface change

Name what is being introduced or modified:
- New network-reachable endpoint?
- New data store containing sensitive or user data?
- New or modified authentication/authorization mechanism?
- New third-party dependency with network or filesystem access?

If none apply, this protocol does not fire — return to the invoking workflow.

### 2. Enumerate data flows

For each new surface: what data crosses it, in which direction, and at what sensitivity level (public, internal, secret)?

### 3. Verify controls

- Every flow from a less-trusted to a more-trusted zone has authentication.
- Every flow carrying user-scoped data has authorization.
- Sensitive data in transit uses encryption (TLS or equivalent).
- New dependencies are from well-known, actively maintained sources.

### 4. Produce findings

List findings as: surface → flow → issue → severity (critical/high/medium). If no findings: "Security review passed — no new risks identified."

## Exit criteria

- Every new surface has been reviewed.
- Findings (if any) are documented and addressed or accepted as known risks.
