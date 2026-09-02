#!/usr/bin/env python3
"""Build the one-tap link that hands the appointment back to her.

The agent finds the clinic and drafts the message; she sends it. That split is
deliberate. Messaging a clinic as her would mean a bot negotiating with someone
who does not know it is a bot, and the Plow line cannot reach a clinic's number
in most of the world anyway. A link she taps costs her one tap and leaves her
the author of her own appointment.

`sms:` is the default because this agent already lives in Messages: she taps,
Messages opens with the text written, and she sends it from the same app she is
reading this in. No new app, no account, nothing to learn.

URL-encoding is here rather than in the prompt because a model that gets it
subtly wrong produces a link that opens with a mangled message, and nobody
notices until she has already sent it.
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
    if len(n) < 10:
        raise SystemExit(
            f"{phone!r} looks like a local number ({len(n)} digits) -- these links "
            "need the country code, so find it before building one")
    if len(n) > 15:
        raise SystemExit(f"{phone!r} has {len(n)} digits -- E.164 allows at most 15")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phone", help="the clinic's number, with country code")
    ap.add_argument("message", nargs="?", default="",
                    help="the message she will send, already in her language")
    ap.add_argument("--via", choices=("sms", "call", "whatsapp"), default="sms",
                    help="sms opens Messages with the text written (the default, and "
                         "the one that keeps her in the app she is already in); call "
                         "opens the dialler; whatsapp only where a clinic actually "
                         "answers there")
    args = ap.parse_args()

    n = digits(args.phone)
    text = args.message.strip()

    if args.via == "call":
        print(f"tel:+{n}")
        return 0

    if not text:
        raise SystemExit("a message link with no message just opens a blank thread")
    if len(text) > 800:
        raise SystemExit("too long for a first contact; say less")

    if args.via == "whatsapp":
        print(f"https://wa.me/{n}?text={quote(text)}")
        return 0

    # iOS wants `&` between the number and the body; Android wants `?`. She is
    # reading this in Messages on an iPhone, so `&` is the right one.
    print(f"sms:+{n}&body={quote(text)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
