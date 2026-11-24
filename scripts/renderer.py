#!/usr/bin/env python3
"""Terminal progress bar renderer for AgyBar.

Configured with high-precision 'smooth' fractional blocks and 'pink' neon theme.
"""

import json
import os
import shutil
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

# 256-Color, Truecolor & Standard ANSI Palettes
COLOR_PALETTES = {
    "pink": {
        "primary": "\033[38;2;216;180;254m\033[1m",    # Bright pastel lilac (#d8b4fe) for 'Progress'
        "secondary": "\033[38;2;233;213;255m\033[1m",  # Soft lavender (#e9d5ff)
        "pct": "\033[38;2;216;180;254m\033[1m",        # Bright pastel lilac (#d8b4fe) for percentage
        "bar_fill": "\033[38;2;249;168;212m",          # Soft pastel baby pink (#f9a8d4) for progress bar
        "empty": "\033[38;2;65;70;85m",                # Soft slate gray background block
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
        "badge_symbol": "✦",
        "badge_name": "Progress",
        "badge_style": "default",  # "default" | "pill" | "bracket" | "minimal"
        "dual_line": True,
        "show_eta": True,
        "show_badge": True,
        "show_bar": True,
        "show_pct": True,
        "show_steps": True,
        "show_action": True,
        "show_timer": False,  # Replaced by ETA as AI CLI already has intrinsic elapsed timer
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
        self.badge_symbol = badge_symbol or conf.get("badge_symbol", "✦")
        self.badge_name = badge_name or conf.get("badge_name", "Progress")
        self.badge_style = badge_style or conf.get("badge_style", "default")
        self.dual_line = conf.get("dual_line", True)
        self.show_eta = conf.get("show_eta", True)

        self.show_badge = conf.get("show_badge", True)
        self.show_bar = conf.get("show_bar", True)
        self.show_pct = conf.get("show_pct", True)
        self.show_steps = conf.get("show_steps", True)
        self.show_action = conf.get("show_action", True)
        self.show_timer = conf.get("show_timer", False)

        self.colors = COLOR_PALETTES.get(self.theme, COLOR_PALETTES["pink"])
        self.last_rendered = False

    def format_badge(self, status: str = "running") -> str:
        """Format the #badge component."""
        if not self.show_badge:
            return ""

        purple_color = self.colors["primary"]
        name_str = f"{purple_color}{self.badge_name}{RESET}"

        if status == "completed":
            sym_str = f"\033[38;2;110;231;183m\033[1m✔{RESET}"
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

        term_cols = shutil.get_terminal_size((80, 24)).columns
        if term_cols < 60:
            w = max(8, min(self.width, 10))
        elif term_cols < 75:
            w = max(10, min(self.width, 14))
        else:
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

    def format_eta(self, state_data: Dict[str, Any], pct: float, status: str) -> str:
        """Calculates and formats live ETA instead of redundant elapsed timer."""
        if not self.show_eta:
            return ""

        if status == "completed":
            return f"{DIM}[Completed]{RESET}"

        start_time = state_data.get("start_time", time.time())
        elapsed_sec = max(0.1, time.time() - start_time)

        if pct >= 99.0:
            return f"{DIM}[Finalizing...]{RESET}"
        elif pct < 5.0 or elapsed_sec < 1.5:
            return f"{DIM}[Estimating ETA...]{RESET}"

        velocity = pct / elapsed_sec  # % per second
        rem_pct = max(0.0, 100.0 - pct)
        rem_sec = int(rem_pct / max(0.08, velocity))
        r_mins, r_secs = divmod(rem_sec, 60)

        if r_mins > 0:
            return f"{DIM}[ETA {r_mins}m {r_secs:02d}s]{RESET}"
        return f"{DIM}[ETA {r_secs:02d}s]{RESET}"

    def format_subagent_line(self, state_data: Dict[str, Any]) -> str:
        """Formats the secondary dual-line breadcrumb showing subagent findings."""
        if not self.dual_line:
            return ""

        source = state_data.get("subagent_source", "Radar")
        action = (
            state_data.get("subagent_action")
            or state_data.get("step_name")
            or "Analyzing workspace and inspecting progress"
        )
        # Normalize whitespace and strip newlines so line 2 stays strictly on a single line
        action = " ".join(str(action).split())

        term_cols = shutil.get_terminal_size((80, 24)).columns
        max_len = max(24, term_cols - 18)
        if len(action) > max_len:
            action = action[:max_len - 3] + "..."

        branch = "\033[38;2;180;185;200m"
        bold_white = "\033[97;1m"
        white = "\033[97m"
        return f"   {branch}└─ {bold_white}{source}:{RESET} {white}{action}{RESET}"

    def format_line(self, state_data: Dict[str, Any]) -> str:
        current = state_data.get("current_step", 1)
        total = state_data.get("total_steps", 4)
        if total <= 0:
            total = 1
        current = max(0, min(current, total))

        # Check for fine-grained percentage (e.g. from subagent inspection or micro-stepping)
        granular_pct = state_data.get("granular_pct")
        if granular_pct is not None:
            pct = float(granular_pct)
            ratio = max(0.0, min(1.0, pct / 100.0))
        else:
            pct = float(round((current / total) * 100))
            ratio = current / total

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
            pct_color = self.colors["pct"]  # Pastel lilac
            parts.append(f"{pct_color}{int(round(pct)):3d}%{RESET}")

        # 4. #step-counter
        if self.show_steps:
            parts.append(f"{DIM}({current}/{total}){RESET}")

        # 5. #action-title (shown on line 1 only in single-line mode)
        if self.show_action and not self.dual_line:
            parts.append(f"{BOLD}• {step_name}{RESET}")

        # 6. #eta
        eta = self.format_eta(state_data, pct, status)
        if eta:
            parts.append(eta)

        line1 = " ".join(parts)

        if self.dual_line:
            line2 = self.format_subagent_line(state_data)
            return f"{line1}\n{line2}"

        return line1

    def render(self, state_data: Dict[str, Any], newline: bool = False, anchor_bottom: bool = False) -> None:
        """Render single or dual line with support for inline and anchored terminal modes."""
        output_text = self.format_line(state_data)

        def write_stream(stream):
            if anchor_bottom:
                try:
                    rows, _ = shutil.get_terminal_size((80, 24))
                    lines = output_text.split("\n")
                    l1 = lines[0] if len(lines) > 0 else ""
                    l2 = lines[1] if len(lines) > 1 else ""
                    if self.dual_line and l2:
                        cmd = (
                            f"\0337\033[?25l"
                            f"\033[{rows-1};1H\033[2K{l1}"
                            f"\033[{rows};1H\033[2K{l2}"
                            f"\033[?25h\0338"
                        )
                    else:
                        cmd = f"\0337\033[?25l\033[{rows};1H\033[2K{l1}\033[?25h\0338"
                    stream.write(cmd)
                    stream.flush()
                    return
                except Exception:
                    pass

            if self.dual_line:
                lines = output_text.split("\n")
                l1 = lines[0] if len(lines) > 0 else ""
                l2 = lines[1] if len(lines) > 1 else ""
                prefix = "\033[1A\033[2K\r" if self.last_rendered else "\033[2K\r"
                stream.write(f"{prefix}{l1}\n\033[2K\r{l2}" + ("\n" if newline else ""))
                stream.flush()
                self.last_rendered = not newline
            else:
                stream.write(CLEAR_LINE + output_text + ("\n" if newline else ""))
                stream.flush()
                self.last_rendered = not newline

        try:
            with open("/dev/tty", "w", encoding="utf-8") as tty:
                write_stream(tty)
                return
        except Exception:
            pass

        try:
            write_stream(sys.stderr)
        except Exception:
            pass
