# Luna — a pregnancy companion you text

Text it once a week and it knows exactly how far along you are. It cobra the
exams the schedule calls for, explains the ones you photograph, keeps the
questions you meant to ask at your next visit — and when you describe something
that should not wait, it does not reassure you. It tells you to go.

A [Hermes](https://github.com/NousResearch/hermes-agent) agent for
[Plow Chat](https://plow.co), deployed with
[`agent-mgr`](https://github.com/plow-pbc/agent-mgr).

## Why

An obstetrician sees you for fifteen minutes a month. The other twenty-nine days
you are alone with a search engine at 3am, and the lab result that arrived four
days before your appointment is a page of acronyms you cannot read.

Luna is not a second opinion. It is the continuity between visits: it holds the
week, it holds the calendar, it holds the paperwork, and it holds the list of
things you keep forgetting to ask. Everything clinical goes back to the doctor.

## What it does

- **Knows the week, always.** Tell it "I'm 22 weeks" — or when your last period
  started — and it never has to ask again. Every date it states is computed, not
  estimated.
- **Cobra the schedule.** Anatomy scan, glucose test, Tdap, group B strep: it
  knows which weeks each belongs to and raises them before they are late.
- **Messages first.** A daily job decides whether this morning is worth a
  message, and stays silent when it is not.
- **Reads what you photograph.** A request slip or a lab result, explained in
  plain language and filed where you can find it again.
- **Keeps the questions list.** Anything it cannot place confidently goes on the
  list for your next visit instead of being guessed at.
- **Answers in your language.** It replies in whatever language you write in.

## What it will not do

It does not diagnose, prescribe, adjust medication, or tell you a result is
normal. Asked something clinical, it has exactly three answers: *this is common
at this stage* (and mention it at your next visit), *I have added this to your
questions list*, or *this needs care now*. There is no fourth.

And one rule sits above every other, in [`runtime/SOUL.md`](runtime/SOUL.md):
bleeding, leaking fluid, severe pain, fever, reduced fetal movement, visual
changes, sudden swelling — it stops, and it says go. No reassurance, no
clarifying question first.

> Erring toward reassurance kills people. Erring toward "get it checked" costs
> someone an afternoon. Always choose the afternoon.

## Running it

You need [`agent-mgr`](https://github.com/plow-pbc/agent-mgr) on `PATH`, a
Docker daemon, an authenticated `gh` (`deploy` fetches the Plow Chat plugin
through it), a Mac running [Plow Latch](https://github.com/plow-pbc/latch), and
a [Gemini API key](https://aistudio.google.com/apikey).

```sh
git clone https://github.com/MedLeveo/aspen-hermes-agent.git ~/services/aspen-hermes-agent
agent-mgr register aspen ~/services/aspen-hermes-agent
agent-mgr deploy aspen
```

`deploy` builds the home and runs this repo's `deploy-hook`, which installs
`SOUL.md` and the `prenatal` skill into it. Then put your own credentials in the
dotenv it created — `agent-mgr resolve aspen` prints its path:

```sh
echo 'GEMINI_API_KEY=...'          >> ~/.hermes-aspen/.env
echo 'AGENT_TZ=America/Sao_Paulo'  >> ~/.hermes-aspen/.env
```

Then bring it up. `activate` prints a code to text from the phone that should
own the agent — **it is a one-time spend and the phone that answers becomes the
owner permanently**:

```sh
agent-mgr activate aspen
agent-mgr up aspen
agent-mgr cron-sync aspen
```

No `sign-in` step: the model is Gemini, which authenticates by API key from the
dotenv rather than by OAuth.

Finally, give it hands. In Plow Latch **on the Mac it should drive**, mint a
credential under *Agents → Connect MCP client → "Can't use OAuth? Create a
static credential"*, then:

```sh
agent-mgr set-latch aspen     # paste the whole JSON; input is hidden
agent-mgr restart aspen
agent-mgr check-latch aspen   # "latch reachable ... (HTTP 200)"
```

Text the number Plow replies with, and say hello.

## Running it somewhere that is not a Mac

`agent-mgr` builds the agent's home on the operator's machine, using `gh` to
fetch the Plow Chat plugin and the fleet skills. A cloud host has none of that
and its volume starts empty, so [`deploy/railway/`](deploy/railway) packages the
home as an image seed and unpacks it before the gateway starts.

That is how this agent actually runs: the container is on Railway, the Mac it
drives is still a Mac, and the two meet over the Plow relay. `Dockerfile` and
`00-agent-seed` carry the reasoning, including the two failures it took to get
there.

Rebuild the seed after changing anything it carries:

```sh
./deploy/railway/build-seed.sh
```

**Never run two gateways against one line.** The local container and the cloud
one share an activation, and two gateways answering one chat race the same
session database. Bring one down before the other comes up.

## Layout

| path | what it is |
|---|---|
| `runtime/SOUL.md` | who the agent is, and the rules it may not break |
| `runtime/crons.json` | the one scheduled job, as data |
| `skill/SKILL.md` | how to use the skill's script, and when |
| `skill/scripts/prenatal.py` | gestational age and the milestone table — the only source of truth for dates |
| `deploy-hook` | installs both into the agent's home on every deploy |
| `agent.env` | the descriptor: everything else is derived from the registered name |
| `deploy/railway/` | the same agent, packaged for a host without `agent-mgr` |
| `seed/` | the home, built by `build-seed.sh`; committed so the image can be built anywhere |

## The dates are code, not prompt

A model that estimates a due date will eventually estimate it wrong, and every
reminder after that is wrong with it. `prenatal.py` owns the arithmetic —
gestational age, Naegele's rule, which milestones the current week falls in —
and `SOUL.md` forbids doing it any other way. The script refuses a future date
and refuses one over 300 days old rather than recording a number that would be
wrong for the whole pregnancy.

## Not medical advice

Luna is a logistics and memory tool. It is not a medical device, it does not
practise medicine, and it does not replace prenatal care. The milestone weeks it
uses are routine low-risk guidance; the obstetrician's own plan always wins.
