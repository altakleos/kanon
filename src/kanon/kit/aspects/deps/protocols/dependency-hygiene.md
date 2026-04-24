---
status: accepted
date: 2026-04-24
depth-min: 1
invoke-when: Adding, removing, or updating project dependencies
---
# Protocol: Dependency hygiene

## Purpose

Ensure LLM-agent-driven dependency changes are deliberate, pinned, and minimal. Agents invoke this protocol whenever they add, remove, or update a dependency in any manifest file.

## Steps

### 1. Justify the addition

- Confirm the standard library or an existing dependency does not already provide the needed functionality.
- Check for duplicate-purpose packages (e.g., multiple HTTP clients, multiple date libraries).
- Document why this specific package was chosen over alternatives.

### 2. Pin the version

- Use exact version pins: `==` in requirements.txt, exact versions in pyproject.toml `dependencies`, no `^` or `~` in package.json.
- Never use open-ended ranges (`>=`, `>`, `*`).
- Record the pinned version in the commit message.

### 3. Audit the package

- Verify the package is actively maintained (recent commits, responsive maintainers).
- Check the license is compatible with the project.
- Confirm the package name is correct — watch for typosquats (e.g., `reqeusts` vs `requests`).
- Prefer packages with broad adoption over niche alternatives.

### 4. Clean up removals

- When removing code that was the sole consumer of a dependency, remove the dependency from all manifest files.
- Verify no other module imports the removed package.

### 5. Keep manifests consistent

- If the project has multiple manifest files, update all of them.
- Run the project's install/lock command to verify resolution succeeds.

## Exit criteria

- Every new dependency has an exact version pin.
- No duplicate-purpose packages added.
- Package name verified against typosquats.
- All manifest files updated consistently.
- Install/lock command succeeds.

## Anti-patterns

- **"Just add it, we'll pin later."** Unpinned dependencies break builds on the next install.
- **Adding `requests` when `httpx` is already in the tree.** Check existing deps first.
- **Leaving phantom deps after refactoring.** Dead dependencies are dead weight.
- **Pinning with `~=` or `^` and calling it "pinned."** Only exact versions are pins.
