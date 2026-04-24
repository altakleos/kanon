## Secure Defaults

LLM agents produce predictable security anti-patterns. Every code change follows these rules:

**Never hardcode secrets.** API keys, tokens, passwords, and credentials go in environment variables or a secret manager — never in source code. If a value looks like a secret, it is one.

**Always use parameterized queries.** Never string-interpolate SQL, shell commands, or LDAP queries. Use the language's parameterized query API or prepared statements.

**Never disable TLS verification.** No `verify=False`, no `rejectUnauthorized: false`, no `NODE_TLS_REJECT_UNAUTHORIZED=0`. If a certificate is invalid, fix the certificate — don't disable the check.

**Use least-privilege file permissions.** Never `chmod 777` or `0o777`. Files default to owner-only unless there is a documented reason for broader access.

**Never use wildcard CORS in production.** `Access-Control-Allow-Origin: *` is acceptable only in local development. Production CORS must specify allowed origins explicitly.

**Validate all external input.** User input, API responses, file contents, and environment variables are untrusted. Validate type, length, and format before use. Reject unexpected values rather than coercing them.

**At depth 2: CI pattern scanner.** `ci/check_security_patterns.py` detects common anti-patterns via regex. It is a safety net, not a SAST replacement — passing the scanner does not mean the code is secure.
