# Claude Token Meter

A desktop widget that tracks your **lifetime Claude Code output token usage** — the tokens Claude actually generated for you.

![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue) ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey) ![License](https://img.shields.io/badge/license-MIT-green)

## What it shows

- **Output tokens** — the real work Claude did for you (big number)
- **API-equivalent cost** — what it would cost at API rates
- **Session count**

## Quick start

```bash
# Clone
git clone https://github.com/Aldhaheri999/claude-token-meter.git
cd claude-token-meter

# Run initial scan (finds all past sessions)
python3 scanner.py

# Launch the desktop widget
pythonw meter.pyw    # Windows
python3 meter.pyw    # macOS/Linux
```

No dependencies — uses only Python standard library (tkinter).

## Auto-update after each session

Add a `SessionEnd` hook to your `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"/path/to/claude-token-meter/hook_session_end.py\""
          }
        ]
      }
    ]
  }
}
```

Replace `/path/to/` with the actual path where you cloned the repo. The hook runs when each Claude Code session ends, parses the transcript, and updates `data.json`.

## Widget controls

| Action | Effect |
|--------|--------|
| **Drag** | Move the widget anywhere |
| **Double-click** | Full rescan of all transcripts |
| **Right-click** | Quit |
| **Escape** | Quit |

The widget auto-refreshes every 30 seconds from `data.json`.

## Files

| File | Purpose |
|------|---------|
| `scanner.py` | Scans `~/.claude/projects/**/*.jsonl` and builds `data.json` |
| `meter.pyw` | Tkinter desktop widget (always-on-top) |
| `hook_session_end.py` | Claude Code SessionEnd hook for auto-tracking |
| `launch.vbs` | Silent launcher for Windows (no console window) |
| `data.json` | Persistent usage data (auto-generated, gitignored) |

## Why output tokens?

Most AI providers count both input and output tokens, but **output tokens are the meaningful metric** — they represent what Claude actually wrote for you. Input tokens and cache reads are inflated by context re-reads every turn and don't reflect real usage.

## Notes

- **Claude Code only** — this tracks CLI usage, not claude.ai web/app conversations
- **API-equivalent cost** — if you're on Claude Max (flat subscription), your actual cost is your subscription fee, not the API estimate
- First scan may take a minute if you have hundreds of sessions

## License

MIT
