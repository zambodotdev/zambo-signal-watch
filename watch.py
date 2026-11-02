#!/usr/bin/env python3
"""Signal watch on Zambo: baseline mode + check mode. Stdlib only.

The pattern: watch a signal on a schedule, remember the baseline, alert
only on real movement, wrap the digest.

  python3 watch.py baseline   first pass: read the signals, save the
                              baseline and the threshold rule to memory
                              under your own caller handle.
  python3 watch.py check      later passes: recall the baseline, read
                              the signals again, apply the rule, save
                              the reading, and wrap a digest handover
                              either way (alert or quiet).

Identity: on first run the endpoint issues a caller handle; it is saved
to the state file (default: zambo-watch-state.json next to this script,
override with ZAMBO_WATCH_STATE) and presented on every later call. Your
memory, your baselines, and your daily free allowance key to that
handle. Lose the state file and you come back as a stranger.

Config (environment):
  ZAMBO_WATCH_SYMBOLS    comma list, default "BTC,ETH,SOL"
  ZAMBO_WATCH_THRESHOLD  percent move that alerts, default 3
  ZAMBO_WATCH_LABEL      your agent name, default "signal-watch"
  ZAMBO_WATCH_JOB        shared job id, default "signal-watch"
  ZAMBO_MCP_URL          endpoint, default https://zambo.dev/mcp
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = os.environ.get("ZAMBO_MCP_URL", "https://zambo.dev/mcp")
LABEL = os.environ.get("ZAMBO_WATCH_LABEL", "signal-watch")
JOB = os.environ.get("ZAMBO_WATCH_JOB", "signal-watch")
SYMBOLS = [s.strip().upper() for s in
           os.environ.get("ZAMBO_WATCH_SYMBOLS", "BTC,ETH,SOL").split(",") if s.strip()]
THRESHOLD = float(os.environ.get("ZAMBO_WATCH_THRESHOLD", "3"))
STATE_PATH = Path(os.environ.get(
    "ZAMBO_WATCH_STATE", Path(__file__).with_name("zambo-watch-state.json")))

RUN_RE = re.compile(r"https://zambo\.dev/run/[0-9a-f-]{36}")
HO_RE = re.compile(r"https://zambo\.dev/handover/[0-9a-f-]{36}")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def parse_rpc(raw):
    msg = None
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            try:
                msg = json.loads(line[5:])
            except Exception:
                pass
    if msg is None:
        msg = json.loads(raw)
    if "error" in msg:
        raise RuntimeError(f"MCP error: {msg['error']}")
    return msg.get("result", {})


class Watcher:
    def __init__(self, state):
        self.state = state
        self.mcp_session = state.get("mcp_session_id")
        self.caller_handle = state.get("caller_handle")
        self.quota_handle = state.get("quota_handle")
        self._n = 0

    def _headers(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "X-Agent-Id": LABEL,
            "X-Agent-Name": LABEL,
            "User-Agent": f"zambo-watch/{LABEL}",
        }
        if self.mcp_session:
            headers["Mcp-Session-Id"] = self.mcp_session
        return headers

    def _absorb_headers(self, header_block):
        for line in header_block.splitlines():
            if ":" not in line:
                continue
            name, value = line.split(":", 1)
            name, value = name.strip().lower(), value.strip()
            if name == "mcp-session-id" and value:
                self.mcp_session = value
            elif name == "x-zambo-caller-handle" and value and not self.caller_handle:
                self.caller_handle = value

    def _post_curl(self, payload):
        # curl is the transport when present: no Python dependencies, and
        # it rides out flaky proxies that clip urllib response bodies.
        cmd = ["curl", "-sS", "--http1.1", "-i", "-X", "POST", URL,
               "--data-binary", "@-"]
        for k, v in self._headers().items():
            cmd += ["-H", f"{k}: {v}"]
        cmd += ["-H", "Expect:"]
        out = subprocess.run(cmd, input=json.dumps(payload).encode(),
                             capture_output=True, timeout=120)
        if out.returncode != 0:
            raise RuntimeError(f"curl transport failed: {out.stderr.decode()[:200]}")
        raw = out.stdout.decode()
        # With -i the header block(s) precede the body; take the last one.
        parts = raw.split("\r\n\r\n")
        if len(parts) < 2:
            parts = raw.split("\n\n")
        body = parts[-1]
        for block in parts[:-1]:
            if "mcp-session-id" in block.lower() or "x-zambo" in block.lower():
                self._absorb_headers(block)
        return body

    def _post_urllib(self, payload):
        req = urllib.request.Request(
            URL, data=json.dumps(payload).encode(),
            headers=self._headers(), method="POST")
        with urllib.request.urlopen(req, timeout=90) as resp:
            block = "\n".join(f"{k}: {v}" for k, v in resp.headers.items())
            self._absorb_headers(block)
            return resp.read().decode()

    def _post(self, payload, expect=True):
        raw = None
        last = None
        for attempt in range(3):
            try:
                if shutil.which("curl"):
                    raw = self._post_curl(payload)
                else:
                    raw = self._post_urllib(payload)
                break
            except Exception as e:
                last = e
                raw = None
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        if raw is None:
            raise last
        if not expect:
            return None
        return parse_rpc(raw)

    def _id(self):
        self._n += 1
        return self._n

    def initialize(self):
        result = self._post({
            "jsonrpc": "2.0", "id": self._id(), "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": LABEL, "version": "1.0.0"}},
        })
        meta = result.get("_meta", {}) or {}
        if not self.caller_handle:
            self.caller_handle = meta.get("caller_handle")
        self.quota_handle = meta.get("quota_handle") or self.quota_handle
        try:
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized"},
                       expect=False)
        except Exception:
            pass
        if not self.caller_handle:
            raise RuntimeError("endpoint did not issue a caller handle")
        self.state.update({
            "agent_name": LABEL, "caller_handle": self.caller_handle,
            "quota_handle": self.quota_handle,
            "mcp_session_id": self.mcp_session, "endpoint": URL, "job": JOB,
        })
        save_state(self.state)
        return result

    def call(self, tool, arguments):
        args = dict(arguments)
        args["_caller_handle"] = self.caller_handle
        args.setdefault("_caller_label", LABEL)
        args.setdefault("_session_id", JOB)
        params = {"name": tool, "arguments": args}
        if self.quota_handle:
            params["_meta"] = {"quota_handle": self.quota_handle}
        result = self._post({"jsonrpc": "2.0", "id": self._id(),
                             "method": "tools/call", "params": params})
        sc = result.get("structuredContent") or {}
        if not self.quota_handle:
            self.quota_handle = (result.get("_meta") or {}).get("quota_handle") \
                or sc.get("quota_handle")
            if self.quota_handle:
                self.state["quota_handle"] = self.quota_handle
                save_state(self.state)
        blob = json.dumps(result)
        return {
            "result": result, "structured": sc,
            "receipts": list(dict.fromkeys(RUN_RE.findall(blob))),
            "handovers": list(dict.fromkeys(HO_RE.findall(blob))),
            "text": texts(result),
        }


def texts(result):
    out = []
    for block in (result.get("content") or []):
        if block.get("type") == "text":
            out.append(block.get("text", ""))
    sc = result.get("structuredContent")
    if sc:
        out.append(json.dumps(sc))
    return "\n".join(out)


def dig(obj, keys):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and isinstance(v, (int, float)):
                return v
            r = dig(v, keys)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = dig(v, keys)
            if r is not None:
                return r
    return None


def price_of(entry):
    price = dig(entry["structured"], {"price", "usd", "current_price", "price_usd", "value", "last"})
    if price is None:
        m = re.search(r"\$([0-9][0-9,]*\.?[0-9]*)", entry["text"])
        if m:
            price = float(m.group(1).replace(",", ""))
    chg = dig(entry["structured"], {"change_24h", "price_change_percentage_24h",
                                    "change_24h_pct", "percent_change_24h", "change24h"})
    return price, chg


def fmt(price):
    return f"{price:,.2f}" if price is not None else "unknown"


def read_prices(w):
    prices = {}
    receipts = {}
    for sym in SYMBOLS:
        e = w.call("live_price", {"symbol": sym})
        price, chg = price_of(e)
        if price is None:
            raise RuntimeError(f"could not parse a price for {sym}")
        prices[sym] = price
        receipts[sym] = e["receipts"][0] if e["receipts"] else None
        print(f"live_price {sym}: ${fmt(price)}  receipt: {receipts[sym]}")
    return prices, receipts


def baseline_fact(prices, receipts):
    parts = ", ".join(f"{s} {prices[s]}" for s in SYMBOLS)
    recs = "; ".join(f"{s} price receipt {receipts[s]}" for s in SYMBOLS)
    return (f"Signal watch baseline, set {now_iso()}. Rule: alert when any watched "
            f"asset moves {THRESHOLD:g} percent or more from its baseline. "
            f"Baselines in USD from live_price: {parts}. {recs}. Job: {JOB}.")


def parse_baselines(text):
    out = {}
    start = text.find("Baselines in USD")
    if start >= 0:
        seg = text[start:start + 300]
        for sym in SYMBOLS:
            mm = re.search(rf"\b{sym}\s+([0-9][0-9,]*\.?[0-9]*)", seg)
            if mm:
                out[sym] = float(mm.group(1).replace(",", ""))
    return out


def mode_baseline():
    state = load_state()
    w = Watcher(state)
    w.initialize()
    print(f"identity: {LABEL} (handle saved to {STATE_PATH})")
    prices, receipts = read_prices(w)
    e = w.call("memory_remember", {
        "fact": baseline_fact(prices, receipts), "agent_name": LABEL})
    print("baseline saved. remember receipt:", e["receipts"])
    state["baselines"] = prices
    state["threshold_percent"] = THRESHOLD
    save_state(state)
    print(json.dumps({"mode": "baseline", "prices": prices,
                      "receipts": receipts,
                      "remember_receipt": e["receipts"]}, indent=2))
    return 0


def mode_check():
    state = load_state()
    if not state.get("caller_handle"):
        print("no saved identity or baseline: run `watch.py baseline` first",
              file=sys.stderr)
        return 2
    w = Watcher(state)
    w.initialize()

    rec = w.call("memory_recall", {
        "query": "signal watch baseline rule alert threshold"})
    baselines = parse_baselines(rec["text"])
    source = "memory_recall"
    if len(baselines) < len(SYMBOLS):
        baselines = {**state.get("baselines", {}), **baselines}
        source = "memory_recall + state file fallback"
    print(f"baselines recalled ({source}):",
          {s: baselines.get(s) for s in SYMBOLS})

    prices, receipts = read_prices(w)
    moves, fired = {}, []
    for sym in SYMBOLS:
        base = baselines.get(sym)
        moves[sym] = ((prices[sym] - base) / base * 100.0) if base else None
        if moves[sym] is not None and abs(moves[sym]) >= THRESHOLD:
            fired.append(sym)
    alert = bool(fired)
    move_line = ", ".join(
        f"{s} {moves[s]:+.2f} percent from baseline" if moves[s] is not None
        else f"{s} no baseline" for s in SYMBOLS)
    price_line = ", ".join(f"{s} ${fmt(prices[s])}" for s in SYMBOLS)
    print("moves:", move_line)
    print("rule outcome:", "ALERT on " + ", ".join(fired) if alert else "no alert")

    reading = (f"Signal watch reading, {now_iso()}. {price_line}. Moves: {move_line}. "
               f"Rule ({THRESHOLD:g} percent or more from baseline): "
               f"{'ALERT on ' + ', '.join(fired) if alert else 'no alert'}. "
               f"Baselines unchanged. Job: {JOB}.")
    e = w.call("memory_remember", {"fact": reading, "agent_name": LABEL})
    print("reading saved. remember receipt:", e["receipts"])

    if alert:
        fired_line = " and ".join(
            f"{s} moved {moves[s]:+.2f} percent" for s in fired)
        summary = (f"Signal watch digest, {now_iso()}: ALERT. {fired_line}, at or past "
                   f"the {THRESHOLD:g} percent threshold against the saved baseline. "
                   f"All readings: {price_line}. {move_line}. The baseline and every "
                   f"reading sit in memory under this watch's own handle, job {JOB}.")
    else:
        summary = (f"Signal watch digest, {now_iso()}: quiet check, no alert. "
                   f"No watched asset moved {THRESHOLD:g} percent or more from its "
                   f"saved baseline. {price_line}. {move_line}. The reading is saved "
                   f"in memory either way, so a quiet day is on the record too. "
                   f"Job: {JOB}.")
    hov = w.call("handover", {
        "summary": summary,
        "goal": (f"Watch {', '.join(SYMBOLS)} against the saved baseline; alert on a "
                 f"move of {THRESHOLD:g} percent or more; publish a digest either way."),
        "recipient": "the operator running this watch",
        "recipient_type": "human",
        "next_steps": [
            "Run watch.py check again on the next scheduled pass; the baseline and every reading stay under this job.",
            "Re-run watch.py baseline only when the operator resets the watch; a new baseline is a new remembered fact, never an edit.",
        ],
    })
    print("digest handover:", hov["handovers"])
    print("wrap receipt:", hov["receipts"])
    print(json.dumps({"mode": "check", "prices": prices, "moves": moves,
                      "alert": alert, "fired": fired,
                      "handover": hov["handovers"],
                      "wrap_receipt": hov["receipts"]}, indent=2))
    return 0


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("baseline", "check"):
        print(__doc__)
        return 2
    return mode_baseline() if sys.argv[1] == "baseline" else mode_check()


if __name__ == "__main__":
    sys.exit(main())
