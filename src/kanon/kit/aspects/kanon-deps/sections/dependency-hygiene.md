## Dependency Hygiene

LLM agents add dependencies casually. Every dependency change follows these rules:

**Always pin exact versions.** Use `==` in requirements.txt, exact versions in pyproject.toml, and exact versions (no `^` or `~`) in package.json. Unpinned dependencies break reproducibility.

**Never add a dependency without justification.** Before adding a package, check whether the standard library or an existing dependency already covers the need. Duplicate-purpose libraries bloat the dependency tree and create maintenance burden.

**Audit before adding.** Verify the package is actively maintained, has a compatible license, and is not a typosquat. Prefer well-known packages over obscure alternatives.

**Remove unused dependencies.** When removing code that was the sole consumer of a dependency, remove the dependency too. Phantom dependencies are tech debt.

**Keep manifests consistent.** If the project uses multiple manifest formats (e.g., pyproject.toml and requirements.txt), keep them in sync. Conflicting version constraints across manifests cause silent failures.

**At depth 2: CI dependency scanner.** `ci/check_deps.py` detects unpinned versions and duplicate-purpose packages. It is a safety net — passing the scanner does not mean the dependency tree is optimal.
