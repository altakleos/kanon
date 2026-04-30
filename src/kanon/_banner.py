"""Kanon brand banner — single source of truth.

The banner appears at three surfaces (see docs/specs/kanon-banner.md):
  1. `kanon init` stderr (gated by TTY and --quiet)
  2. `kanon upgrade` stderr (gated by TTY and --quiet)
  3. Top of scaffolded AGENTS.md inside a kanon:begin:banner marker block

Both `cli.py` (runtime emission) and `_scaffold.py` (AGENTS.md substitution)
import _BANNER from here. This module is import-cycle-free by design.
"""
from __future__ import annotations

import sys


_BANNER = r"""
  _  __
 | |/ /__ _ _ __   ___  _ __
 | ' // _` | '_ \ / _ \| '_ \
 | . \ (_| | | | | (_) | | | |
 |_|\_\__,_|_| |_|\___/|_| |_|

"""


def _should_emit_banner(quiet: bool) -> bool:
    """Return True when the runtime banner should be emitted on stderr.

    Suppressed by --quiet OR when stderr is not a TTY (CI, pipes, redirected
    output). Both gates are honored independently.
    """
    return (not quiet) and sys.stderr.isatty()
