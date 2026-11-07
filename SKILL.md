---
name: signal-watch
description: Run a recurring signal watch on Zambo: save a baseline to memory under your own caller handle, check the signal against it on a schedule, apply a stated threshold rule, save every reading either way, and wrap a digest handover when the rule fires (and a quiet-day digest when it does not). Use when you watch prices, leads, mentions, or any signal that must be checked again tomorrow: a watch that recurs, remembers, and reports only on real movement. The memory and the record live on Zambo (endpoint https://zambo.dev/mcp); your own scheduler runs the passes.
---

# Signal watch on Zambo

You are a watcher: an agent that checks the same signal again and
again, on a schedule, and speaks only when something real moved. The
failure mode of watchers is not missing the move; it is crying wolf on
noise, forgetting yesterday's baseline, and leaving no record that the
quiet days were checked at all. This pattern fixes all three. The
baseline lives in memory under your own handle. The rule is stated in
the same fact, in plain words. Every reading is saved either way. And
every pass ends in a digest handover: an alert when the rule fires, a
quiet-day digest when it does not.

Zambo is where the watch's memory and record live, at
https://zambo.dev/mcp. It does not run your schedule: your cron, your
agent loop, or your operator's runner starts each pass. Zambo is where
the baseline, the readings, and the proof sit between passes.

This skill ships inside the zambo-watch package. Next to it you will
find `watch.py`, the runnable watcher (baseline mode and check mode),
a no-code paste for a chat agent, and RUN.md, the record of a real
watch run on the live endpoint with every receipt live.

## Step zero: your handle is your memory

On initialize, the endpoint issues a caller handle (in the initialize
result and the `X-Zambo-Caller-Handle` header). Save it in your own
state file before doing anything else, and present it as
`_caller_handle` on every call, with your agent name as
`_caller_label`. Your memory keys to that handle: the baseline you save
today is recallable tomorrow only under the same handle. Lose it and
you come back as a stranger with no baseline and a fresh allowance.
One handle per watch, never shared.

**Quota rule, in the placement that works:** Put `_caller_handle` inside the tool arguments on every call, as a field of the arguments object itself, not in `_meta` and not in a header. That argument placement is what meters your own daily bucket. Presenting a handle only at `_meta` level or in a header can route you onto a shared network bucket and wall you early.

## The pattern

One watch = one job id (a `_session_id` string you pick once and reuse
on every pass). Three moves, repeated:

1. Baseline (first pass only). Read the signal. Save ONE fact with
   `memory_remember`: the values, the source receipts, and the rule in
   plain words (for example: alert when any watched asset moves 3
   percent or more from its baseline). Keep the remember receipt; it
   is the anchor every later move is measured from.
2. Check (every later pass). `memory_recall` the baseline and read the
   values back out of the recalled fact. Read the signal again.
   Compute the move for each watched item and apply the rule exactly
   as stated: no rounding a 2.9 into a 3, no alerting on a hunch. Save
   the reading with `memory_remember` either way, alert or quiet.
3. Wrap the digest. `handover` with a summary, a goal, a recipient,
   and next steps. When the rule fires, the summary leads with the
   alert and the size of the move. When it does not, use the quiet
   format: the prices, the moves, and the words "no alert", so a
   reader can tell a checked quiet day from a day the watch never
   ran. Wrapping is the day's free wrap-up and leaves the call counter
   untouched.

A wrap needs its inputs: a `handover` call without a summary and a
recipient is refused, receipted. That refusal is a feature: a digest
is a deliverable being published, and it is held to that standard.

## The next pass: the return

A return pass on the three-signal shape in RUN.md costs 5 counted
calls and measures against the baseline saved under the same caller
handle. Every later pass measures against a baseline that is
already saved. Run each return pass the same way:

1. **Come back under the same handle.** The baseline lives in memory
   under your caller handle, and the free tier resets at 00:00 UTC:
   a new UTC day hands you 20 calls + 1 wrap-up free again. A
   different handle recalls nothing, so the watch would start over
   as a stranger with no baseline to measure against.
2. **Pick up the last digest free.** If the previous pass wrapped a
   digest handover, `handover_accept` on it is always free and
   spends none of today's calls. Its next steps name this pass: the
   assets, the rule, where the last reading stopped.
3. **Measure against the saved baseline, not a fresh one.** Recall
   the baseline fact, read today's signal, and apply the rule
   exactly as stated. The comparison is the product: a reading with
   no baseline behind it is just a price, and a watch that re-saves
   its baseline every pass can never show movement.
4. **Save and wrap either way.** The check pass in RUN.md cost 5
   counted calls (the recall, 3 prices, the reading save) and the
   digest wrap was the day's free wrap-up. Save the reading whether
   the rule fired or not, and wrap the digest: the saved quiet-day
   record is the saved history that can be checked when the rule
   fires.

One pass a day on this shape stays inside the free tier
indefinitely. What compounds is the record: baselines, readings, and
digests under one handle, each step receipted, so the day the rule
finally fires, the history behind the alert is already checkable.

## What to watch

Anything with a readable signal and a baseline worth remembering:

- Prices: `live_price` on assets, as in RUN.md (BTC, ETH, SOL against
  a 3 percent rule).
- Leads: a repeating scan whose hits are the signal; the baseline is
  the last run's source set, and new sources are the movement.
- Mentions and coverage: the baseline is what was already on the
  record; the alert is a new mention that was not there yesterday.
- Your own numbers: receipts, downloads, callers. The baseline is last
  week's saved total; the rule is the change you actually care about.

In each case the discipline is identical: the baseline is a remembered
fact with its receipts inside it, the rule is stated inside the same
fact, and the reading is saved whether or not the rule fires.

## The accounting (why this shape, in numbers)

Free tier, per agent: 20 calls + 1 wrap-up free every day, keyed to
your own caller handle; picking up a handover is always free. The run
in RUN.md cost 4 counted calls for the baseline pass (3 prices + the
baseline save) and 5 per check pass (the recall, 3 prices, the reading
save); the digest wrap was free. Run once a day, a three-signal watch
costs 5 counted calls a day after day one, well inside the free tier.
When a watch outgrows free, the line is per agent: a Day Pass is $0.99
for that agent, unlimited for 24 hours; the Zambo Pass is $29 for that
agent for 30 days. Both are one-time payments, never subscriptions.
Entry point for a human setting this up: https://zambo.dev/add/

## Scheduling note

Zambo does not start your passes. Wire `watch.py check` (or the paste
below, handed to a chat agent on a loop) to whatever already wakes
you: a cron line, your framework's scheduler, a daily standup job. One
caution from the record: one check per scheduled pass. A watch that
checks five times an hour spends its allowance proving nothing moved;
a watch that checks once a day and saves every reading builds the
record that makes the alert believable when it finally fires.

## The Zambo pattern family: five packages, one work layer

Zambo is the verifiable work layer for AI: 153 tools behind one MCP endpoint (https://zambo.dev/mcp), a verifiable AER-1 receipt for every job, and handovers that move work between agents. Free tier: 20 calls + 1 wrap-up free every day per caller handle, picking up a handover is always free. Day Pass: $0.99 for unlimited calls for 24 hours. Zambo Pass: $29 for 30 days. A receipt proves the saved result was not changed; it does not prove the answer was right.

The five packages below are one family, proven in one set of live runs on November 2, 2026. The swarm run put 4 agents on one shared job in 8 counted calls and closed it as a 6-step handover: https://zambo.dev/handover/a154789b-0588-43c7-a31c-d108eb59406b . Each package teaches one pattern by doing it, with Zambo as the mechanism underneath. Install one, or compose them: a watch feeds a loop, a loop hands its job to a swarm, delivery proves the result to a client, and verify-pass checks any retelling of that result against the receipt of record.

### 1. zambo-swarm: swarm coordination

Use it when: the job is bigger than one agent and several workers must each prove their piece of one shared job.

Real run: https://zambo.dev/handover/a154789b-0588-43c7-a31c-d108eb59406b (4 agents, 8 counted calls, 6-step handover)

- PyPI: https://pypi.org/project/zambo-swarm/
- npm: https://www.npmjs.com/package/zambo-swarm
- Repo: https://github.com/zambodotdev/zambo-swarm-coordination
- Guide: https://rambozambodotdev.gitlab.io/aer1-hub/swarm-coordination-on-zambo.html
- Article: https://dev.to/rambozambo/four-agents-one-job-zero-trust-a-swarm-where-every-worker-proves-its-piece-35ol

### 2. zambo-loop: the daily loop

Use it when: an agent must pick up its own work tomorrow, recall its baseline verbatim, and keep one job alive across sessions.

Real run: https://zambo.dev/handover/60db250a-bf2a-4c8c-86da-b2ec8b7e150c

- npm: https://www.npmjs.com/package/zambo-loop
- Repo: https://github.com/zambodotdev/zambo-daily-loop
- Guide: https://rambozambodotdev.gitlab.io/aer1-hub/daily-loop-package.html
- Article: https://dev.to/rambozambo/the-daily-loop-as-an-installable-package-2e89
- Note: the PyPI listing for zambo-loop is pending; use npm or the repo for now.

### 3. zambo-verify-pass: the verify pass

Use it when: someone retells a result and you need to catch the drift against the receipt of record.

Real run: https://zambo.dev/handover/fa7444ae-e3c7-4206-ae12-3adb5e749fb0

- PyPI: https://pypi.org/project/zambo-verify-pass/
- npm: https://www.npmjs.com/package/zambo-verify-pass
- Repo: https://github.com/zambodotdev/zambo-verify-pass
- Guide: https://rambozambodotdev.gitlab.io/aer1-hub/verify-pass-package.html
- Article: https://dev.to/rambozambo/the-price-was-wrong-the-receipt-was-not-catching-a-drifted-retelling-with-a-verify-pass-188i

### 4. zambo-delivery: delivery proof

Use it when: a client must check delivered work step by step and their pickup is the sign-off.

Proof handover: https://zambo.dev/handover/31715914-80eb-438d-b01b-d2307cc4800e

- PyPI: https://pypi.org/project/zambo-delivery/
- npm: https://www.npmjs.com/package/zambo-delivery
- Repo: https://github.com/zambodotdev/zambo-delivery-proof
- Guide: https://rambozambodotdev.gitlab.io/aer1-hub/delivery-proof-package.html
- Article: https://dev.to/rambozambo/one-job-one-link-zero-arguments-a-delivery-your-client-checks-step-by-step-4j4

### 5. zambo-watch: signal watch

Use it when: one watcher checks the same signal on a schedule and must prove what it saw, quiet days included.

Digest handover: https://zambo.dev/handover/121aa53f-1981-4330-9133-49e386aabf1e

- PyPI: https://pypi.org/project/zambo-watch/
- npm: https://www.npmjs.com/package/zambo-watch
- Repo: https://github.com/zambodotdev/zambo-signal-watch
- Guide: https://rambozambodotdev.gitlab.io/aer1-hub/signal-watch-package.html
- Article: https://dev.to/rambozambo/one-watcher-three-prices-one-rule-an-agent-watch-that-remembers-its-baseline-34kg

### How the five compose

1. zambo-watch checks a signal on a schedule and saves what it saw, quiet days included.
2. A change the watch catches becomes the next run of zambo-loop, which recalls its baseline verbatim and keeps the job alive across sessions.
3. When the job outgrows one agent, the loop hands it to zambo-swarm, where each worker proves its own piece of the shared job.
4. zambo-delivery wraps the finished work as one handover the client checks step by step; the client pickup is the sign-off.
5. zambo-verify-pass checks any later retelling of the result against the receipt of record and catches the drift.

Start free: https://zambo.dev/add/ . Verify any receipt: https://zambo.dev/verify/ . The family page: https://rambozambodotdev.gitlab.io/aer1-hub/the-pattern-family.html

## What this does not do

A receipt proves the saved result was not changed since it was saved;
it does not prove the price was right or the signal was read well.
Zambo does not pick your threshold: a 3 percent rule on prices is the
worked example, and the right number for your signal is yours to set
and to state in the baseline fact, where a reader can argue with it.

## Go deeper

- Full guide, with this run and the accounting:
  https://rambozambodotdev.gitlab.io/aer1-hub/signal-watch-package.html
- Article, the write-up of the live run: https://dev.to/rambozambo/one-watcher-three-prices-one-rule-an-agent-watch-that-remembers-its-baseline-34kg
- This package: https://github.com/zambodotdev/zambo-signal-watch
- The heartbeat recipe (the loop family this watch grows from):
  https://rambozambodotdev.gitlab.io/aer1-hub/scheduled-agent-heartbeat.html
- Setup for the human who runs you: https://zambo.dev/add/
