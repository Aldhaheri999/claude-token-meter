# Claude Token Meter

A desktop widget that tracks your **lifetime Claude Code token usage**. Parses all local transcript files and displays a running total with cost estimates.

![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue) ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey) ![License](https://img.shields.io/badge/license-MIT-green)

## What it shows

- **Total lifetime tokens** (input + output + cache)
- **Breakdown**: input, output, cache reads, cache writes
- **API-equivalent cost** (what it would cost at API rates)
- **Session count**

## Quick start

```bash
# Clone
git clone https://github.com/AAbdulla-Lime/claude-token-meter.git
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

## How it works

Claude Code stores session transcripts as JSONL files in `~/.claude/projects/`. Each assistant message contains a `usage` object with token counts:

```json
{
  "usage": {
    "input_tokens": 3,
    "output_tokens": 26,
    "cache_read_input_tokens": 14738,
    "cache_creation_input_tokens": 10054
  }
}
```

The scanner reads all transcript files, sums the usage per session, and stores the results. The widget displays the running totals.

## Notes

- **Claude Code only** — this tracks CLI usage, not claude.ai web/app conversations
- **API-equivalent cost** — if you're on Claude Max (flat subscription), your actual cost is your subscription fee, not the API estimate
- **Cache reads** will dominate your token count — this is normal (Claude re-reads cached context each turn)
- First scan may take a minute if you have hundreds of sessions

## License

MIT
