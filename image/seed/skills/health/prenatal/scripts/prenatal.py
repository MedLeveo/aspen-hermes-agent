#!/usr/bin/env python3
"""Gestational age, the schedule, what she has had, and what she is carrying.

Dates are arithmetic, not judgement: the model must never compute a week in its
head. Every number the agent states about timing comes from here.

State lives under HERMES_HOME -- the agent's own volume -- so it survives a
container replacement and does not depend on the owner's Mac being awake. The
path is read from the environment rather than baked in: the image that runs
this decides where its home is, and a hard-coded one silently wrote to a
directory nothing else looked at.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", "/var/lib/hermes"))
STATE = HOME / "luna" / "profile.json"
GESTATION_DAYS = 280  # Naegele: LMP + 40 weeks

# Routine low-risk care plus the logistics that have deadlines. The
# obstetrician's own plan always wins, so the agent presents the clinical ones
# as "usually this week", never as orders.
#
# `key` is what `mark-done` records, so it has to stay stable: renaming one
# would orphan a record of something she actually did and start raising it
# again.
#
# `kind` separates the two halves. "clinical" is her doctor's territory and the
# agent only reminds. "logistics" is nobody's territory, which is exactly why it
# gets missed -- and it is where an agent is unambiguously allowed to help.
MILESTONES: list[dict] = [
    {"key": "first_visit", "start": 6, "end": 8, "kind": "clinical",
     "what": "First prenatal visit and baseline labs"},
    {"key": "nt_scan", "start": 11, "end": 14, "kind": "clinical",
     "what": "First-trimester ultrasound with nuchal translucency"},
    {"key": "anatomy_scan", "start": 20, "end": 24, "kind": "clinical",
     "what": "Anatomy (morphology) ultrasound"},
    {"key": "tdap", "start": 20, "end": 36, "kind": "clinical",
     "what": "Tdap vaccine"},
    {"key": "glucose", "start": 24, "end": 28, "kind": "clinical",
     "what": "Glucose tolerance test"},
    {"key": "leave_notice", "start": 28, "end": 32, "kind": "logistics",
     "what": "Tell your employer your leave dates — in the US, FMLA notice is "
             "usually due 30 days before leave starts, and short-term disability "
             "has its own forms"},
    {"key": "repeat_labs", "start": 28, "end": 30, "kind": "clinical",
     "what": "Repeat baseline labs"},
    {"key": "pediatrician", "start": 30, "end": 36, "kind": "logistics",
     "what": "Choose a pediatrician — most want to meet you before the birth"},
    {"key": "preadmission", "start": 32, "end": 36, "kind": "logistics",
     "what": "Hospital pre-registration and the birth plan conversation"},
    {"key": "gbs", "start": 35, "end": 37, "kind": "clinical",
     "what": "Group B strep swab"},
    {"key": "insurance_add", "start": 39, "end": 42, "kind": "logistics",
     "what": "Adding the baby to your insurance — in the US that window is "
             "usually 30 days from the birth, and missing it is expensive"},
]
KEYS = {m["key"] for m in MILESTONES}
NOTE_KINDS = ("question", "symptom")


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
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
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


def week_on(data: dict, when: date) -> int | None:
    lmp = data.get("lmp")
    return (when - parse_day(lmp)).days // 7 if lmp else None


def open_notes(data: dict) -> list[dict]:
    """Notes taken since the last visit — what she is still carrying."""
    since = data.get("visits", {}).get("last")
    return [n for n in data.get("notes", [])
            if not n.get("resolved") and (since is None or n["on"] > since)]


def status(today: date) -> dict:
    data = load()
    lmp_text = data.get("lmp")
    if not lmp_text:
        return {"has_lmp": False,
                "ask": "how many weeks she is, or the first day of her last period"}

    lmp = parse_day(lmp_text)
    elapsed = (today - lmp).days
    if elapsed < 0:
        raise SystemExit(f"LMP {lmp} is in the future relative to {today}")

    week, day = divmod(elapsed, 7)
    edd = lmp + timedelta(days=GESTATION_DAYS)
    done = data.get("done", {})
    visits = data.get("visits", {})
    notes = open_notes(data)

    def shape(m: dict, **extra) -> dict:
        return {"key": m["key"], "what": m["what"], "kind": m["kind"],
                "weeks": f"{m['start']}-{m['end']}", **extra}

    out = {
        "has_lmp": True,
        "today": today.isoformat(),
        "lmp": lmp.isoformat(),
        "edd": edd.isoformat(),
        "week": week,
        "day": day,
        "display": f"{week}w{day}d",
        "days_to_edd": (edd - today).days,
        "weeks_to_edd": max((edd - today).days, 0) // 7,
        "trimester": 1 if week < 14 else 2 if week < 28 else 3,
        "visit_cadence": visit_cadence(week),
        "postpartum": week > 42,
        # Only what she has NOT done. Raising something she already did is the
        # fastest way to teach her the reminders are not worth reading.
        "due_now": [shape(m) for m in MILESTONES
                    if m["start"] <= week <= m["end"] and m["key"] not in done],
        "overdue": [shape(m, weeks_late=week - m["end"]) for m in MILESTONES
                    if week > m["end"] and m["key"] not in done],
        "upcoming": [shape(m, weeks_away=m["start"] - week) for m in MILESTONES
                     if m["start"] > week and m["key"] not in done][:3],
        "done": done,
        "open_questions": sum(1 for n in notes if n["kind"] == "question"),
        "open_symptoms": sum(1 for n in notes if n["kind"] == "symptom"),
    }
    if nxt := visits.get("next"):
        out["next_visit"] = nxt
        out["days_to_visit"] = (parse_day(nxt) - today).days
    if last := visits.get("last"):
        out["last_visit"] = last
    if name := data.get("name"):
        out["name"] = name
    return out


def visit_brief(today: date) -> dict:
    """Everything she should walk into the appointment holding."""
    data = load()
    st = status(today)
    if not st.get("has_lmp"):
        return st

    visits = data.get("visits", {})
    when = parse_day(visits["next"]) if visits.get("next") else today
    w = week_on(data, when)
    notes = open_notes(data)

    return {
        "visit_on": when.isoformat(),
        "days_away": (when - today).days,
        "week_at_visit": f"{w}w" if w is not None else None,
        "likely_this_visit": [m["what"] for m in MILESTONES
                              if w is not None and m["start"] <= w <= m["end"]
                              and m["key"] not in data.get("done", {})
                              and m["kind"] == "clinical"],
        "questions": [n["text"] for n in notes if n["kind"] == "question"],
        "symptoms": [{"on": n["on"], "week": n.get("week"), "text": n["text"]}
                     for n in notes if n["kind"] == "symptom"],
        "since": visits.get("last"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_set = sub.add_parser("set-lmp", help="record the first day of the last period")
    p_set.add_argument("date")
    p_set.add_argument("--name", default=None)

    p_week = sub.add_parser("set-week", help="record gestational age from weeks")
    p_week.add_argument("weeks", type=int)
    p_week.add_argument("days", type=int, nargs="?", default=0)

    p_done = sub.add_parser("mark-done", help="record a milestone she has had")
    p_done.add_argument("key", choices=sorted(KEYS))
    p_done.add_argument("--on", default=None)

    p_undo = sub.add_parser("mark-pending", help="undo a mark-done")
    p_undo.add_argument("key", choices=sorted(KEYS))

    p_note = sub.add_parser("note", help="something to raise at the next visit")
    p_note.add_argument("kind", choices=NOTE_KINDS)
    p_note.add_argument("text")

    p_visit = sub.add_parser("set-visit", help="when her next appointment is")
    p_visit.add_argument("date")

    p_vdone = sub.add_parser("visit-done", help="the visit happened; clear what she carried")
    p_vdone.add_argument("--on", default=None)

    p_rem = sub.add_parser("remember", help="save one fact about her")
    p_rem.add_argument("key")
    p_rem.add_argument("value")

    p_status = sub.add_parser("status", help="week, dates, what is due, what is open")
    p_status.add_argument("--today", default=None)

    p_brief = sub.add_parser("visit-brief", help="what to walk into the appointment with")
    p_brief.add_argument("--today", default=None)

    sub.add_parser("schedule")
    sub.add_parser("profile")

    args = ap.parse_args()
    today = parse_day(args.today) if getattr(args, "today", None) else date.today()

    if args.cmd == "set-lmp":
        lmp = parse_day(args.date)
        if lmp > today:
            raise SystemExit("that date is in the future -- ask again")
        if (today - lmp).days > 300:
            raise SystemExit("more than 300 days ago -- confirm before recording")
        data = load()
        data["lmp"] = lmp.isoformat()
        if args.name:
            data["name"] = args.name
        save(data)

    elif args.cmd == "set-week":
        # Most people know their week -- the obstetrician did this arithmetic
        # for them -- and not the date their last period started.
        if not 0 <= args.days <= 6:
            raise SystemExit("days must be 0-6")
        if not 1 <= args.weeks <= 42:
            raise SystemExit("weeks must be 1-42 -- confirm before recording")
        data = load()
        data["lmp"] = (today - timedelta(days=args.weeks * 7 + args.days)).isoformat()
        data["lmp_source"] = "derived from stated gestational age"
        save(data)

    elif args.cmd == "mark-done":
        data = load()
        data.setdefault("done", {})[args.key] = (
            parse_day(args.on).isoformat() if args.on else today.isoformat())
        save(data)

    elif args.cmd == "mark-pending":
        data = load()
        if data.get("done", {}).pop(args.key, None) is None:
            raise SystemExit(f"{args.key} was not marked done")
        save(data)

    elif args.cmd == "note":
        text = args.text.strip()
        if not text:
            raise SystemExit("empty note -- nothing to carry")
        data = load()
        data.setdefault("notes", []).append({
            "kind": args.kind, "text": text,
            "on": today.isoformat(), "week": week_on(data, today)})
        save(data)
        print(json.dumps({"noted": args.kind,
                          "open": len(open_notes(data))}, indent=2, ensure_ascii=False))
        return 0

    elif args.cmd == "set-visit":
        when = parse_day(args.date)
        if when < today:
            raise SystemExit("that date has passed -- record it with visit-done instead")
        data = load()
        data.setdefault("visits", {})["next"] = when.isoformat()
        save(data)

    elif args.cmd == "visit-done":
        # Closing the visit is what makes the brief mean "since we last saw the
        # doctor" rather than "everything, forever".
        data = load()
        when = parse_day(args.on) if args.on else today
        visits = data.setdefault("visits", {})
        visits["last"] = when.isoformat()
        visits.pop("next", None)
        save(data)

    elif args.cmd == "remember":
        if not args.value.strip():
            raise SystemExit("empty value -- nothing to remember")
        data = load()
        data.setdefault("about", {})[args.key] = args.value
        save(data)
        print(json.dumps(data.get("about", {}), indent=2, ensure_ascii=False))
        return 0

    elif args.cmd == "profile":
        data = load()
        print(json.dumps({"about": data.get("about", {}), "done": data.get("done", {}),
                          "visits": data.get("visits", {}),
                          "open_notes": len(open_notes(data)),
                          "has_lmp": bool(data.get("lmp"))}, indent=2, ensure_ascii=False))
        return 0

    elif args.cmd == "schedule":
        print(json.dumps(MILESTONES, indent=2, ensure_ascii=False))
        return 0

    elif args.cmd == "visit-brief":
        print(json.dumps(visit_brief(today), indent=2, ensure_ascii=False))
        return 0

    print(json.dumps(status(today), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
