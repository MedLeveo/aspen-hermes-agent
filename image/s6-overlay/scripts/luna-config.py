#!/opt/hermes/.venv/bin/python
"""Ensure this agent's config keys in a home that already has a config.

The seed only reaches a home that has none: cont-init copies config.yaml when
absent, and plow-init's own edit is deliberately narrow -- "it writes the
settings it owns and touches nothing else", which is model and provider. So a
key added to the seed after an agent's first boot never arrives, and the change
looks applied in git and is absent in production. That is how a job header
stayed on a message for a whole afternoon after being switched off.

This writes only the keys named below, leaves every other key alone, and is
idempotent: the home's config stays the agent's, because the chat plugin
rewrites its own parts of it on every connect.

Runs as the agent's uid, never as root: root writing here would take ownership
of a file the plugin has to keep writing, and on a host where root is not
privileged it could not write it at all.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

CONFIG = Path(os.environ.get("HERMES_HOME", "/var/lib/hermes")) / "config.yaml"

# Path -> value. Each is a decision this repo owns about how the agent behaves
# for the person reading it, none of them something the agent or Plow sets.
OWNED: dict[tuple[str, ...], object] = {
    # Cron output is wrapped with the job's name and id and a footer saying the
    # agent cannot see the message. Here the scheduled delivery IS the product.
    ("cron", "wrap_response"): False,
    # "Gateway shutting down" on every deploy reads as the thing breaking to
    # someone who is not an operator.
    ("platforms", "plow_chat", "gateway_restart_notification"): False,
    # First-run tips explain /stop and /busy queue to someone sending a text.
    ("onboarding", "seen", "busy_input_prompt"): True,
    ("onboarding", "seen", "tool_progress_prompt"): True,
}


def main() -> int:
    if not CONFIG.is_file():
        # A home with no config is one cont-init just seeded from ours, which
        # already carries these.
        print(f"[luna] no {CONFIG} yet -- the seed carries these keys")
        return 0

    try:
        config = yaml.safe_load(CONFIG.read_text()) or {}
    except (yaml.YAMLError, OSError) as exc:
        print(f"[luna] cannot read {CONFIG}: {exc}", file=sys.stderr)
        return 0

    changed = []
    for path, value in OWNED.items():
        section = config
        for key in path[:-1]:
            nxt = section.get(key)
            if not isinstance(nxt, dict):
                nxt = {}
                section[key] = nxt
            section = nxt
        if section.get(path[-1]) != value:
            section[path[-1]] = value
            changed.append(".".join(path))

    if not changed:
        print("[luna] config already carries this agent's keys")
        return 0

    # Written beside and renamed: a boot interrupted mid-write would otherwise
    # leave a half-config that the next boot keeps, because cont-init only
    # seeds an absent one.
    tmp = CONFIG.with_suffix(".yaml.incoming")
    try:
        tmp.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True))
        tmp.replace(CONFIG)
    except OSError as exc:
        print(f"[luna] cannot write {CONFIG}: {exc}", file=sys.stderr)
        return 0

    print(f"[luna] set {', '.join(changed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
