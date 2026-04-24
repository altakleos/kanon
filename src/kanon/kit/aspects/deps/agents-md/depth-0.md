The `deps` aspect is enabled at depth 0 (opt-out). No dependency hygiene guidance or automation is active. To enable dependency discipline, raise the depth:

```bash
kanon aspect set-depth . deps 1
```
