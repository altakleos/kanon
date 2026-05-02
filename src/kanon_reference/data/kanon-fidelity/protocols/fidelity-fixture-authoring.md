---
status: accepted
date: 2026-04-27
depth-min: 1
invoke-when: Adding a new fidelity fixture, updating an existing fixture's assertions, or recapturing a `.dogfood.md` after a protocol's prose has changed
---
# Protocol: Fidelity-fixture authoring

## Purpose

Author and maintain the YAML-frontmatter fixtures and `.dogfood.md` captures that the `kanon-fidelity` aspect's lexical-replay engine evaluates during `kanon verify`. The fixture-and-capture pair is the binding contract between a protocol's prose intent and an agent's actual behaviour.

## Steps

### 1. Choose the protocol you are verifying

Pick a kit-shipped or project-shipped protocol whose prose contains a *behavioural assertion* — something the agent must say, must not say, or must demonstrate. Example: `kanon-worktrees/worktree-lifecycle.md` mandates an audit sentence (`Working in worktree \`.worktrees/<slug>/\` on branch \`wt/<slug>\``) before any file-modifying tool call. That sentence is the fidelity contract.

### 2. Author the fixture

Create `.kanon/fidelity/<protocol-slug>.md` with this frontmatter shape:

```yaml
---
protocol: <protocol-slug>      # informational; matches the protocol filename
actor: <ACTOR>                  # turn-prefix label, e.g. AGENT or ASSISTANT
forbidden_phrases:              # optional; ANY match in the actor's text fails
  - "<python-regex>"
required_one_of:                # optional; AT LEAST ONE must match
  - "<python-regex>"
required_all_of:                # optional; EVERY regex must match somewhere
  - "<python-regex>"
---
# Fidelity fixture: <protocol-slug>

What this fixture asserts about agent behaviour, and why.
```

Worked example for `worktree-lifecycle`:

```yaml
---
protocol: worktree-lifecycle
actor: AGENT
forbidden_phrases:
  - "git worktree remove --force"
required_one_of:
  - "Working in worktree `\\.worktrees/[a-z0-9-]+/` on branch `wt/[a-z0-9-]+`"
---
# Fidelity fixture: worktree-lifecycle

Asserts that the agent emits the worktree audit sentence (with valid slug and
branch name) before its first file-modifying tool call, and never invokes
`git worktree remove --force` (per the kit's teardown rules).
```

Each entry under `forbidden_phrases`, `required_one_of`, and `required_all_of` is a Python regex passed to `re.search` against the actor's joined text. Use `\\` to escape backslashes inside YAML strings; YAML's double-quoted form is recommended for any regex containing metacharacters. The body of the fixture file is freeform markdown — explain *why* the assertions exist, so a future contributor can decide whether a failure is the agent's defect or the assertion's.

### 3. Capture the agent transcript

Create `.kanon/fidelity/<protocol-slug>.dogfood.md` containing a captured run where the agent was given a task that exercises the protocol. The capture file uses *named-actor turns*: each turn begins at column zero with `<ACTOR>:` followed by at least one space or tab. Example:

```
USER: Edit src/foo.py to fix the typo on line 42.

AGENT: Working in worktree `.worktrees/typo-fix/` on branch `wt/typo-fix`.
       I'll edit the file now.

USER: Looks good.

AGENT: Done. Tests pass.
```

A turn ends at the next turn marker line or end-of-file. The marker line is part of its turn. The fixture's `actor` selects which turns the assertions evaluate against — all `AGENT:` turns in the example above are joined with `\n` and matched as a single string.

Lines outside any turn (file headers, scene-setting prose, blank lines before the first turn) are ignored.

### 4. Run `kanon verify` and confirm

With the `kanon-fidelity` aspect enabled at depth ≥ 1, run `kanon verify .` from the consumer repo. The fixture is evaluated against the dogfood; pass means `status: ok`, fail means `errors:` listing each failed assertion with the regex that matched (forbidden) or did not match (required).

If the fixture passes on a known-good capture and fails on a deliberately-broken one, the contract is meaningful. If it passes both, the assertion is too loose. If it fails the known-good, the regex is wrong.

### 5. Commit the pair

Commit the fixture and the dogfood together. A fixture without a paired dogfood produces a warning from `kanon verify` but never an error — it's an in-flight signal, not a defect. A dogfood without a fixture is silently ignored (the engine discovers fixtures, not captures).

### 6. Recapture when the protocol changes

If you edit the protocol's prose in a way that changes the behaviour the agent should produce, the dogfood becomes stale. Recapture as part of the same change. The fixture's frontmatter usually does not need updating — the assertions encode the *contract*, which is more stable than the prose phrasing.

## Exit criteria

- `.kanon/fidelity/<protocol-slug>.md` exists with valid frontmatter (`protocol`, `actor` required; at least one of the three assertion families present).
- `.kanon/fidelity/<protocol-slug>.dogfood.md` exists and contains at least one turn matching `actor`.
- `kanon verify .` returns `status: ok` with no fidelity-related errors.
- The fixture has been deliberately broken once and confirmed to fail (proving the contract is non-trivial).

## Anti-patterns

- **Weakening the regex to make a failing assertion pass.** A failing assertion means the agent did the wrong thing. Fix the agent or fix the protocol prose; do not relax the contract silently.
- **Asserting on the user prompt instead of the agent turn.** The `actor:` field exists precisely to filter out user-side text. If your assertion would match the prompt, it is a vacuous test.
- **Copy-pasting another project's fixture verbatim.** Fixtures encode *your* protocol's behavioural contract. A fixture lifted from another project's repo asserts contracts you have not opted into.
- **Inline arithmetic or inline thresholds in regex.** Tunable values (timeouts, counts) belong in `.kanon/config.yaml`, not in fixture regex. Lexical assertions should encode *what* the agent must (or must not) say, not *how often*.
- **Tier-2 ambitions inside Tier-1.** Do not invoke an LLM, run a subprocess, or import consumer Python from a fidelity fixture's body or the dogfood capture. The carve-out (verification-contract INV-10) hard-bounds replay to text-only.
