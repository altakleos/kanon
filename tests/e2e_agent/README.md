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
./tests/e2e_agent/test_hardgate_sdd_d0_codes_without_ceremony.sh
./tests/e2e_agent/test_hardgate_sdd_d1_plans_before_coding.sh
./tests/e2e_agent/test_hardgate_sdd_d1_skips_plan_for_typo.sh
./tests/e2e_agent/test_hardgate_sdd_d1_builds_from_existing_plan.sh
./tests/e2e_agent/test_hardgate_sdd_d2_specs_before_planning.sh
./tests/e2e_agent/test_hardgate_sdd_d2_skips_spec_for_refactor.sh
./tests/e2e_agent/test_protocol_sdd_d2_respects_existing_vision.sh
./tests/e2e_agent/test_hardgate_sdd_d3_designs_before_planning.sh
./tests/e2e_agent/test_hardgate_sdd_d3_skips_design_for_pattern.sh

# Run all
for f in tests/e2e_agent/test_*.sh; do echo "--- $f ---"; "$f"; done
```

## Naming Convention

```
test_{type}_{aspect}_d{N}_{agent_does_what}.sh
```

| Segment | Values | Purpose |
|---------|--------|---------|
| `type` | `hardgate`, `protocol`, `workflow`, `regression` | What mechanism is being tested |
| `aspect` | `sdd`, `worktrees`, `testing`, `security`, `deps` | Which kanon aspect |
| `d{N}` | `d0`–`d3` | Depth level (omit if depth-agnostic) |
| `agent_does_what` | Behavioral verb phrase | What the agent does — reads as "the agent..." |

Rules:
1. Behavioral suffix reads as a sentence: "the agent plans_before_coding"
2. Skip scenarios use `skips_{what}_for_{reason}`
3. `type` enables filtering: `grep hardgate` vs `grep protocol`
4. Depth prefix enables filtering: `grep d2`

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
