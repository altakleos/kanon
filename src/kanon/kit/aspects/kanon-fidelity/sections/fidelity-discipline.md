## Fidelity Discipline

The `kanon-fidelity` aspect verifies that an LLM agent's *actual behaviour* matches the prose your protocols promise. Lexical assertions over committed `.kanon/fidelity/<protocol>.dogfood.md` captures fail `kanon verify` when the agent's recorded turns drift from the fixture's `forbidden_phrases` / `required_one_of` / `required_all_of` rules.

**Commit fixtures before tagging.** A release tag stamps the protocol prose at a SHA; the paired dogfood capture must reflect agent behaviour at that SHA. Tagging with stale captures ships a hidden contract violation.

**Recapture when the protocol changes.** If you edit a protocol's prose, the previous dogfood capture no longer reflects what the agent should now do. Recapture as part of the same change; commit the new dogfood alongside the prose edit.

**Never weaken an assertion to make a fixture pass.** A failing fidelity assertion means the agent did the wrong thing. Fix the agent's prompt, fix the protocol prose, or accept that the rule does not actually hold — and remove the assertion deliberately, with a note. Silently relaxing the regex is the same anti-pattern as weakening a unit-test assertion.

**Failures are errors; missing dogfood is a warning.** If you have a fixture without its paired capture, you have in-flight work — `kanon verify` warns. If you have a capture that fails the assertions, you have a real defect — `kanon verify` errors and your CI breaks.

The aspect ships only Tier 1 (lexical replay over committed text). Tier 2 (workstation capture) and Tier 3 (paid live-LLM nightly) are out of scope at this depth and require their own ADRs.
