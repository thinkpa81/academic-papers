#!/usr/bin/env python3
"""Create or verify release-file SHA-256/SHA-512 digests without editing evidence.

Run only after all release files are final. This adds SHA-512 to distribution
integrity checks; historical SHA-256 provenance and service schemas stay intact.
The two root manifest files are excluded to avoid circular self-digests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXCLUDED_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
MANIFEST_NAMES = {"manifest_sha256.json", "manifest_sha256_sha512.json"}


def eligible_files(root: Path):
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if len(relative.parts) == 1 and path.name in MANIFEST_NAMES:
            continue
        if path.is_symlink():
            raise ValueError(f"Symlink is not a release file: {relative.as_posix()}")
        if path.is_file() and path.suffix != ".pyc":
            yield path, relative.as_posix()


def file_record(path: Path, relative: str):
    digests = {name: hashlib.new(name) for name in ("sha256", "sha512")}
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            size += len(block)
            for digest in digests.values():
                digest.update(block)
    return {"path": relative, "bytes": size,
            **{name: digest.hexdigest() for name, digest in digests.items()}}


def write_manifests(root: Path, legacy: bool = False):
    records = [file_record(path, relative) for path, relative in eligible_files(root)]
    document = {
        "schema_version": 1,
        "purpose": "Release file integrity; not source authenticity or evidence timing",
        "algorithms": ["sha256", "sha512"],
        "excluded_root_files": sorted(MANIFEST_NAMES),
        "excluded_path_components": sorted(EXCLUDED_PARTS),
        "excluded_suffixes": [".pyc"],
        "files": records,
    }
    (root / "manifest_sha256_sha512.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if legacy:
        rows = [{k: row[k] for k in ("path", "bytes", "sha256")} for row in records]
        (root / "manifest_sha256.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(records)


def verify(root: Path):
    document = json.loads((root / "manifest_sha256_sha512.json").read_text(encoding="utf-8"))
    rows = document["files"]
    if document.get("algorithms") != ["sha256", "sha512"] or not isinstance(rows, list):
        raise ValueError("Invalid dual-hash manifest")
    seen, errors = set(), []
    for row in rows:
        relative = row["path"]
        path = (root / relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(root) or path == root:
            errors.append(f"Unsafe path: {relative}")
            continue
        if relative in seen:
            errors.append(f"Duplicate path: {relative}")
            continue
        seen.add(relative)
        if not path.is_file():
            errors.append(f"Missing file: {relative}")
            continue
        actual = file_record(path, relative)
        for key in ("bytes", "sha256", "sha512"):
            if row.get(key) != actual[key]:
                errors.append(f"{key} mismatch: {relative}")
    current = {relative for _, relative in eligible_files(root)}
    for relative in sorted(current - seen):
        errors.append(f"Unlisted file: {relative}")
    return len(rows), errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--legacy-sha256", action="store_true",
                        help="Also regenerate the backwards-compatible root SHA-256 manifest")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if args.verify and args.legacy_sha256:
        parser.error("--verify and --legacy-sha256 cannot be combined")
    try:
        if args.verify:
            count, errors = verify(root)
            if errors:
                parser.exit(1, "\n".join(errors) + "\n")
            print(f"PASS: {count} files verified with SHA-256 and SHA-512")
        else:
            count = write_manifests(root, legacy=args.legacy_sha256)
            print(f"WROTE: {count} release-file records with SHA-256 and SHA-512")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Manifest error: {exc}\n")


if __name__ == "__main__":
    main()
