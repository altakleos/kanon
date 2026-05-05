# `acme-test-aspects` synthetic publisher overlay

Used by [`tests/scripts/test_publisher_symmetry.py`](../../scripts/test_publisher_symmetry.py) per plan [`retire-kit-aspects-yaml`](../../../docs/plans/active/retire-kit-aspects-yaml.md) **T9 + AC7**.

Mirrors the shape any real third-party `acme-<vendor>-aspects` distribution would ship per ADR-0040 (Python entry-points group `kanon.aspects` + per-aspect `manifest.yaml` canonical per ADR-0055). The overlay's purpose is to point `scripts/check_kit_consistency.py` at a non-`kanon-` namespace and confirm every gate check produces zero errors — i.e., the gate's algorithm is publisher-blind.

If a future contributor accidentally hardcodes `kanon-` (or `kanon-aspects`'s package path) in a gate code path, this overlay turns the corresponding CI step red. That is the load-bearing falsification surface the panel R2 unanimous vote demanded for `P-publisher-symmetry §Implications`.

## Maintenance

If the substrate's dialect-grammar evolves (per ADR-0041), the synthetic manifest may need a parallel update. The overlay's intentional minimalism (one aspect, no files, no protocols) keeps that maintenance surface small.

If you change this fixture, run:

```bash
pytest tests/scripts/test_publisher_symmetry.py
```

to confirm the overlay still satisfies the gate's structural invariants.
