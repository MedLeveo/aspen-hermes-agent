#!/usr/bin/env python3
"""Gestational age and the prenatal schedule -- the agent's only source of truth.

Dates are arithmetic, not judgement: the model must never compute a week in its
head. Every number the agent states about timing comes from here.

State lives in the agent's own home so it survives a container replacement and
does not depend on the owner's Mac being awake.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

STATE = Path("/opt/data/nina/profile.json")
GESTATION_DAYS = 280  # Naegele: LMP + 40 weeks

# (start_week, end_week, what). Ranges are inclusive and follow routine
# low-risk prenatal care; the obstetrician's own plan always wins, so the
# agent presents these as "usually this week", never as orders.
MILESTONES: list[tuple[int, int, str]] = [
    (6, 8, "First prenatal visit and baseline labs (blood count, blood type, glucose, infection screening, urine)"),
    (11, 14, "First-trimester ultrasound with nuchal translucency"),
    (20, 24, "Anatomy (morphology) ultrasound"),
    (20, 36, "Tdap vaccine"),
    (24, 28, "Glucose tolerance test"),
    (28, 30, "Repeat baseline labs"),
    (35, 37, "Group B strep swab"),
]


def load() -> dict:
    if not STATE.is_file():
        return {}
    try:
        return json.loads(STATE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save(data: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".json.incoming")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    tmp.replace(STATE)


def parse_day(text: str) -> date:
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise SystemExit(f"date must be YYYY-MM-DD, got {text!r}")


def visit_cadence(week: int) -> str:
    if week < 28:
        return "monthly"
    if week < 36:
        return "every two weeks"
    return "weekly"


def status(today: date) -> dict:
    data = load()
    lmp_text = data.get("lmp")
    if not lmp_text:
        return {"has_lmp": False, "ask": "first day of the last menstrual period (YYYY-MM-DD)"}

    lmp = parse_day(lmp_text)
    elapsed = (today - lmp).days
    if elapsed < 0:
        raise SystemExit(f"LMP {lmp} is in the future relative to {today}")

    week, day = divmod(elapsed, 7)
    edd = lmp + timedelta(days=GESTATION_DAYS)
    delivered = week > 42

    out = {
        "has_lmp": True,
        "today": today.isoformat(),
        "lmp": lmp.isoformat(),
        "edd": edd.isoformat(),
        "week": week,
        "day": day,
        "display": f"{week}w{day}d",
        "days_to_edd": (edd - today).days,
        "trimester": 1 if week < 14 else 2 if week < 28 else 3,
        "visit_cadence": visit_cadence(week),
        "postpartum": delivered,
        "due_now": [w for a, b, w in MILESTONES if a <= week <= b],
        "upcoming": [
            {"weeks": f"{a}-{b}", "what": w, "weeks_away": a - week}
            for a, b, w in MILESTONES
            if a > week
        ][:3],
    }
    if name := data.get("name"):
        out["name"] = name
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_set = sub.add_parser("set-lmp", help="record the first day of the last menstrual period")
    p_set.add_argument("date", help="YYYY-MM-DD")
    p_set.add_argument("--name", default=None)

    p_week = sub.add_parser(
        "set-week", help="record gestational age when she knows weeks, not her LMP")
    p_week.add_argument("weeks", type=int)
    p_week.add_argument("days", type=int, nargs="?", default=0)

    p_rem = sub.add_parser("remember", help="save one fact about her, learned in conversation")
    p_rem.add_argument("key")
    p_rem.add_argument("value")

    p_status = sub.add_parser("status", help="week, due date, what is due now")
    p_status.add_argument("--today", default=None, help="YYYY-MM-DD, for testing")

    sub.add_parser("schedule", help="the whole milestone table")
    sub.add_parser("profile", help="everything known about her so far")

    args = ap.parse_args()
    today = parse_day(args.today) if getattr(args, "today", None) else date.today()

    if args.cmd == "set-lmp":
        lmp = parse_day(args.date)
        if lmp > today:
            raise SystemExit("that date is in the future -- ask again")
        if (today - lmp).days > 300:
            raise SystemExit("that is more than 300 days ago -- confirm before recording")
        data = load()
        data["lmp"] = lmp.isoformat()
        if args.name:
            data["name"] = args.name
        save(data)
        print(json.dumps(status(today), indent=2))
        return 0

    if args.cmd == "set-week":
        # Most people know their week -- the obstetrician did this arithmetic
        # for them -- and not the date their last period started. Deriving the
        # LMP backwards means never having to ask for it.
        if not 0 <= args.days <= 6:
            raise SystemExit("days must be 0-6")
        if not 1 <= args.weeks <= 42:
            raise SystemExit("weeks must be 1-42 -- confirm before recording")
        data = load()
        data["lmp"] = (today - timedelta(days=args.weeks * 7 + args.days)).isoformat()
        data["lmp_source"] = "derived from stated gestational age"
        save(data)
        print(json.dumps(status(today), indent=2))
        return 0

    if args.cmd == "remember":
        if not args.value.strip():
            raise SystemExit("empty value -- nothing to remember")
        data = load()
        data.setdefault("about", {})[args.key] = args.value
        save(data)
        print(json.dumps(data.get("about", {}), indent=2))
        return 0

    if args.cmd == "profile":
        data = load()
        print(json.dumps({"about": data.get("about", {}),
                          "has_lmp": bool(data.get("lmp"))}, indent=2))
        return 0

    if args.cmd == "schedule":
        print(json.dumps(
            [{"weeks": f"{a}-{b}", "what": w} for a, b, w in MILESTONES], indent=2))
        return 0

    print(json.dumps(status(today), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
