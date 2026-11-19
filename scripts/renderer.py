#!/usr/bin/env python3
"""Terminal progress bar renderer for AgyBar."""

import os
import sys
import time
from typing import Dict, Any, Optional

# ANSI Color Codes
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
CLEAR_LINE = "\033[2K\r"


class ProgressBarRenderer:
    def __init__(self, style: str = "blocks", width: int = 24):
        self.style = style
        self.width = width

    def format_bar(self, current: int, total: int, width: Optional[int] = None) -> str:
        w = width or self.width
        if total <= 0:
            total = 1
        current = max(0, min(current, total))
        ratio = current / total
        fill_len = int(round(w * ratio))

        if self.style == "ascii":
            fill = "=" * max(0, fill_len - 1) + (">" if fill_len > 0 and fill_len < w else ("=" if fill_len == w else ""))
            empty = "-" * (w - len(fill))
            return f"[{fill}{empty}]"

        elif self.style == "dots":
            fill = "●" * fill_len
            empty = "○" * (w - fill_len)
            return f"[{fill}{empty}]"

        # Default: Unicode blocks
        fill = "█" * fill_len
        empty = "░" * (w - fill_len)
        return f"{CYAN}{fill}{DIM}{empty}{RESET}"

    def format_line(self, state_data: Dict[str, Any]) -> str:
        current = state_data.get("current_step", 1)
        total = state_data.get("total_steps", 4)
        if total <= 0:
            total = 1
        current = max(0, min(current, total))
        pct = int(round((current / total) * 100))

        start_time = state_data.get("start_time", time.time())
        elapsed_sec = int(time.time() - start_time)
        mins, secs = divmod(elapsed_sec, 60)
        time_str = f"{mins:02d}:{secs:02d}"

        step_name = state_data.get("step_name", "")
        # Truncate step name if too long for clean single-line terminal output
        if len(step_name) > 38:
            step_name = step_name[:35] + "..."

        bar = self.format_bar(current, total)
        status = state_data.get("status", "running")

        if status == "completed":
            pct_color = GREEN
            prefix = f"{GREEN}{BOLD}✔ AgyBar{RESET}"
        else:
            pct_color = YELLOW if pct < 50 else CYAN
            prefix = f"{MAGENTA}{BOLD}⚡ AgyBar{RESET}"

        line = (
            f"{prefix} {bar} {pct_color}{BOLD}{pct:3d}%{RESET} "
            f"{DIM}({current}/{total}){RESET} "
            f"{BOLD}{step_name}{RESET} "
            f"{DIM}[{time_str}]{RESET}"
        )
        return line

    def render(self, state_data: Dict[str, Any], newline: bool = False) -> None:
        """Render to /dev/tty if available, fallback to sys.stderr."""
        line = self.format_line(state_data)

        # Prefer writing directly to the controlling terminal
        try:
            with open("/dev/tty", "w", encoding="utf-8") as tty:
                tty.write(CLEAR_LINE + line + ("\n" if newline else ""))
                tty.flush()
                return
        except Exception:
            pass

        # Fallback to sys.stderr if /dev/tty is unavailable
        try:
            sys.stderr.write(CLEAR_LINE + line + ("\n" if newline else ""))
            sys.stderr.flush()
        except Exception:
            pass
