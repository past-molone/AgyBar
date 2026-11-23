#!/usr/bin/env python3
"""Terminal progress bar renderer for AgyBar.

Configured with high-precision 'smooth' fractional blocks and 'pink' neon theme.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# ANSI Color Codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CLEAR_LINE = "\033[2K\r"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"

# 256-Color & Standard ANSI Palettes
COLOR_PALETTES = {
    "pink": {
        "primary": "\033[38;5;205m\033[1m",      # Neon hot pink
        "secondary": "\033[38;5;198m\033[1m",    # Electric magenta
        "pct": "\033[38;5;212m\033[1m",          # Bright pink
        "bar_fill": "\033[38;5;205m",
        "empty": "\033[38;5;237m",               # Subtle dark block
    },
    "cyan": {
        "primary": "\033[38;5;51m\033[1m",
        "secondary": "\033[38;5;45m\033[1m",
        "pct": "\033[38;5;81m\033[1m",
        "bar_fill": "\033[38;5;45m",
        "empty": "\033[38;5;237m",
    },
    "green": {
        "primary": "\033[38;5;48m\033[1m",
        "secondary": "\033[38;5;120m\033[1m",
        "pct": "\033[38;5;84m\033[1m",
        "bar_fill": "\033[38;5;48m",
        "empty": "\033[38;5;237m",
    },
    "purple": {
        "primary": "\033[38;5;141m\033[1m",
        "secondary": "\033[38;5;177m\033[1m",
        "pct": "\033[38;5;183m\033[1m",
        "bar_fill": "\033[38;5;141m",
        "empty": "\033[38;5;237m",
    },
    "amber": {
        "primary": "\033[38;5;214m\033[1m",
        "secondary": "\033[38;5;220m\033[1m",
        "pct": "\033[38;5;221m\033[1m",
        "bar_fill": "\033[38;5;214m",
        "empty": "\033[38;5;237m",
    },
}

CONFIG_PATH = Path.home() / ".agybar.json"


def load_config() -> Dict[str, Any]:
    default_config: Dict[str, Any] = {
        "style": "smooth",
        "theme": "pink",
        "width": 20,
        "badge_symbol": "⚡",
        "badge_name": "AgyBar",
        "badge_style": "default",  # "default" | "pill" | "bracket" | "minimal"
        "show_badge": True,
        "show_bar": True,
        "show_pct": True,
        "show_steps": True,
        "show_action": True,
        "show_timer": True,
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_conf = json.load(f)
                default_config.update(user_conf)
        except Exception:
            pass
    return default_config


class ProgressBarRenderer:
    def __init__(
        self,
        style: Optional[str] = None,
        theme: Optional[str] = None,
        width: Optional[int] = None,
        badge_symbol: Optional[str] = None,
        badge_name: Optional[str] = None,
        badge_style: Optional[str] = None,
    ):
        conf = load_config()
        self.style = style or conf.get("style", "smooth")
        self.theme = theme or conf.get("theme", "pink")
        self.width = width or conf.get("width", 20)
        self.badge_symbol = badge_symbol or conf.get("badge_symbol", "⚡")
        self.badge_name = badge_name or conf.get("badge_name", "AgyBar")
        self.badge_style = badge_style or conf.get("badge_style", "default")

        self.show_badge = conf.get("show_badge", True)
        self.show_bar = conf.get("show_bar", True)
        self.show_pct = conf.get("show_pct", True)
        self.show_steps = conf.get("show_steps", True)
        self.show_action = conf.get("show_action", True)
        self.show_timer = conf.get("show_timer", True)

        self.colors = COLOR_PALETTES.get(self.theme, COLOR_PALETTES["pink"])

    def format_badge(self, status: str = "running") -> str:
        """Format the #badge component."""
        if not self.show_badge:
            return ""

        if status == "completed":
            symbol = "✔"
            name = self.badge_name
            color = "\033[38;5;120m\033[1m"  # Green
        else:
            symbol = self.badge_symbol
            name = self.badge_name
            color = self.colors["primary"]

        if self.badge_style == "pill":
            # Inverted colored pill: [ ⚡ AgyBar ]
            return f"\033[48;5;198m\033[38;5;232m\033[1m {symbol} {name} {RESET}"
        elif self.badge_style == "bracket":
            return f"{color}[{symbol} {name}]{RESET}"
        elif self.badge_style == "minimal":
            return f"{color}{symbol}{RESET}"
        else:
            # Default: Bold symbol + name
            return f"{color}{symbol} {name}{RESET}"

    def format_bar(self, current: int, total: int) -> str:
        """Format the #bar-fill component with smooth fractional sub-blocks."""
        if not self.show_bar:
            return ""

        w = self.width
        if total <= 0:
            total = 1
        current = max(0, min(current, total))
        ratio = current / total

        fill_color = self.colors["bar_fill"]
        empty_color = self.colors["empty"]

        if self.style == "smooth":
            sub_blocks = ["", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"]
            full_blocks = int(w * ratio)
            remainder = (w * ratio) - full_blocks
            sub_idx = int(remainder * 8)
            sub_char = sub_blocks[sub_idx]

            fill_str = "█" * full_blocks + sub_char
            empty_count = w - full_blocks - (1 if sub_char else 0)
            empty_str = "░" * max(0, empty_count)

            return f"{fill_color}{fill_str}{empty_color}{empty_str}{RESET}"

        elif self.style == "ascii":
            fill_len = int(round(w * ratio))
            fill = "=" * max(0, fill_len - 1) + (">" if 0 < fill_len < w else ("=" if fill_len == w else ""))
            empty = "-" * (w - len(fill))
            return f"{fill_color}[{fill}{DIM}{empty}]{RESET}"

        elif self.style == "dots":
            fill_len = int(round(w * ratio))
            fill = "●" * fill_len
            empty = "○" * (w - fill_len)
            return f"{fill_color}{fill}{DIM}{empty}{RESET}"

        else:
            # Default: solid blocks
            fill_len = int(round(w * ratio))
            fill = "█" * fill_len
            empty = "░" * (w - fill_len)
            return f"{fill_color}{fill}{empty_color}{empty}{RESET}"

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
        if len(step_name) > 36:
            step_name = step_name[:33] + "..."

        status = state_data.get("status", "running")

        parts = []

        # 1. #badge
        badge = self.format_badge(status)
        if badge:
            parts.append(badge)

        # 2. #bar-fill
        bar = self.format_bar(current, total)
        if bar:
            parts.append(bar)

        # 3. #percentage
        if self.show_pct:
            pct_color = "\033[38;5;120m\033[1m" if status == "completed" else self.colors["pct"]
            parts.append(f"{pct_color}{pct:3d}%{RESET}")

        # 4. #step-counter
        if self.show_steps:
            parts.append(f"{DIM}({current}/{total}){RESET}")

        # 5. #action-title
        if self.show_action:
            parts.append(f"{BOLD}• {step_name}{RESET}")

        # 6. #timer
        if self.show_timer:
            parts.append(f"{DIM}[{time_str}]{RESET}")

        return " ".join(parts)

    def render(self, state_data: Dict[str, Any], newline: bool = False) -> None:
        """Render directly to controlling terminal (/dev/tty) or fallback to sys.stderr."""
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
