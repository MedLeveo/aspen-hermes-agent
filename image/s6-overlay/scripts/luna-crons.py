#!/opt/hermes/.venv/bin/python
"""Register this agent's scheduled jobs, idempotently, at container boot.

There is no cron-sync in the Plow agent contract, and nothing outside the
container to run one: `docker compose up` is the whole of starting an agent. So
the convergence runs from the image, as an s6 oneshot after plow-init and
before the gateway -- the jobs land in the home's cron store, which the gateway
reads when it comes up.

Creation only, like agent-mgr's v1: a job whose name is already registered is
left alone, whatever state it is in. Nothing here edits or deletes, so a job
the owner paused stays paused rather than being silently resurrected on the
next deploy.

Never fatal. A container that cannot register a cron is still a container that
answers messages, and refusing to boot over it would trade a missing reminder
for a dead agent.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERMES = "/opt/hermes/bin/hermes"
JOBS = Path(os.environ.get("HERMES_HOME", "/var/lib/hermes")) / "cron" / "jobs.json"
SPEC = Path("/opt/hermes/plow-seed/crons.json")

# Only delivery identifiers may be interpolated -- the same restriction
# agent-mgr's spec loader enforces, so a spec cannot smuggle a secret into a
# job's arguments.
PLACEHOLDER = re.compile(r"\$\{([A-Z0-9_]+)\}")


def registered_names() -> set[str]:
    if not JOBS.is_file():
        return set()
    try:
        data = json.loads(JOBS.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        # Unreadable is not empty: treating it as empty would re-create every
        # job on every boot and duplicate them.
        raise SystemExit(f"[cron] cannot read {JOBS}: {exc}")
    return {j.get("name") for j in data.get("jobs", []) if j.get("name")}


def expand(value: str) -> str:
    def sub(m: re.Match[str]) -> str:
        name = m.group(1)
        if not (name.endswith("_UID") or name.endswith("_CHANNEL")):
            raise SystemExit(f"[cron] refusing to expand {name}: not a delivery identifier")
        got = os.environ.get(name, "")
        if not got:
            raise SystemExit(f"[cron] {name} is unset -- cannot address delivery")
        return got

    return PLACEHOLDER.sub(sub, value)


def argv_for(row: dict) -> list[str]:
    argv = [HERMES, "cron", "create", row["schedule"]]
    if row.get("prompt"):
        argv.append(row["prompt"])
    argv += ["--name", row["name"], "--deliver", expand(row["deliver"])]
    for skill in row.get("skills", []):
        argv += ["--skill", skill]
    if row.get("script"):
        argv += ["--script", row["script"]]
    if row.get("no_agent"):
        argv.append("--no-agent")
    return argv


# A job that exists only to prove the scheduler is alive, on a schedule the
# host picks. The real job is deliberately quiet -- SOUL.md tells it to skip a
# morning with nothing to say -- so its silence cannot distinguish "nothing to
# report" from "the gateway is not running the scheduler at all". That
# ambiguity cost two days of waiting a whole night per test.
#
# Unset in the image, so nothing ships to anyone cloning this. Set
# LUNA_TEST_CRON to a cron expression on the host, watch the messages arrive,
# then unset it.
def test_row(deliver: str) -> dict | None:
    schedule = os.environ.get("LUNA_TEST_CRON", "").strip()
    if not schedule:
        return None
    return {
        "name": "luna-scheduler-probe",
        "schedule": schedule,
        "deliver": deliver,
        "skills": ["prenatal"],
        "prompt": (
            "This is a scheduled probe, not a message to the owner's day. "
            "Run the prenatal skill's status script and reply with exactly one "
            "line: the current time, the gestational week the script reports "
            "(or 'no week recorded'), and the words 'scheduler alive'. Always "
            "send it -- silence here is indistinguishable from a dead "
            "scheduler, which is the whole reason this job exists."
        ),
    }


def main() -> int:
    if not SPEC.is_file():
        print(f"[cron] no {SPEC} -- this agent ships no jobs")
        return 0

    rows = json.loads(SPEC.read_text())
    probe = test_row(rows[0]["deliver"] if rows else "${PLOW_HOME_CHANNEL}")
    if probe:
        print(f"[cron] LUNA_TEST_CRON is set -- adding {probe['name']} ({probe['schedule']})")
        rows = rows + [probe]
    have = registered_names()

    for row in rows:
        name = row["name"]
        if name in have:
            print(f"[cron] {name} already registered")
            continue
        result = subprocess.run(argv_for(row), capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[cron] created {name} ({row['schedule']})")
        else:
            print(f"[cron] FAILED to create {name}: "
                  f"{(result.stderr or result.stdout).strip()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 -- boot must not die over a cron
        print(f"[cron] skipped: {exc}", file=sys.stderr)
        sys.exit(0)
