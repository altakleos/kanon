"""kanon-aspects — reference aspect bundles for the kanon protocol.

Source-tree relocated from `src/kanon_reference/` to
`packages/kanon-aspects/src/kanon_aspects/` per ADR-0054 §3 + §7.

The seven reference aspects ship as data + loaders, registered under the
`kanon.aspects` entry-point group (per ADR-0040). The substrate kernel
(`kanon-core`) discovers them at runtime via importlib.metadata.

Per ADR-0054 §6, kanon-aspects ships lock-stepped with kanon-core under a
single `kanon-kit` distribution to PyPI until ADR-0053's forcing function
fires. The version below mirrors `kanon_core.__version__`.
"""

__version__ = "0.5.0a3"
