---
name: prenatal
description: Gestational week, the prenatal milestone schedule, the questions list, and filing exam results. Use it for anything involving timing, dates, or what is due.
version: 1.0.0
---

# Prenatal

## Never do date arithmetic yourself

The week, the due date and what is due are computed, never estimated. Run:

```
python3 <this skill's dir>/scripts/prenatal.py status
```

It returns JSON: `week`, `day`, `display` (e.g. `24w3d`), `edd`, `trimester`,
`visit_cadence`, `due_now`, `upcoming`. Every timing claim you make comes from
that output. If `has_lmp` is false, you do not know the week — ask for the LMP
before saying anything about timing.

The install root differs by runtime, so resolve the script relative to this
skill's own directory. Never assume an absolute home.

## Recording how far along she is

**Prefer this one.** When she tells you her week — "I'm 22 weeks", "22 weeks and
3 days" — that is enough, and it is what most people know:

```
python3 <this skill's dir>/scripts/prenatal.py set-week 22 3
```

Only when she does not know her week do you ask when her last period started:

```
python3 <this skill's dir>/scripts/prenatal.py set-lmp YYYY-MM-DD
```

Both refuse impossible values rather than recording a number that would be wrong
for the whole pregnancy. If one refuses, ask again — never override it.

If she only knows the due date, subtract 280 days for the LMP and confirm the
resulting week with her before recording.

## What she has already had

`due_now` and `overdue` exclude anything recorded as done, so an exam she has
had is never cobrado again. When she says she has had one:

```
python3 <this skill's dir>/scripts/prenatal.py mark-done anatomy_scan
python3 <this skill's dir>/scripts/prenatal.py mark-done glucose --on 2026-08-20
```

Keys: `first_visit`, `nt_scan`, `anatomy_scan`, `tdap`, `glucose`,
`repeat_labs`, `gbs`. `mark-pending <key>` undoes one recorded by mistake.

If `overdue` lists something from early pregnancy that she almost certainly had,
ask once whether she had it rather than cobrando it as late -- then record the
answer either way.

## Remembering her

Anything you learn about her — her name, first pregnancy or not, her
obstetrician, where she plans to give birth, what worries her:

```
python3 <this skill's dir>/scripts/prenatal.py remember <key> "<value>"
python3 <this skill's dir>/scripts/prenatal.py profile
```

Check `profile` before asking anything personal. Asking twice for something she
already told you is worse than not asking at all.

## What `due_now` means

Routine low-risk care, not orders. Present it as "this is usually the week
for X — is it already scheduled?" The obstetrician's own plan always wins; if
they say their doctor asked for something different, follow the doctor and note
it.

`visit_cadence` is how often visits usually happen at this stage: monthly until
28 weeks, every two weeks until 36, then weekly.

## The questions list

Anything you cannot place confidently goes here — that is the honest default,
not a failure. Append to `/opt/data/nina/questions.md` with the date and the
week it came up. When a visit is near, send the list back unprompted and offer
to clear it afterwards.

## Filing an exam

When they send a photo or PDF of a lab result or a request slip:

1. Read it and say what it is in plain language, in their language.
2. Write it to `/opt/data/nina/exams/` named `YYYY-MM-DD-<what>.<ext>`.
3. Anything you cannot read confidently, or any value you cannot place, goes on
   the questions list. Do not call a result normal or abnormal.

Keeping it in the agent's own home rather than on the owner's Mac is
deliberate: the record has to be readable when the Mac is asleep.

## No account of hers, ever

Everything here works without her connecting anything: no OAuth, no portal
login, no app. She texts, and that is the whole interface she is asked to learn.
If a capability would need her to authorise an account, it does not belong in
this agent -- the person this serves is not going to complete a consent screen
at 3am, and an agent that asks her to is one she stops using.
