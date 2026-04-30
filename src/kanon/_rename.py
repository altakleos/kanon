"""Atomic slug rename across the cross-link graph.

Implements ``kanon graph rename`` per ``docs/specs/spec-graph-rename.md``.
The contract:

- Each rename targets one namespace at a time (``--type`` is required).
- The rewrite is computed first into a list of ``FileRewrite`` plans;
  the plans are then serialized to an ops-manifest at
  ``.kanon/graph-rename.ops`` before any file is touched (per ADR-0027).
- A ``.kanon/.pending`` sentinel labels the operation ``graph-rename``;
  the recovery path reads the manifest and completes a partial rename
  idempotently.
- Each rewrite is applied via :func:`kanon._atomic.atomic_write_text`,
  preserving per-file crash safety from ADR-0024.
- ``--dry-run`` emits the plan without writing anything.

Phase-3 of the spec-graph MVP plan ships namespace coverage incrementally
in this module. The current implementation covers the ``principle``
namespace end-to-end. Other namespaces raise a ``NotImplementedError``
at compute time; the CLI surface accepts all seven values per
spec-graph-rename INV-1 so the help text and error messages match the
final contract.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click

from kanon._atomic import atomic_write_text

_OP_GRAPH_RENAME = "graph-rename"
"""Sentinel label for an in-progress ``kanon graph rename`` op (rename-spec INV-7)."""

OPS_MANIFEST_FILENAME = "graph-rename.ops"
"""Per-operation manifest filename inside ``.kanon/`` (ADR-0027)."""

VALID_NAMESPACES: tuple[str, ...] = (
    "principle",
    "persona",
    "spec",
    "aspect",
    "capability",
    "inv-anchor",
    "adr",
)


_SLUG_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")
"""Slug grammar — first char alpha, then alphanumerics or hyphen."""


def _slug_boundary_pattern(slug: str) -> re.Pattern[str]:
    """Compile a regex matching *slug* only as a complete token.

    Uses negative lookbehind/lookahead over the slug-character class
    ``[A-Za-z0-9-]`` so a search for ``P-foo`` does NOT match inside
    ``P-foo-bar`` (which would be the wrong rename target). The slug is
    re-escaped with :func:`re.escape` to be safe even though our
    grammar restricts it to alphanumerics and hyphens.
    """
    return re.compile(rf"(?<![A-Za-z0-9-]){re.escape(slug)}(?![A-Za-z0-9-])")


# ---------------------------------------------------------------------------
# Dataclasses


@dataclass(frozen=True)
class FileRewrite:
    """One file's contribution to a rename op.

    ``src_path`` is where the file lives now. ``dst_path`` is where its
    content should land — usually the same as ``src_path``; differs only
    when the canonical file for the renamed slug is itself moving.
    ``delete_src`` is True iff ``src_path`` is to be removed after the
    write to ``dst_path`` succeeds (i.e., a true file-move).
    """

    src_path: Path
    dst_path: Path
    new_content: str
    delete_src: bool

    def is_move(self) -> bool:
        return self.src_path != self.dst_path


@dataclass(frozen=True)
class OpsManifest:
    """The persisted plan for one rename op (ADR-0027 schema).

    Serialized to ``.kanon/graph-rename.ops`` before any rewrite begins,
    deleted only after the post-rewrite CI self-check has cleared the
    sentinel.
    """

    old: str
    new: str
    type: str
    files: list[FileRewrite] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validation


def validate_namespace(namespace: str) -> None:
    """Raise ``ClickException`` with the seven-options error message
    when *namespace* is unrecognised (rename-spec INV-1)."""
    if namespace not in VALID_NAMESPACES:
        raise click.ClickException(
            f"Invalid --type {namespace!r}: must be one of "
            f"{list(VALID_NAMESPACES)}."
        )


def validate_slug(slug: str, label: str) -> None:
    if not isinstance(slug, str) or not _SLUG_RE.match(slug):
        raise click.ClickException(
            f"Invalid {label} slug {slug!r}: must match "
            r"`[A-Za-z][A-Za-z0-9-]*`."
        )


def _principle_path(repo_root: Path, slug: str) -> Path:
    return repo_root / "docs" / "foundations" / "principles" / f"{slug}.md"


def detect_collision(repo_root: Path, namespace: str, new_slug: str) -> Path | None:
    """Return the colliding artifact path when *new_slug* already exists in
    the target namespace, else ``None`` (rename-spec INV-10)."""
    if namespace == "principle":
        candidate = _principle_path(repo_root, new_slug)
        return candidate if candidate.is_file() else None
    return None  # other namespaces handled in subsequent commits


def _require_canonical_exists(repo_root: Path, namespace: str, old_slug: str) -> Path:
    if namespace == "principle":
        path = _principle_path(repo_root, old_slug)
        if not path.is_file():
            raise click.ClickException(
                f"Cannot rename: no principle file at {path.relative_to(repo_root)}."
            )
        return path
    raise NotImplementedError(
        f"--type {namespace!r} is declared in INV-1 but its rewrite engine "
        f"is not yet implemented in this build. Stay tuned."
    )


# ---------------------------------------------------------------------------
# Frontmatter / link-target token replacement


_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def _replace_in_frontmatter(text: str, slug_re: re.Pattern[str], new_slug: str) -> str:
    """Replace token-bounded matches of *slug_re* within the YAML frontmatter
    block at the start of *text* (if present); leaves body untouched.

    Frontmatter is matched line-anchored (``\\A---\\n...\\n---\\n``) — a
    file without a leading frontmatter block is returned unchanged.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return text
    fm_text = m.group(1)
    new_fm = slug_re.sub(new_slug, fm_text)
    if new_fm == fm_text:
        return text
    return text[: m.start(1)] + new_fm + text[m.end(1):]


def _replace_link_targets(text: str, namespace_dir: str, old: str, new: str) -> str:
    """Replace markdown link targets pointing at ``<...>/<namespace_dir>/<old>.md``.

    Matches both relative forms (``../<dir>/<old>.md``) and absolute-from-root
    forms (``docs/<dir>/<old>.md``) by scanning for the directory + filename
    pair regardless of leading path segments. An optional ``#anchor`` suffix
    is preserved.
    """
    pattern = re.compile(
        rf"\]\(([^)\s]*?{re.escape(namespace_dir)}/){re.escape(old)}\.md(#[^)\s]*)?\)"
    )
    return pattern.sub(rf"](\g<1>{new}.md\g<2>)", text)


# ---------------------------------------------------------------------------
# Per-namespace rewrite computation


def _principle_rewrites(
    repo_root: Path, old_slug: str, new_slug: str,
) -> list[FileRewrite]:
    """Compute the file rewrites for a ``principle`` rename.

    Touches:
      * the canonical principle file (move + frontmatter ``id:`` update);
      * any spec or persona whose frontmatter cites the slug as a token
        (``realizes:`` / ``stresses:`` lists, in practice);
      * any markdown file in ``docs/`` containing a markdown link whose
        target path resolves to ``<...>/principles/<old>.md``.

    Per the rename-spec § Match semantics, prose mentions are out of
    scope; the engine emits no rewrites for body mentions of the slug
    outside link targets.
    """
    canonical_src = _principle_path(repo_root, old_slug)
    canonical_dst = _principle_path(repo_root, new_slug)
    rewrites: list[FileRewrite] = []
    slug_re = _slug_boundary_pattern(old_slug)

    # Canonical file: rewrite frontmatter id and move to new path.
    try:
        canonical_text = canonical_src.read_text(encoding="utf-8")
    except OSError as exc:
        raise click.ClickException(
            f"Cannot read principle file {canonical_src}: {exc}"
        ) from None
    new_canonical_text = _replace_in_frontmatter(canonical_text, slug_re, new_slug)
    new_canonical_text = _replace_link_targets(
        new_canonical_text, "principles", old_slug, new_slug,
    )
    rewrites.append(FileRewrite(
        src_path=canonical_src,
        dst_path=canonical_dst,
        new_content=new_canonical_text,
        delete_src=True,
    ))

    # Inbound frontmatter scan: any spec or persona whose frontmatter
    # mentions the slug as a token gets a frontmatter rewrite.
    inbound_dirs = [
        repo_root / "docs" / "specs",
        repo_root / "docs" / "foundations" / "personas",
    ]
    for d in inbound_dirs:
        if not d.is_dir():
            continue
        for md in sorted(d.glob("*.md")):
            if md == canonical_src:
                continue
            rewrites_extend_with_frontmatter(rewrites, md, slug_re, new_slug)

    # Link-target scan: every markdown under docs/.
    docs_root = repo_root / "docs"
    if docs_root.is_dir():
        for md in sorted(docs_root.rglob("*.md")):
            if md == canonical_src:
                continue
            # Skip files we've already queued — their link rewrite happens
            # against their *post-frontmatter-update* content below.
            existing = next(
                (r for r in rewrites if r.src_path == md and r.dst_path == md),
                None,
            )
            base_text = (
                existing.new_content if existing is not None
                else md.read_text(encoding="utf-8")
            )
            updated_text = _replace_link_targets(
                base_text, "principles", old_slug, new_slug,
            )
            if updated_text == base_text:
                continue
            if existing is not None:
                rewrites.remove(existing)
            rewrites.append(FileRewrite(
                src_path=md, dst_path=md,
                new_content=updated_text, delete_src=False,
            ))

    return rewrites


def rewrites_extend_with_frontmatter(
    rewrites: list[FileRewrite],
    md: Path,
    slug_re: re.Pattern[str],
    new_slug: str,
) -> None:
    """Helper: append a frontmatter-rewrite for *md* to *rewrites* if the
    slug appears as a token in its frontmatter, else no-op."""
    try:
        text = md.read_text(encoding="utf-8")
    except OSError as exc:
        raise click.ClickException(f"Cannot read {md}: {exc}") from None
    new_text = _replace_in_frontmatter(text, slug_re, new_slug)
    if new_text == text:
        return
    rewrites.append(FileRewrite(
        src_path=md, dst_path=md,
        new_content=new_text, delete_src=False,
    ))


def compute_rewrites(
    repo_root: Path, namespace: str, old_slug: str, new_slug: str,
) -> list[FileRewrite]:
    if namespace == "principle":
        return _principle_rewrites(repo_root, old_slug, new_slug)
    raise NotImplementedError(
        f"Rewrite engine for namespace {namespace!r} is not yet "
        f"implemented in this build."
    )


# ---------------------------------------------------------------------------
# Ops-manifest serialization (ADR-0027 schema)


def manifest_path(repo_root: Path) -> Path:
    return repo_root / ".kanon" / OPS_MANIFEST_FILENAME


def write_ops_manifest(repo_root: Path, manifest: OpsManifest) -> None:
    """Serialize *manifest* to ``.kanon/graph-rename.ops`` atomically.

    Per ADR-0027 the rendered post-rewrite content is captured directly
    so recovery does not depend on re-deriving it from the (partially
    rewritten) source files.
    """
    payload = {
        "old": manifest.old,
        "new": manifest.new,
        "type": manifest.type,
        "files": [
            {
                "src": str(rw.src_path.relative_to(repo_root)),
                "dst": str(rw.dst_path.relative_to(repo_root)),
                "content": rw.new_content,
                "delete_src": rw.delete_src,
                "sha256": hashlib.sha256(rw.new_content.encode("utf-8")).hexdigest(),
            }
            for rw in manifest.files
        ],
    }
    target = manifest_path(repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(target, json.dumps(payload, indent=2) + "\n")


def read_ops_manifest(repo_root: Path) -> OpsManifest | None:
    target = manifest_path(repo_root)
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise click.ClickException(
            f"Cannot parse {target}: {exc}. Delete the file manually if "  # nosec
            f"you intended to abandon the in-flight rename."
        ) from None
    if not isinstance(data, dict):
        raise click.ClickException(f"{target}: ops-manifest is malformed.")
    files: list[FileRewrite] = []
    root = repo_root.resolve()
    for entry in data.get("files", []):
        src = repo_root / entry["src"]
        dst = repo_root / entry["dst"]
        if not src.resolve().is_relative_to(root) or not dst.resolve().is_relative_to(root):
            raise click.ClickException(
                f"Path traversal in ops-manifest: src={entry['src']!r}, "
                f"dst={entry['dst']!r} escapes repo root."
            )
        files.append(FileRewrite(
            src_path=src,
            dst_path=dst,
            new_content=entry["content"],
            delete_src=bool(entry.get("delete_src", False)),
        ))
    return OpsManifest(
        old=data["old"], new=data["new"], type=data["type"], files=files,
    )


def clear_ops_manifest(repo_root: Path) -> None:
    target = manifest_path(repo_root)
    if target.is_file():
        target.unlink()


# ---------------------------------------------------------------------------
# Atomic rewrite engine


def apply_rewrites(manifest: OpsManifest) -> None:
    """Execute every entry in *manifest* idempotently.

    Each ``dst_path`` is written via :func:`atomic_write_text`. After
    every write succeeds, files marked ``delete_src=True`` whose
    ``src_path`` differs from ``dst_path`` are removed. A re-run of this
    function over the same manifest produces no observable change beyond
    the eventual deletion of the obsolete source.
    """
    # Phase 1: write all dst files (idempotent — atomic_write_text overwrites).
    for rw in manifest.files:
        rw.dst_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(rw.dst_path, rw.new_content)
    # Phase 2: remove src for moves now that dst is on disk.
    for rw in manifest.files:
        if rw.delete_src and rw.is_move() and rw.src_path.exists():
            rw.src_path.unlink()


# ---------------------------------------------------------------------------
# Dry-run rendering


def format_dry_run(rewrites: list[FileRewrite], repo_root: Path) -> str:
    """Render a plain-text plan describing each rewrite — one line per
    file, naming the source path, the destination path (if different),
    and whether the source will be deleted.
    """
    lines: list[str] = []
    for rw in rewrites:
        rel_src = rw.src_path.relative_to(repo_root)
        if rw.is_move():
            rel_dst = rw.dst_path.relative_to(repo_root)
            lines.append(f"move:    {rel_src} -> {rel_dst}")
        else:
            lines.append(f"rewrite: {rel_src}")
    if not lines:
        lines.append("(no files would change)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Top-level entry — used by the CLI's `kanon graph rename` command and the
# crash-recovery path in `_check_pending_recovery`.


def perform_rename(
    repo_root: Path,
    namespace: str,
    old_slug: str,
    new_slug: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Plan, validate, and execute a rename.

    Returns a small report dict suitable for printing or test inspection.
    Side-effects: writes the ops-manifest + sentinel before rewrites,
    clears them after.
    """
    from kanon._atomic import clear_sentinel, write_sentinel  # local: avoids cycle

    validate_namespace(namespace)
    validate_slug(old_slug, "old")
    validate_slug(new_slug, "new")
    if old_slug == new_slug:
        raise click.ClickException(
            "Old slug and new slug are identical; nothing to rename."
        )

    _require_canonical_exists(repo_root, namespace, old_slug)
    collision = detect_collision(repo_root, namespace, new_slug)
    if collision is not None:
        raise click.ClickException(
            f"Collision: {collision.relative_to(repo_root)} already exists. "
            f"Resolve manually before retrying."
        )

    rewrites = compute_rewrites(repo_root, namespace, old_slug, new_slug)
    manifest = OpsManifest(
        old=old_slug, new=new_slug, type=namespace, files=rewrites,
    )

    if dry_run:
        return {
            "status": "dry-run",
            "plan": format_dry_run(rewrites, repo_root),
            "files": len(rewrites),
        }

    kanon_dir = repo_root / ".kanon"
    kanon_dir.mkdir(parents=True, exist_ok=True)

    write_ops_manifest(repo_root, manifest)
    write_sentinel(kanon_dir, _OP_GRAPH_RENAME)
    try:
        apply_rewrites(manifest)
    finally:
        # Clear sentinel + manifest only on success. On exception, sentinel
        # persists so the next run can recover.
        pass
    clear_ops_manifest(repo_root)
    clear_sentinel(kanon_dir)
    return {"status": "ok", "files": len(rewrites)}


def recover_pending_rename(repo_root: Path) -> bool:
    """Complete a partial rename whose ops-manifest is on disk.

    Returns ``True`` if a recovery was performed, ``False`` if no
    manifest was present (nothing to do). Intended for the CLI entry
    point's ``_check_pending_recovery`` integration — when the sentinel
    label is ``graph-rename``, call this to finish the work.
    """
    from kanon._atomic import clear_sentinel  # local: avoids cycle

    manifest = read_ops_manifest(repo_root)
    if manifest is None:
        return False
    apply_rewrites(manifest)
    clear_ops_manifest(repo_root)
    clear_sentinel(repo_root / ".kanon")
    return True
