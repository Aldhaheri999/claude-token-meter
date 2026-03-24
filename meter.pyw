"""
Claude Token Meter — Always-on-top desktop widget.
Tracks output tokens: the real work Claude did for you.
Double-click to rescan. Right-click to quit. Drag to move.
Works on Windows, macOS, and Linux.
"""

import json
import pathlib
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime

DATA_FILE = pathlib.Path(__file__).parent / "data.json"
SCANNER = pathlib.Path(__file__).parent / "scanner.py"

BG = "#0f0f0f"
ACCENT = "#6c5ce7"
DIM = "#666666"
GREEN = "#00b894"
ORANGE = "#fdcb6e"


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
            pass

        self.overrideredirect(True)

        self.w = 280
        self.h = 150
        x = self.winfo_screenwidth() - self.w - 20
        y = self.winfo_screenheight() - self.h - 60
        self.geometry(f"{self.w}x{self.h}+{x}+{y}")

        self._drag_x = 0
        self._drag_y = 0

        self._build_ui()

        if not DATA_FILE.exists():
            self._rescan()
        else:
            self._refresh()

        self.bind("<Button-1>", self._start_drag)
        self.bind("<B1-Motion>", self._do_drag)
        self.bind("<Double-Button-1>", self._rescan)
        self.bind("<Button-3>", self._quit)
        self.bind("<Escape>", self._quit)
        self.after(30000, self._schedule_refresh)

    def _build_ui(self):
        # Title bar
        title = tk.Frame(self, bg=ACCENT, height=28)
        title.pack(fill="x")
        title.pack_propagate(False)
        tk.Label(title, text="CLAUDE OUTPUT METER", font=("Segoe UI", 9, "bold"),
                 fg="white", bg=ACCENT).pack(side="left", padx=10)
        self.status_dot = tk.Label(title, text="●", font=("Segoe UI", 8),
                                   fg=GREEN, bg=ACCENT)
        self.status_dot.pack(side="right", padx=10)

        # Content
        content = tk.Frame(self, bg=BG, padx=15, pady=8)
        content.pack(fill="both", expand=True)

        # Output tokens — the hero number
        self.output_label = tk.Label(content, text="—", font=("Segoe UI", 36, "bold"),
                                     fg="white", bg=BG)
        self.output_label.pack(anchor="w")
        tk.Label(content, text="OUTPUT TOKENS", font=("Segoe UI", 8),
                 fg=DIM, bg=BG).pack(anchor="w")

        # Sessions + since date
        tk.Frame(content, bg="#222", height=1).pack(fill="x", pady=4)
        self.info_label = tk.Label(content, text="—", font=("Segoe UI", 10),
                                   fg="#aaaaaa", bg=BG)
        self.info_label.pack(anchor="w")

        # Footer
        self.footer = tk.Label(self, text="Dbl-click: rescan | R-click: quit",
                               font=("Segoe UI", 7), fg="#333", bg=BG)
        self.footer.pack(side="bottom", pady=1)

    def _refresh(self):
        data = load_data()
        if not data or "totals" not in data:
            self.output_label.config(text="No data")
            self.footer.config(text="Double-click to run first scan")
            return

        t = data["totals"]
        self.output_label.config(text=format_tokens(t.get("output_tokens", 0)))

        # Sessions + since date
        since = t.get("first_session", "")
        since_str = ""
        if since:
            try:
                dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                since_str = f"  ·  since {dt.strftime('%b %d, %Y')}"
            except Exception:
                pass
        self.info_label.config(text=f"{t.get('sessions', 0)} sessions{since_str}")

        scan_time = data.get("last_scan", "")
        try:
            scan_time = datetime.fromisoformat(scan_time).strftime("%H:%M")
        except Exception:
            scan_time = "—"
        self.footer.config(text=f"Last scan: {scan_time}  |  Dbl-click: rescan  |  R-click: quit")

    def _schedule_refresh(self):
        self._refresh()
        self.after(30000, self._schedule_refresh)

    def _rescan(self, event=None):
        self.status_dot.config(fg=ORANGE)
        self.footer.config(text="Scanning...")
        self.update()

        def do_scan():
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x08000000
            subprocess.run([sys.executable, str(SCANNER)],
                           cwd=str(SCANNER.parent), **kwargs)
            self.after(0, self._on_scan_done)

        threading.Thread(target=do_scan, daemon=True).start()

    def _on_scan_done(self):
        self.status_dot.config(fg=GREEN)
        self._refresh()

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        self.geometry(f"+{self.winfo_x() + event.x - self._drag_x}+{self.winfo_y() + event.y - self._drag_y}")

    def _quit(self, event=None):
        self.destroy()


if __name__ == "__main__":
    TokenMeter().mainloop()
