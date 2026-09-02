#!/usr/bin/env python3
"""Build the one-tap WhatsApp link that hands the conversation back to her.

The agent finds the clinic and drafts the message; she sends it. That split is
deliberate. Messaging a clinic as her would mean a bot negotiating an
appointment with a stranger who does not know it is a bot, over a channel the
Plow line cannot even reach in most of the world. A link she taps costs her one
tap and leaves her the author of her own appointment.

URL-encoding is here rather than in the prompt because a model that gets it
subtly wrong produces a link that opens WhatsApp with a mangled message, and
nobody notices until she has already sent it.
"""
from __future__ import annotations

import argparse
import re
import sys
from urllib.parse import quote


def digits(phone: str) -> str:
    n = re.sub(r"\D", "", phone)
    if not n:
        raise SystemExit(f"no digits in {phone!r}")
    # wa.me needs the country code and nothing else. A local number without one
    # silently resolves to whatever country the viewer is in.
    if len(n) < 10:
        raise SystemExit(
            f"{phone!r} looks like a local number ({len(n)} digits) -- wa.me needs "
            "the country code, so find it before building the link")
    if len(n) > 15:
        raise SystemExit(f"{phone!r} has {len(n)} digits -- E.164 allows at most 15")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phone", help="the clinic's number, with country code")
    ap.add_argument("message", help="the message she will send, already in her language")
    args = ap.parse_args()

    text = args.message.strip()
    if not text:
        raise SystemExit("empty message -- she should not send a blank one")
    if len(text) > 800:
        raise SystemExit("too long for a first contact; say less")

    print(f"https://wa.me/{digits(args.phone)}?text={quote(text)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
