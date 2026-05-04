# Common dev targets
.PHONY: test lint typecheck e2e check wheel-check

test:
	.venv/bin/pytest -x -q

lint:
	.venv/bin/ruff check packages/kanon-core/src/ packages/kanon-aspects/src/ tests/ scripts/

typecheck:
	.venv/bin/mypy packages/kanon-core/src/kanon_core/

e2e:
	.venv/bin/pytest -m e2e -x -q

check: lint typecheck test

# Pre-tag check: builds a fresh sdist+wheel via `python -m build`
# (the same pipeline release.yml runs on tag push) and validates the
# resulting wheel via scripts/check_package_contents.py. Closes the
# gap that produced v0.5.0a2 hotfix PRs #99 and #100.
wheel-check:
	.venv/bin/python scripts/check_wheel_build.py
