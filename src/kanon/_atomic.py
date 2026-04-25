"""Atomic file-write helper for irreplaceable state.

Uses write-to-temp + fsync + rename(2) to guarantee that a crash or
interrupt cannot leave the target file truncated or half-written.
Ported from Sensei — see that project's `_atomic.py` for prior art.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path


def atomic_write_text(path: Path, content: str) -> None:
    """Write *content* to *path* atomically.

    Algorithm:
    1. Write to a sibling .tmp file (same directory → same filesystem).
    2. fsync the file descriptor so bytes reach storage before rename.
    3. os.replace() for an atomic POSIX rename(2); also safe on Windows.
    4. fsync the parent directory so the rename's dirent update is durable
       across power loss. Required on POSIX — the file fsync covers data
       but not the containing directory entry. No-op on non-POSIX.
    5. On any exception, remove the tmp file to avoid leaving debris.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(content)
            # Flush Python's buffer then sync to storage before we rename.
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        if os.name == "posix":
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    except Exception:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise


def write_sentinel(kanon_dir: Path, operation: str) -> None:
    """Write a crash-recovery sentinel before a multi-file mutation.

    The sentinel records the operation name so that if the process is
    interrupted, the next kanon invocation can detect and re-execute
    the incomplete operation.
    """
    sentinel = kanon_dir / ".pending"
    atomic_write_text(sentinel, operation + "\n")


def clear_sentinel(kanon_dir: Path) -> None:
    """Remove the crash-recovery sentinel after successful completion."""
    sentinel = kanon_dir / ".pending"
    with contextlib.suppress(FileNotFoundError):
        sentinel.unlink()


def read_sentinel(kanon_dir: Path) -> str | None:
    """Return the pending operation name, or None if no sentinel exists."""
    sentinel = kanon_dir / ".pending"
    try:
        return sentinel.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
