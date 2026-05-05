# E2E Agent Tests

Live LLM-in-the-loop tests that verify kanon's SDD gates cause correct agent behavior.

## What these test

| Depth | Expected Agent Behavior |
|-------|------------------------|
| 0 | Agent writes code directly — no ceremony |
| 1 | Agent writes `docs/plans/*.md` before source code |
| 2 | Agent writes `docs/specs/*.md` before planning |
| 3 | Agent writes `docs/design/*.md` before spec |

## Running

```bash
# Individual tests
./tests/e2e_agent/test_d0_no_gates_freedom.sh
./tests/e2e_agent/test_d1_plan_fire_new_function.sh
./tests/e2e_agent/test_d1_plan_skip_typo.sh
./tests/e2e_agent/test_d1_plan_skip_approved.sh
./tests/e2e_agent/test_d2_spec_fire_new_capability.sh
./tests/e2e_agent/test_d2_spec_skip_refactor.sh
./tests/e2e_agent/test_d2_foundations_skip_populated.sh
./tests/e2e_agent/test_d3_design_fire_new_boundaries.sh
./tests/e2e_agent/test_d3_design_skip_existing_pattern.sh

# Run all
for f in tests/e2e_agent/test_d*.sh; do echo "--- $f ---"; "$f"; done
```

## Naming Convention

```
test_d{depth}_{gate}_{fire|skip}_{context}.sh
```

- `d{N}` — SDD depth level (0–3)
- `{gate}` — which gate is being tested (plan, spec, design, foundations, no_gates)
- `{fire|skip}` — whether the gate should fire (require artifact) or be skipped
- `{context}` — what makes this scenario unique

## Requirements

- `kiro-cli` installed and on PATH
- `kanon` installed and on PATH
- Active Midway session (`mwinit -s`)

## Design

These are **canary tests**, not CI gates. They verify that the current LLM model
respects kanon's AGENTS.md instructions at each depth level.

- **Non-deterministic**: LLMs may take different paths. Tests use coarse assertions
  (file existence, not exact content).
- **Expensive**: Each depth costs ~$0.05-0.50 in API tokens.
- **Slow**: ~1-5 minutes per depth.
- **Attribution ambiguous**: A failure may be kanon's AGENTS.md being unclear OR
  the LLM ignoring clear instructions. Human review of the transcript is needed.

## When to run

- After changing AGENTS.md hard-gates section
- After changing protocol frontmatter (gate declarations)
- After upgrading the LLM model
- Weekly as a regression canary
