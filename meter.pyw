"""
Claude Token Meter — Always-on-top desktop widget.
Shows lifetime Claude Code token usage with auto-refresh.
Double-click to run a full rescan. Right-click to quit.
Works on Windows, macOS, and Linux.
"""

import json
import os
import pathlib
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime

DATA_FILE = pathlib.Path(__file__).parent / "data.json"
SCANNER = pathlib.Path(__file__).parent / "scanner.py"

# Colors
BG = "#0f0f0f"
FG = "#e0e0e0"
ACCENT = "#6c5ce7"
DIM = "#666666"
GREEN = "#00b894"
ORANGE = "#fdcb6e"
RED = "#d63031"


def format_tokens(n):
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return None


class TokenMeter(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Claude Token Meter")
        self.configure(bg=BG)
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.92)
        except tk.TclError:
            pass  # alpha not supported on some Linux WMs
        self.overrideredirect(True)

        # Window size and position (bottom-right corner)
        self.w = 320
        self.h = 200
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = screen_w - self.w - 20
        y = screen_h - self.h - 60
        self.geometry(f"{self.w}x{self.h}+{x}+{y}")

        # Drag support
        self._drag_x = 0
        self._drag_y = 0

        # Build UI
        self._build_ui()

        # Run initial scan if no data exists
        if not DATA_FILE.exists():
            self._rescan()
        else:
            self._refresh()

        # Bind events
        self.bind("<Button-1>", self._start_drag)
        self.bind("<B1-Motion>", self._do_drag)
        self.bind("<Double-Button-1>", self._rescan)
        self.bind("<Button-3>", self._quit)
        self.bind("<Escape>", self._quit)

        # Auto-refresh every 30 seconds
        self._schedule_refresh()

    def _build_ui(self):
        # Title bar
        title_frame = tk.Frame(self, bg=ACCENT, height=32)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame,
            text="CLAUDE TOKEN METER",
            font=("Segoe UI", 10, "bold"),
            fg="white",
            bg=ACCENT,
        ).pack(side="left", padx=10)

        self.status_dot = tk.Label(
            title_frame,
            text="●",
            font=("Segoe UI", 8),
            fg=GREEN,
            bg=ACCENT,
        )
        self.status_dot.pack(side="right", padx=10)

        # Main content
        content = tk.Frame(self, bg=BG, padx=15, pady=10)
        content.pack(fill="both", expand=True)

        # Output tokens (big number — the real work Claude did)
        self.total_label = tk.Label(
            content,
            text="—",
            font=("Segoe UI", 28, "bold"),
            fg="white",
            bg=BG,
        )
        self.total_label.pack(anchor="w")

        tk.Label(
            content,
            text="OUTPUT TOKENS",
            font=("Segoe UI", 8),
            fg=DIM,
            bg=BG,
        ).pack(anchor="w")

        # Cost and sessions row
        tk.Frame(content, bg="#222", height=1).pack(fill="x", pady=8)

        bottom = tk.Frame(content, bg=BG)
        bottom.pack(fill="x")

        # Cost
        cost_frame = tk.Frame(bottom, bg=BG)
        cost_frame.pack(side="left")
        tk.Label(cost_frame, text="API EQUIV.", font=("Segoe UI", 7), fg=DIM, bg=BG).pack(anchor="w")
        self.cost_label = tk.Label(
            cost_frame,
            text="$—",
            font=("Segoe UI", 16, "bold"),
            fg=ORANGE,
            bg=BG,
        )
        self.cost_label.pack(anchor="w")

        # Sessions
        sess_frame = tk.Frame(bottom, bg=BG)
        sess_frame.pack(side="right")
        tk.Label(sess_frame, text="SESSIONS", font=("Segoe UI", 7), fg=DIM, bg=BG).pack(anchor="e")
        self.sessions_label = tk.Label(
            sess_frame,
            text="—",
            font=("Segoe UI", 16, "bold"),
            fg=ACCENT,
            bg=BG,
        )
        self.sessions_label.pack(anchor="e")

        # Footer
        self.footer = tk.Label(
            self,
            text="Double-click: rescan  |  Right-click: quit",
            font=("Segoe UI", 7),
            fg="#444",
            bg=BG,
        )
        self.footer.pack(side="bottom", pady=2)

    def _refresh(self):
        data = load_data()
        if not data or "totals" not in data:
            self.total_label.config(text="No data")
            self.footer.config(text="Double-click to run first scan")
            return

        t = data["totals"]
        self.total_label.config(text=format_tokens(t.get("output_tokens", 0)))

        cost = t.get("cost_usd", 0)
        self.cost_label.config(text=f"${cost:,.2f}")
        if cost > 500:
            self.cost_label.config(fg=RED)
        elif cost > 100:
            self.cost_label.config(fg=ORANGE)
        else:
            self.cost_label.config(fg=GREEN)

        self.sessions_label.config(text=str(t.get("sessions", 0)))

        scan_time = data.get("last_scan", "never")
        if scan_time != "never":
            try:
                dt = datetime.fromisoformat(scan_time)
                scan_time = dt.strftime("%H:%M")
            except Exception:
                pass
        self.footer.config(text=f"Last scan: {scan_time}  |  Dbl-click: rescan  |  R-click: quit")

    def _schedule_refresh(self):
        self._refresh()
        self.after(30000, self._schedule_refresh)

    def _rescan(self, event=None):
        self.status_dot.config(fg=ORANGE)
        self.footer.config(text="Scanning...")
        self.update()

        def do_scan():
            # Use CREATE_NO_WINDOW on Windows to avoid console popup
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x08000000
            subprocess.run(
                [sys.executable, str(SCANNER)],
                cwd=str(SCANNER.parent),
                **kwargs,
            )
            self.after(0, self._on_scan_done)

        threading.Thread(target=do_scan, daemon=True).start()

    def _on_scan_done(self):
        self.status_dot.config(fg=GREEN)
        self._refresh()

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        x = self.winfo_x() + event.x - self._drag_x
        y = self.winfo_y() + event.y - self._drag_y
        self.geometry(f"+{x}+{y}")

    def _quit(self, event=None):
        self.destroy()


if __name__ == "__main__":
    app = TokenMeter()
    app.mainloop()
