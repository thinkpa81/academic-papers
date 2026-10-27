#!/usr/bin/env python3
"""Verify the release manifest without modifying the package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def verify(root: Path) -> tuple[int, list[str]]:
    root = root.resolve()
    manifest = json.loads((root / "manifest_sha256.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, list):
        raise ValueError("Manifest must contain a list of file records")
    errors = []
    seen = set()
    for record in manifest:
        relative = record["path"]
        path = (root / relative).resolve()
        if (
            path == root
            or not path.is_relative_to(root)
            or Path(relative).is_absolute()
        ):
            errors.append(f"Unsafe manifest path: {relative}")
            continue
        if relative in seen:
            errors.append(f"Duplicate manifest path: {relative}")
            continue
        seen.add(relative)
        if not path.is_file():
            errors.append(f"Missing file: {relative}")
            continue
        if path.stat().st_size != record["bytes"]:
            errors.append(f"Size mismatch: {relative}")
            continue
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != record["sha256"]:
            errors.append(f"SHA-256 mismatch: {relative}")
    return len(manifest), errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    try:
        count, errors = verify(args.root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Invalid package manifest: {exc}\n")
    if errors:
        parser.exit(1, "\n".join(errors) + "\n")
    print(f"PASS: {count} files verified")


if __name__ == "__main__":
    main()
