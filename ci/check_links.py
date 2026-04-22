"""Markdown link validator (maintainer-side, CI hard-fail).

Walks every `*.md` file under the supplied root and verifies that each
relative markdown link resolves to an existing file on disk. Catches the
class of drift where a file gets renamed or moved and forgotten
cross-references silently decay — e.g. a principle file carrying
`../../docs/specs/...` after the `docs/` segment was removed from the
path.

Scope:

- Scans ``[text](url)`` and ``![alt](url)`` inline markdown links.
- Skips external URLs (any `scheme://` prefix), mailto:, and same-file
  anchors (`#section`).
- Strips `#anchor` and `?query` before resolving the file part, so
  "file.md#heading" is valid iff "file.md" exists. Anchor validity
  itself is out of scope.
- Skips content inside fenced code blocks (```), which may contain
  illustrative paths that aren't real links.

Does NOT validate:

- Reference-style links `[text][label]`.
- Anchor existence inside the target file.
- External URLs (requires network and is flaky).

Exit codes:
    0 — every relative link resolves
    1 — one or more broken links detected

Prints a JSON report to stdout either way, matching the convention in
`ci/check_foundations.py` and `ci/check_package_contents.py`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_ROOT = _REPO_ROOT / "docs"

# ``[text](url)`` or ``![alt](url)``; capture group 1 is the URL.
# Non-greedy URL match stops at the first `)` — we accept the simplification
# that parenthesized paths are rare in documentation links.
_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

# Any URL that starts with `scheme:` (http://, https://, mailto:, file:, etc.)
# is treated as external and not validated.
_EXTERNAL_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+\-.]*:")


def _iter_markdown(root: Path) -> list[Path]:
    """Return all *.md files under *root*, sorted."""
    return sorted(root.rglob("*.md"))


def _strip_fragment(target: str) -> str:
    """Drop any `#anchor` or `?query` suffix; return the file part."""
    return target.split("#", 1)[0].split("?", 1)[0]


def _is_external(target: str) -> bool:
    return bool(_EXTERNAL_SCHEME.match(target))


def check_links(root: Path) -> list[str]:
    """Return a list of human-readable error messages for broken links."""
    errors: list[str] = []
    for md_path in _iter_markdown(root):
        text = md_path.read_text(encoding="utf-8")
        in_code_block = False
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            for match in _LINK_PATTERN.finditer(line):
                target = match.group(1).strip()
                if not target or target.startswith("#"):
                    continue
                if _is_external(target):
                    continue
                file_part = _strip_fragment(target)
                if not file_part:
                    continue
                resolved = (md_path.parent / file_part).resolve()
                if not resolved.exists():
                    # Prefer repo-root-relative paths for real runs; fall back
                    # to the supplied root (e.g. pytest's tmp_path) otherwise.
                    try:
                        rel_path = md_path.relative_to(_REPO_ROOT)
                    except ValueError:
                        rel_path = md_path.relative_to(root)
                    errors.append(
                        f"{rel_path}:{lineno}: broken link → {target} "
                        f"(resolved to {resolved})"
                    )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument(
        "--root",
        type=Path,
        default=_DEFAULT_ROOT,
        help=f"Directory to scan recursively for *.md files (default: {_DEFAULT_ROOT})",
    )
    args = parser.parse_args(argv)

    if not args.root.is_dir():
        print(json.dumps({"status": "fail", "error": f"root not found: {args.root}"}))
        return 1

    errors = check_links(args.root)
    report: dict[str, Any] = {"root": str(args.root), "errors": errors}
    if errors:
        report["status"] = "fail"
        print(json.dumps(report, indent=2))
        return 1

    report["status"] = "ok"
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
