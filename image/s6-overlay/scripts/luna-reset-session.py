#!/opt/hermes/.venv/bin/python
"""Drop the chat's session binding, so the next message starts a fresh one.

The system prompt -- SOUL.md included -- is built when a session is created and
not re-read afterwards. So an edit to the agent's identity reaches every future
conversation and none of the current one: the thread carries on with the
persona it was born with, and the change looks like it did nothing.

`/reset` in the chat cannot do this here. The Plow Chat plugin prefixes each
inbound turn with the chat's roster before the person's own text, so a leading
slash is no longer leading and the gateway's reset trigger never matches.

Runs at boot, before the gateway starts, which is the only moment the routing
table is not being written. Off unless LUNA_RESET_SESSION is set: a session
carries the conversation, and dropping one on every boot would make the agent
forget the person every time it was redeployed.

Only the routing row is removed. The session and its transcript stay in the
store -- this is "start a new conversation", not "erase the old one".
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", "/var/lib/hermes"))
STATE_DB = HOME / "state.db"
MIRROR = HOME / "sessions" / "sessions.json"

TRUTHY = {"1", "true", "yes", "on"}


def main() -> int:
    if os.environ.get("LUNA_RESET_SESSION", "").strip().lower() not in TRUTHY:
        return 0

    if not STATE_DB.is_file():
        print("[luna] no session store yet -- nothing to reset")
        return 0

    try:
        db = sqlite3.connect(STATE_DB)
        rows = db.execute("SELECT count(*) FROM gateway_routing").fetchone()[0]
        db.execute("DELETE FROM gateway_routing")
        db.commit()
        db.close()
    except sqlite3.Error as exc:
        # Never fatal: an agent that cannot reset its session is still an agent
        # that answers messages.
        print(f"[luna] could not reset the session binding: {exc}", file=sys.stderr)
        return 0

    # The legacy mirror the gateway also writes; left behind it would be read
    # back as the binding that was just dropped.
    try:
        MIRROR.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        print(f"[luna] left {MIRROR} in place: {exc}", file=sys.stderr)

    print(f"[luna] LUNA_RESET_SESSION set -- dropped {rows} routing row(s); "
          "the next message starts a new session")
    return 0


if __name__ == "__main__":
    sys.exit(main())
