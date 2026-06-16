#!/usr/bin/env python3
"""Rebrand the mothership codename across the whole repo (back / front / docs).

Replaces the old codename ``그물매`` / ``Geulmae`` (in every case + the combined
``그물매 (Geulmae)`` forms) with a new, sleek English codename — default
**Peregrine**. Operates on all tracked text files; binary assets are skipped.

    python tools/rename_codename.py                 # -> Peregrine
    python tools/rename_codename.py Gyrfalcon       # pick your own
"""

from __future__ import annotations

import subprocess
import sys

SKIP_EXT = {".xlsx", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mov",
            ".webm", ".stl", ".3mf", ".ico", ".woff", ".woff2", ".ttf", ".zip"}


def replacements(name: str):
    up, low = name.upper(), name.lower()
    # ordered: collapse the combined Korean+roman forms first so we never emit
    # "Peregrine (Peregrine)"
    return [
        ("그물매 (Geulmae)", name), ("그물매(Geulmae)", name),
        ("Geulmae (그물매)", name), ("Geulmae(그물매)", name),
        ("그물매", name),
        ("GEULMAE", up), ("Geulmae", name), ("geulmae", low),
    ]


def tracked_files():
    # -z keeps non-ASCII paths (e.g. Korean doc filenames) raw + unquoted
    out = subprocess.run(["git", "ls-files", "-z"], capture_output=True, text=True,
                         check=True).stdout
    return [f for f in out.split("\0") if f]


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "Peregrine"
    rules = replacements(name)
    me = "tools/rename_codename.py"
    changed = 0
    total = 0
    for path in tracked_files():
        if path == me or any(path.lower().endswith(e) for e in SKIP_EXT):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        new = text
        n = 0
        for old, rep in rules:
            c = new.count(old)
            if c:
                new = new.replace(old, rep)
                n += c
        if new != text:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
            print(f"  {path}: {n} replacement(s)")
            changed += 1
            total += n
    print(f"rebranded -> '{name}': {total} replacement(s) across {changed} file(s)")


if __name__ == "__main__":
    main()
