---
status: done
shipped-in: PR #76
slug: sub-substrate-independence
date: 2026-05-02
design: docs/design/kernel-reference-interface.md
---

# Plan: Sub-plan — `scripts/check_substrate_independence.py` gate (per ADR-0044)

## Context

Per [ADR-0044 substrate-self-conformance](../../decisions/0044-substrate-self-conformance.md): `kanon-core` MUST run without `kanon-aspects`. This is the substrate's foundational invariant — it's how we prove kanon is a substrate, not a kit. The gate is publicly-readable; `acme-` publishers can replicate against their own bundles per ADR-0044's invariants.

**Today's reality:** `kanon-core` and `kanon-aspects` ship together as one `kanon-kit` wheel from the top-level pyproject. The packaging split (per ADR-0043) is documented but not built. So the substrate-independence gate can't yet verify a separately-installed `kanon-core` wheel.

**What this gate CAN verify:** the substrate's *runtime code* doesn't fail when `kanon_reference` isn't importable. We achieve this by:

1. Spawning a Python sub-process with `kanon_reference` masked (via `sys.modules['kanon_reference'] = None` shim).
2. Running a focused subset of substrate-internal logic that should not require `kanon_reference`:
   - `kanon._manifest._load_aspects_from_entry_points()` returns empty when no entry-points discovered
   - `kanon._manifest._load_aspect_registry()` works when target has no project-aspects and no entry-points
   - `kanon._verify` core paths (when no aspects enabled)
3. Asserting all paths exit cleanly with no `ModuleNotFoundError` for `kanon_reference`.

This is a **partial implementation** of ADR-0044's gate — full implementation requires the packaging split to be build-active (a future plan). Today's gate ships green and establishes the contract; future work expands the gate's scope.

## Scope

### In scope

#### A. `scripts/check_substrate_independence.py` (~120 LOC)

Sub-process invocation pattern: spawn `python -c "..."` with `kanon_reference` masked, run substrate-internal queries, exit 0 if all green.

```python
def main() -> int:
    test_script = '''
import sys
# Mask kanon_reference imports.
class _BlockKanonReference:
    def find_module(self, name, path=None):
        if name == "kanon_reference" or name.startswith("kanon_reference."):
            return self
        return None
    def load_module(self, name):
        raise ImportError(f"kanon_reference is masked")
sys.meta_path.insert(0, _BlockKanonReference())

# Substrate logic that must work without kanon_reference.
from kanon._manifest import _load_aspects_from_entry_points
import os
os.environ["KANON_TEST_OVERLAY_PATH"] = "/nonexistent/empty/overlay"
aspects = _load_aspects_from_entry_points()
assert aspects == {}, f"expected empty registry, got {sorted(aspects)}"
print("substrate-independence: OK")
'''
    result = subprocess.run([sys.executable, "-c", test_script], capture_output=True, text=True)
    print(json.dumps({
        "errors": [...],
        "warnings": [...],
        "status": "ok" | "fail",
    }, indent=2))
    return 0 if result.returncode == 0 else 1
```

#### B. `tests/scripts/test_check_substrate_independence.py` (~80 LOC, 4 cases)

- Real-repo passes
- Main exits zero on ok
- Subprocess captures masked-import correctly
- Failure mode: if substrate code attempted `import kanon_reference`, gate would fail (synthesised by monkeypatching the test script)

#### C. CHANGELOG entry under `[Unreleased] § Added`.

### Out of scope

- Building separate `kanon-core` wheel and installing in clean venv (future plan; requires packaging split to be build-active)
- Refactoring substrate code to avoid `kanon_reference` imports (none exist today; if any creep in later, this gate catches them)

## Acceptance criteria

- [x] AC-G1: `scripts/check_substrate_independence.py` exists, runnable, exits 0 with `status: ok` on clean substrate
- [x] AC-G2: Gate detects when substrate code attempts `import kanon_reference` (synthesised in test)
- [x] AC-T1: ≥4 tests passing
- [x] AC-X1..X8: standard gates green; full pytest no regression
