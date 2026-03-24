"""
Claude Code SessionEnd hook — parses the session transcript
and appends token usage to the lifetime data.json.

Setup: Add this to your ~/.claude/settings.json:

{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"/path/to/token-meter/hook_session_end.py\""
          }
        ]
      }
    ]
  }
}
"""

import json
import sys
import pathlib
from datetime import datetime

DATA_FILE = pathlib.Path(__file__).parent / "data.json"

# Pricing per million tokens (Claude Opus 4, as of 2026)
PRICING = {
    "input": 15.00,
    "output": 75.00,
    "cache_read": 1.50,
    "cache_creation": 18.75,
}


def estimate_cost(usage):
    cost = 0.0
    cost += usage.get("input_tokens", 0) / 1_000_000 * PRICING["input"]
    cost += usage.get("output_tokens", 0) / 1_000_000 * PRICING["output"]
    cost += usage.get("cache_read_input_tokens", 0) / 1_000_000 * PRICING["cache_read"]
    cost += usage.get("cache_creation_input_tokens", 0) / 1_000_000 * PRICING["cache_creation"]
    return cost


def main():
    # Hook receives JSON on stdin with session_id and transcript_path
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        return

    transcript_path = hook_input.get("transcript_path")
    session_id = hook_input.get("session_id", "unknown")

    if not transcript_path or not pathlib.Path(transcript_path).exists():
        return

    # Parse transcript for token usage
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
    }
    model = None
    first_ts = None

    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            if not first_ts and obj.get("timestamp"):
                first_ts = obj["timestamp"]

            if obj.get("type") == "assistant":
                msg = obj.get("message", {})
                u = msg.get("usage", {})
                if not model and msg.get("model"):
                    model = msg["model"]
                for key in usage:
                    usage[key] += u.get(key, 0)

    if usage["input_tokens"] == 0 and usage["output_tokens"] == 0:
        return

    cost = round(estimate_cost(usage), 4)

    # Load existing data
    data = {"sessions": {}, "totals": {}, "last_scan": None}
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE) as f:
                data = json.load(f)
        except Exception:
            pass

    # Add this session
    key = transcript_path
    if key not in data.get("sessions", {}):
        data.setdefault("sessions", {})[key] = {
            "file": transcript_path,
            "session_id": session_id,
            "model": model,
            "timestamp": first_ts,
            "usage": usage,
            "cost_usd": cost,
        }

        # Recompute totals
        totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cost_usd": 0.0,
            "sessions": 0,
        }
        for s in data["sessions"].values():
            u = s["usage"]
            for k in ["input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"]:
                totals[k] += u.get(k, 0)
            totals["cost_usd"] += s.get("cost_usd", 0)
            totals["sessions"] += 1

        totals["cost_usd"] = round(totals["cost_usd"], 2)
        totals["total_tokens"] = (
            totals["input_tokens"]
            + totals["output_tokens"]
            + totals["cache_read_input_tokens"]
            + totals["cache_creation_input_tokens"]
        )

        data["totals"] = totals
        data["last_scan"] = datetime.now().isoformat()

        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)


if __name__ == "__main__":
    main()
