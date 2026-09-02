#!/usr/bin/env python3
"""File one exam photo or PDF into her record, under a name she could find.

The Plow Chat plugin drops an inbound attachment into Hermes' media cache and
hands the model the path. That cache is temporary; this copies it into the
record, which lives on the agent's own volume and therefore survives a
container replacement and does not need the owner's Mac to be awake.

Naming is done here rather than by the model so two exams filed a week apart
sort together and neither can overwrite the other.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

EXAMS = Path("/opt/data/nina/exams")
# Deliberately narrow: these are the things a person photographs of a medical
# record. Anything else is a mistake worth failing on rather than filing.
ALLOWED = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".pdf"}


def slug(text: str) -> str:
    """A filename fragment: lowercase, ASCII-ish, no separators of its own."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return text[:60] or "exame"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", help="the path the turn gave you for the attachment")
    ap.add_argument("label", help="what it is, in a few words: 'ultrassom morfologico'")
    ap.add_argument("--on", default=None,
                    help="YYYY-MM-DD the exam is dated, if the document says so")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.is_file():
        raise SystemExit(f"no file at {src} -- the attachment may have expired from the cache")

    ext = src.suffix.lower()
    if ext not in ALLOWED:
        raise SystemExit(f"{ext or 'no extension'} is not something to file here")

    if args.on:
        try:
            when = datetime.strptime(args.on, "%Y-%m-%d").date()
        except ValueError:
            raise SystemExit(f"--on must be YYYY-MM-DD, got {args.on!r}")
    else:
        when = date.today()

    EXAMS.mkdir(parents=True, exist_ok=True)
    stem = f"{when.isoformat()}-{slug(args.label)}"
    dest = EXAMS / f"{stem}{ext}"
    # Never overwrite: two scans of the same exam on the same day are two
    # documents, and losing one silently is worse than an ugly name.
    n = 2
    while dest.exists():
        dest = EXAMS / f"{stem}-{n}{ext}"
        n += 1

    shutil.copy2(src, dest)
    print(f"filed: {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
