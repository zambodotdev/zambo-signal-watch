# Signal watch run: the proof record

Executed live against https://zambo.dev/mcp on November 2, 2026 (20:45 to
20:49 UTC). Job id (_session_id): `signal-watch-2026-11-02`. Pattern: one
watcher identity with its own server-issued caller handle, running the
package's own `watch.py`. Identity file: `identity-signal-watch.json` in
the build record (handle value lives there only). Working logs:
`work/run-baseline.log`, `work/run-check.log`, `work/run-check2.log` in
the build record.

## The watcher

| Agent | Role | Identity file |
|---|---|---|
| signal-watch-demo | Saves the baseline, checks against it, wraps the digest | `identity-signal-watch.json` (build record) |

A fresh identity, created for this run. It is not the heartbeat demo's
identity (the-18th-heartbeat-demo): a new handle, a new allowance, its
own memory. That is the pattern's point: the watch's state lives in the
watch's own memory, not in a file a human keeps.

## The rule

Alert when any watched asset moves 3 percent or more from its baseline.
Watched assets: BTC, ETH, SOL, priced by `live_price`.

## Pass 1: baseline (watch.py baseline)

1. Initialized; the endpoint issued a caller handle; saved before any
   other call.
2. `live_price` BTC at $76,800.00. Receipt:
   https://zambo.dev/run/a78b8851-5ab7-4b4d-bf70-a90a46a87b6c
3. `live_price` ETH at $2,244.62. Receipt:
   https://zambo.dev/run/b1adb980-2b13-4680-bc97-2b3b4e54c745
4. `live_price` SOL at $91.29. Receipt:
   https://zambo.dev/run/25da9cc8-616d-4383-9498-3aaad7ee5f27
5. `memory_remember` saved the baseline fact: the three prices, the
   rule, and the three price receipts, under the job id. Receipt:
   https://zambo.dev/run/a6fe88a7-a882-4880-90f8-5437bb05aa7d

## Pass 2: check (watch.py check, first attempt)

Minutes later, the check pass recalled memory, re-priced, saved the
reading, and wrapped a digest. Its numbers: BTC $76,802.00, ETH
$2,245.12, SOL $91.32; moves +0.00, +0.02, +0.03 percent; no alert.
Reading receipt: https://zambo.dev/run/93e27d2d-0500-4d57-b3a7-9266e06f2806
Digest handover: https://zambo.dev/handover/8654e4d4-765a-47ef-955a-fa67e84cab6d

Recorded honestly: in this pass the baseline values were completed from
the watch's local state file because the first version of the baseline
parser missed the decimal point in the recalled fact's numbers. The
recall itself returned the baseline fact in full; the parser was the
only gap. The parser was fixed, the fix was proven against a fresh
recall (all three baselines extracted from memory text alone), and the
canonical check pass below was run with the fixed, shipped code.

## Pass 3: check (watch.py check, shipped code, canonical)

1. `memory_recall` returned the baseline fact; the parser extracted all
   three baselines from the recalled text alone: BTC 76800.0, ETH
   2244.62, SOL 91.29. Verbatim the values saved in pass 1.
2. `live_price` BTC at $76,793.00. Receipt:
   https://zambo.dev/run/cb8202ea-3913-468f-b7b8-f281c8cf6122
3. `live_price` ETH at $2,245.12. Receipt:
   https://zambo.dev/run/adf91ada-41b8-4253-a396-54fa019d5bdd
4. `live_price` SOL at $91.34. Receipt:
   https://zambo.dev/run/598d63b7-8144-46f8-9707-b4a15169acd8
5. Moves computed against the recalled baselines: BTC -0.01 percent,
   ETH +0.02 percent, SOL +0.05 percent. The rule was applied exactly
   as stated: no asset reached 3 percent, so NO ALERT. The quiet
   outcome is the honest outcome for a check run minutes after its
   baseline; the digest says so, in so many words.
6. `memory_remember` saved the reading. Receipt:
   https://zambo.dev/run/12b0616b-e825-4574-9501-ac88ef06f2d6
7. The digest wrap (`handover`, the day's free wrap-up): the quiet-day
   format, naming every price, every move, and the rule's outcome.
   Digest handover:
   https://zambo.dev/handover/121aa53f-1981-4330-9133-49e386aabf1e
   Wrap receipts:
   https://zambo.dev/run/1fb43864-4cac-4c0f-a8d3-a3c495fa82b9
   https://zambo.dev/run/75facd71-b2d0-4812-ab5d-8df6d26fe089

## Free-tier accounting

Counted calls key to the watcher's own handle. The documented passes:
baseline 4 (3 prices + the baseline save); each check 5 (the recall, 3
prices, the reading save); each digest wrap free. Three passes plus one
extra recall to prove the parser fix: 15 counted calls, inside the 20
free calls for the day, zero paid calls. (A transport rehearsal before
the baseline pass cost a few extra price reads against the same handle;
the pattern run cleanly costs 4 once, then 5 per check.) Run daily, a
watch shaped like this costs 5 counted calls a day after day one.

## Mechanics that differed from the naive pattern (teach only these)

- The baseline is a remembered fact, not a config file. The check pass
  recalls it from the endpoint's memory under the watch's handle; the
  local state file holds the identity, and only a fallback copy of the
  numbers.
- Save the reading either way. A quiet day with no saved reading is a
  gap in the record exactly when you later need to prove the watch was
  running. The digest wraps on quiet days too, in the quiet format.
- A receipt proves the saved result was not changed since it was
  saved. It does not prove the price was right, and the digest never
  claims otherwise.

## Verification

Every link above was fetched on 2026-11-02 after the run: all returned
HTTP 200 (16 of 16, including both digest handovers and every price,
remember, and wrap receipt).
