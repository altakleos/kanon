# Common dev targets
.PHONY: test lint typecheck e2e check

test:
	.venv/bin/pytest -x -q

lint:
	.venv/bin/ruff check kernel/ src/ tests/ scripts/

typecheck:
	.venv/bin/mypy kernel/

e2e:
	.venv/bin/pytest -m e2e -x -q

check: lint typecheck test
