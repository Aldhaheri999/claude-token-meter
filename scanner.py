"""
Scan all Claude Code transcript JSONL files and compute lifetime token usage.
Stores results in data.json with per-session breakdown and running totals.
"""

import json
import pathlib
import sys
from datetime import datetime

CLAUDE_DIR = pathlib.Path.home() / ".claude" / "projects"
DATA_FILE = pathlib.Path(__file__).parent / "data.json"

# Pricing per million tokens (Claude Opus 4, as of 2026)
# Update these if Anthropic changes pricing
PRICING = {
    "input": 15.00,
    "output": 75.00,
    "cache_read": 1.50,
    "cache_creation": 18.75,
}


def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"sessions": {}, "totals": {}, "last_scan": None}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def estimate_cost(usage):
    """Estimate USD cost from token counts using API pricing."""
    cost = 0.0
    cost += usage.get("input_tokens", 0) / 1_000_000 * PRICING["input"]
    cost += usage.get("output_tokens", 0) / 1_000_000 * PRICING["output"]
    cost += usage.get("cache_read_input_tokens", 0) / 1_000_000 * PRICING["cache_read"]
    cost += usage.get("cache_creation_input_tokens", 0) / 1_000_000 * PRICING["cache_creation"]
    return cost


def scan_transcript(filepath):
    """Parse a single transcript JSONL and sum token usage."""
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
    }
    first_ts = None
    session_id = None
    model = None

    try:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if not session_id and obj.get("sessionId"):
                    session_id = obj["sessionId"]
                if not first_ts and obj.get("timestamp"):
                    first_ts = obj["timestamp"]

                if obj.get("type") == "assistant":
                    msg = obj.get("message", {})
                    u = msg.get("usage", {})
                    if not model and msg.get("model"):
                        model = msg["model"]
                    for key in usage:
                        usage[key] += u.get(key, 0)
    except Exception as e:
        print(f"  Error reading {filepath.name}: {e}", file=sys.stderr)
        return None

    if usage["input_tokens"] == 0 and usage["output_tokens"] == 0:
        return None

    return {
        "file": str(filepath),
        "session_id": session_id or filepath.stem,
        "model": model,
        "timestamp": first_ts,
        "usage": usage,
        "cost_usd": round(estimate_cost(usage), 4),
    }


def full_scan():
    """Scan all transcripts and build complete usage database."""
    if not CLAUDE_DIR.exists():
        print(f"Claude Code directory not found: {CLAUDE_DIR}")
        print("Make sure you have Claude Code installed and have run at least one session.")
        sys.exit(1)

    data = load_data()
    known = set(data.get("sessions", {}).keys())

    all_jsonl = list(CLAUDE_DIR.rglob("*.jsonl"))
    print(f"Found {len(all_jsonl)} transcript files")

    new_count = 0
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cost_usd": 0.0,
        "sessions": 0,
    }

    sessions = data.get("sessions", {})

    for i, fpath in enumerate(all_jsonl):
        key = str(fpath)
        if key not in known:
            result = scan_transcript(fpath)
            if result:
                sessions[key] = result
                new_count += 1
            if (i + 1) % 50 == 0:
                print(f"  Scanned {i+1}/{len(all_jsonl)}...")

    # Recompute totals from all sessions
    for s in sessions.values():
        u = s["usage"]
        for k in ["input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"]:
            totals[k] += u.get(k, 0)
        totals["cost_usd"] += s.get("cost_usd", 0)
        totals["sessions"] += 1

    totals["cost_usd"] = round(totals["cost_usd"], 2)

    # Find the earliest session timestamp
    earliest = None
    for s in sessions.values():
        ts = s.get("timestamp")
        if ts:
            if earliest is None or ts < earliest:
                earliest = ts
    totals["first_session"] = earliest

    data["sessions"] = sessions
    data["totals"] = totals
    data["last_scan"] = datetime.now().isoformat()

    save_data(data)

    print(f"\n{'='*50}")
    print(f"  New sessions found: {new_count}")
    print(f"  Total sessions:     {totals['sessions']}")
    print(f"  OUTPUT TOKENS:      {totals['output_tokens']:,}")
    print(f"  API-equiv cost:     ${totals['cost_usd']:,.2f}")
    print(f"{'='*50}")

    return data


if __name__ == "__main__":
    full_scan()
