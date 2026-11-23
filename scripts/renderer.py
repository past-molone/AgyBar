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
        "primary": "\033[38;5;141m\033[1m",      # Neon electric purple for badge text
        "secondary": "\033[38;5;177m\033[1m",    # Orchid purple accent
        "pct": "\033[38;5;141m\033[1m",          # Neon electric purple for percentage
        "bar_fill": "\033[38;5;205m",            # Hot neon pink for the smooth progress bar
        "empty": "\033[38;5;237m",               # Subtle dark background block
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
        "badge_name": "Progress",
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

        purple_color = self.colors["primary"]
        name_str = f"{purple_color}{self.badge_name}{RESET}"

        if status == "completed":
            sym_str = f"\033[38;5;120m\033[1m✔{RESET}"
        else:
            sym_str = f"{purple_color}{self.badge_symbol}{RESET}"

        if self.badge_style == "pill":
            return f"\033[48;5;141m\033[38;5;232m\033[1m {self.badge_symbol} {self.badge_name} {RESET}"
        elif self.badge_style == "bracket":
            return f"{purple_color}[{self.badge_symbol} {self.badge_name}]{RESET}"
        elif self.badge_style == "minimal":
            return sym_str
        else:
            # Default: Symbol + Purple word
            return f"{sym_str} {name_str}"

    def format_bar(self, current: int, total: int, ratio: Optional[float] = None) -> str:
        """Format the #bar-fill component with smooth fractional sub-blocks."""
        if not self.show_bar:
            return ""

        w = self.width
        if ratio is None:
            if total <= 0:
                total = 1
            current = max(0, min(current, total))
            ratio = current / total
        else:
            ratio = max(0.0, min(1.0, float(ratio)))

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

        # Check for fine-grained percentage (e.g. from subagent inspection or micro-stepping)
        granular_pct = state_data.get("granular_pct")
        if granular_pct is not None:
            pct = int(round(granular_pct))
            ratio = max(0.0, min(1.0, float(granular_pct) / 100.0))
        else:
            pct = int(round((current / total) * 100))
            ratio = current / total

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
        bar = self.format_bar(current, total, ratio=ratio)
        if bar:
            parts.append(bar)

        # 3. #percentage
        if self.show_pct:
            pct_color = self.colors["pct"]  # Always purple
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
