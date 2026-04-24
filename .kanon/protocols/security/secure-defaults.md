---
status: accepted
date: 2026-04-24
depth-min: 1
invoke-when: Writing or modifying code that handles secrets, user input, network requests, file operations, or authentication
---
# Protocol: Secure defaults

## Purpose

Ensure LLM-agent-authored code follows hardened security defaults. Agents invoke this protocol whenever they write or modify code that touches secrets, user input, network requests, file operations, or authentication.

## Steps

### 1. Secrets

- Confirm no API keys, tokens, passwords, or credentials are hardcoded in source.
- Use environment variables or a secret manager for all sensitive values.
- Check for high-entropy strings that look like accidentally committed secrets.

### 2. Injection

- Use parameterized queries for all SQL, shell, and LDAP operations.
- Never use string interpolation or concatenation to build queries or commands.
- Use subprocess APIs with argument lists, not shell=True with interpolated strings.

### 3. Transport

- Verify TLS is not disabled (`verify=False`, `rejectUnauthorized: false`, `NODE_TLS_REJECT_UNAUTHORIZED=0`).
- Use HTTPS for all external requests.
- Do not downgrade transport security for convenience.

### 4. Permissions

- File permissions default to owner-only (0o644 for files, 0o755 for directories).
- Never use 0o777 or `chmod 777`.
- Apply least-privilege to IAM roles, database users, and API scopes.

### 5. Defaults

- CORS must specify allowed origins explicitly in production — no `Access-Control-Allow-Origin: *`.
- Debug modes, verbose logging of secrets, and development-only flags must not ship to production.

### 6. Input validation

- Validate type, length, and format of all external input before use.
- Reject unexpected values rather than coercing them.
- Sanitize output to prevent XSS when rendering user-supplied content.

## Exit criteria

- No hardcoded secrets in the changeset.
- All queries and commands use parameterized APIs.
- TLS verification is not disabled.
- File permissions follow least-privilege.
- CORS is not wildcarded in production code.
- External input is validated before use.

## Anti-patterns

- **"It's just a dev key."** Dev keys leak to production. Treat all secrets the same.
- **`verify=False` with a TODO.** TODOs don't fix themselves. Fix the certificate now.
- **`chmod 777` to make it work.** Diagnose the permission error instead.
- **String-interpolated SQL "because it's an internal tool."** Internal tools get compromised too.
